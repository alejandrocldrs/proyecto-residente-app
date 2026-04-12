"""
Planificador Inteligente de Estudio - Backend Module
Generates structured study plans based on app content and user preferences.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
import uuid
import math
import unicodedata
import re

# Time weights in minutes per activity
WEIGHTS = {
    "presentacion": 20,
    "cuestionario": 20,
    "escape_room": 8,
    "imagen_dx": 0.5,
    "simulacro": 240,
}

# Priority order when time is insufficient
PRIORITY_ORDER = ["cuestionario", "presentacion", "escape_room", "imagen_dx", "simulacro"]

# Strict area ordering for the study plan
AREA_ORDER = {
    "Cirugía": 0,
    "Ginecología y Obstetricia": 1,
    "Medicina Interna": 2,
    "Pediatría": 3,
    "Otros": 4,
}

planner_router = APIRouter(prefix="/api/planner", tags=["planner"])


# ── Pydantic Models ──────────────────────────────────────────────────────────

class PlanRequest(BaseModel):
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    intensity: str   # "leve" | "moderado" | "intenso"
    rest_day: bool   # True = 1 rest day per week


class ActivityComplete(BaseModel):
    day_number: int
    activity_index: int


class RecalculateRequest(BaseModel):
    plan_id: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_specialty(specialty: str):
    """Split 'Cirugía - Angiología' into (area, subtema).
    If no dash, or subtema is 'General', use the area name as subtema."""
    # Normalize test/irregular specialty names
    SPECIALTY_MAP = {
        "TEST-Oncologia": ("Medicina Interna", "Oncología"),
    }
    if specialty in SPECIALTY_MAP:
        return SPECIALTY_MAP[specialty]

    if " - " in specialty:
        parts = specialty.split(" - ", 1)
        area = parts[0].strip()
        subtema = parts[1].strip()
        if subtema == "General":
            subtema = area
        return area, subtema
    return specialty.strip(), specialty.strip()


def get_vueltas(intensity: str, available_capacity: float, one_pass_load: float):
    """Calculate number of passes based on intensity."""
    if one_pass_load <= 0:
        return 1
    max_possible = available_capacity / one_pass_load
    if intensity == "leve":
        return min(1.0, max_possible)
    elif intensity == "moderado":
        target = 2.0
        return min(target, max_possible)
    else:  # intenso
        return max_possible


async def gather_content(db) -> dict:
    """Gather all content from DB, structured by area → subtema."""
    structure = {}

    # 1. Presentaciones (module → submodule)
    presentations = await db.presentations.find(
        {}, {"_id": 0, "id": 1, "title": 1, "module": 1, "submodule": 1}
    ).to_list(None)
    for p in presentations:
        area = p.get("module", "Otros")
        subtema = p.get("submodule") or area
        key = (area, subtema)
        if key not in structure:
            structure[key] = {"presentaciones": [], "cuestionarios": [], "escape_rooms": [], "imagenes": []}
        structure[key]["presentaciones"].append({
            "id": p["id"],
            "title": p.get("title", "Presentación"),
            "type": "presentacion",
            "weight": WEIGHTS["presentacion"],
        })

    # 2. Cuestionarios GPC (questions grouped by specialty → topic)
    pipeline = [
        {"$group": {
            "_id": {"specialty": "$specialty", "topic": "$topic"},
            "count": {"$sum": 1},
            "sample_id": {"$first": "$id"},
        }},
        {"$sort": {"_id.specialty": 1, "_id.topic": 1}},
    ]
    quiz_groups = await db.questions.aggregate(pipeline).to_list(None)
    for qg in quiz_groups:
        spec = qg["_id"]["specialty"]
        topic = qg["_id"]["topic"]
        area, subtema = parse_specialty(spec)
        key = (area, subtema)
        if key not in structure:
            structure[key] = {"presentaciones": [], "cuestionarios": [], "escape_rooms": [], "imagenes": []}
        import hashlib
        quiz_id = hashlib.sha256(f"{spec}|{topic}".encode()).hexdigest()[:16]
        structure[key]["cuestionarios"].append({
            "id": quiz_id,
            "title": topic,
            "type": "cuestionario",
            "weight": WEIGHTS["cuestionario"],
            "question_count": qg["count"],
        })

    # 3. Escape Rooms (clinical_cases: module → submodule)
    cases = await db.clinical_cases.find(
        {}, {"_id": 0, "id": 1, "title": 1, "module": 1, "submodule": 1}
    ).to_list(None)
    for c in cases:
        area = c.get("module", "Otros")
        raw_sub = c.get("submodule") or area
        subtema = area if raw_sub == "General" else raw_sub
        key = (area, subtema)
        if key not in structure:
            structure[key] = {"presentaciones": [], "cuestionarios": [], "escape_rooms": [], "imagenes": []}
        structure[key]["escape_rooms"].append({
            "id": c["id"],
            "title": c.get("title", "Caso Clínico"),
            "type": "escape_room",
            "weight": WEIGHTS["escape_room"],
        })

    # 4. Imágenes diagnósticas - EXCLUDED from planner (material extra)

    # 5. Simulacros (standalone)
    simulacros = await db.simulacros.find(
        {}, {"_id": 0, "id": 1, "title": 1, "total_questions": 1}
    ).to_list(None)

    return structure, simulacros


def _normalize(text: str) -> str:
    """Remove accents, lowercase, strip special chars."""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9\s]', ' ', text.lower()).strip()


def _stem_es(word: str) -> str:
    """Basic Spanish stemming: strip common suffixes to match plurals/variants."""
    if len(word) <= 3:
        return word
    # Order matters: try longest suffixes first
    for suffix in ['iones', 'cion', 'idad', 'itis', 'osis', 'emia',
                   'icas', 'icos', 'icas', 'ados', 'idas', 'ando', 'endo',
                   'ias', 'ios', 'ica', 'ico', 'osa', 'oso', 'ado', 'ida',
                   'as', 'es', 'os']:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[:-len(suffix)]
    if word.endswith('s') and len(word) > 4:
        return word[:-1]
    return word


def _extract_keywords(text: str) -> set:
    """Extract meaningful medical keywords from a title."""
    n = _normalize(text)
    # Remove common prefixes: "Repaso 1.", "CIRUGIA GENERAL 5.", "ANGIOLOGIA 2.", etc.
    n = re.sub(r'^repaso\s*\d+\.?\s*', '', n)
    n = re.sub(r'^[a-z]+(?:\s+[a-z]+)?\s*\d+\.?\s*', '', n)
    stopwords = {
        'de', 'del', 'la', 'el', 'en', 'y', 'los', 'las', 'un', 'una', 'por',
        'con', 'para', 'que', 'su', 'al', 'se', 'es', 'no', 'mas', 'como',
        'sus', 'o', 'fue', 'ha', 'si', 'son', 'entre', 'muy', 'lo', 'todo',
        'diagnostico', 'tratamiento', 'prevencion', 'manejo', 'atencion',
        'niveles', 'tres', 'adulto', 'adultos', 'ninos', 'paciente', 'pacientes',
        'a', 'e', 'primer', 'nivel', 'segundo', 'tercer', 'poblacion',
        'abordaje', 'intervencion', 'intervenciones', 'preventivas',
        'completa', 'completo', 'complicada', 'complicado',
    }
    words = n.split()
    return {w for w in words if len(w) > 2 and w not in stopwords}


def _extract_stems(text: str) -> set:
    """Extract stemmed keywords for fuzzy matching."""
    keywords = _extract_keywords(text)
    return {_stem_es(w) for w in keywords}


def _match_score(kw1: set, kw2: set, stems1: set, stems2: set) -> float:
    """Enhanced matching using exact keywords + stems + substring containment.
    Returns a score where higher = better match.
    Requires at least 2 matching signals to avoid false positives on common words."""
    if not kw1 or not kw2:
        return 0

    max_possible = min(len(kw1), len(kw2))
    matched_count = 0

    # 1. Exact keyword overlap (strongest signal)
    exact_overlap = kw1 & kw2
    matched_count += len(exact_overlap)

    # 2. Stem overlap (catches plurals: hernias/hernia, fracturas/fractura)
    already_stemmed = {_stem_es(w) for w in exact_overlap}
    stem_overlap = (stems1 & stems2) - already_stemmed
    matched_count += len(stem_overlap) * 0.8

    # 3. Substring containment (catches partial matches)
    remaining_kw1 = kw1 - exact_overlap
    remaining_kw2 = kw2 - exact_overlap
    for w1 in remaining_kw1:
        for w2 in remaining_kw2:
            if len(w1) >= 4 and len(w2) >= 4:
                if w1 in w2 or w2 in w1:
                    matched_count += 0.6
                    break

    score = matched_count / max_possible if max_possible > 0 else 0
    return score


def _get_gpc_base(title: str) -> str:
    """Extract GPC base for grouping escape rooms with their cuestionario.
    E.g. 'CIRUGIA GENERAL 1. Diagnóstico de Apendicitis Aguda_A' -> normalized base without _A suffix.
    """
    # Strip _A, _B, _C suffixes
    base = re.sub(r'_[A-Z]$', '', title.strip())
    return _normalize(base)


def build_study_queue(structure: dict) -> list:
    """Build ordered study queue with topic-level matching:
    For each subtema, group Presentation → matching Cuestionarios → matching Escape Rooms,
    then leftover content at the end of the subtema.
    """
    queue = []
    sorted_keys = sorted(structure.keys(), key=lambda k: (AREA_ORDER.get(k[0], 5), k[0], k[1]))

    for area, subtema in sorted_keys:
        content = structure[(area, subtema)]
        presentations = list(content["presentaciones"])
        cuestionarios = list(content["cuestionarios"])
        escape_rooms = list(content["escape_rooms"])
        imagenes = list(content["imagenes"])

        # --- Step 1: Group escape rooms with their parent cuestionario by GPC base ---
        # Build a map: cuestionario_normalized_title -> cuestionario item
        cuest_map = {}  # normalized_title -> cuestionario item
        for c in cuestionarios:
            base = _normalize(c["title"])
            cuest_map[base] = c

        # Map escape rooms to cuestionarios
        cuest_to_escapes = {_normalize(c["title"]): [] for c in cuestionarios}
        unmatched_escapes = []
        for er in escape_rooms:
            er_base = _get_gpc_base(er["title"])
            if er_base in cuest_to_escapes:
                cuest_to_escapes[er_base].append(er)
            else:
                # Try fuzzy: find closest cuestionario by prefix
                matched = False
                for cbase in cuest_to_escapes:
                    if er_base.startswith(cbase[:30]) or cbase.startswith(er_base[:30]):
                        cuest_to_escapes[cbase].append(er)
                        matched = True
                        break
                if not matched:
                    unmatched_escapes.append(er)

        # --- Step 2: Build GPC groups (cuestionario + its escape rooms) ---
        gpc_groups = []
        for c in cuestionarios:
            cbase = _normalize(c["title"])
            gpc_groups.append({
                "cuestionario": c,
                "escape_rooms": cuest_to_escapes.get(cbase, []),
                "keywords": _extract_keywords(c["title"]),
                "stems": _extract_stems(c["title"]),
            })

        # --- Step 3: REVERSE MATCHING - each cuestionario finds its best presentation ---
        # Pre-compute presentation keywords/stems
        pres_data = []
        for pres in presentations:
            pres_data.append({
                "item": pres,
                "keywords": _extract_keywords(pres["title"]),
                "stems": _extract_stems(pres["title"]),
            })

        # For each GPC group, find its best-matching presentation
        gpc_to_pres = {}  # gpc_index -> pres_index
        for j, gpc in enumerate(gpc_groups):
            best_score = 0
            best_pres_idx = -1
            for i, pd in enumerate(pres_data):
                score = _match_score(pd["keywords"], gpc["keywords"], pd["stems"], gpc["stems"])
                if score > best_score and score >= 0.2:
                    best_score = score
                    best_pres_idx = i
            if best_pres_idx >= 0:
                gpc_to_pres[j] = best_pres_idx

        # Build reverse map: pres_index -> [gpc_indices]
        pres_to_gpcs = {i: [] for i in range(len(presentations))}
        for j, i in gpc_to_pres.items():
            pres_to_gpcs[i].append(j)

        # --- Step 4: Build study blocks - presentation followed by its matched content ---
        study_blocks = []
        for i, pres in enumerate(presentations):
            block_items = [pres]
            for j in pres_to_gpcs[i]:
                block_items.append(gpc_groups[j]["cuestionario"])
                block_items.extend(gpc_groups[j]["escape_rooms"])
            study_blocks.append(block_items)

        # --- Step 5: Collect unmatched GPC groups ---
        for j, gpc in enumerate(gpc_groups):
            if j not in gpc_to_pres:
                block = [gpc["cuestionario"]] + gpc["escape_rooms"]
                study_blocks.append(block)

        # --- Step 6: Match unmatched escape rooms to their best presentation ---
        if unmatched_escapes and pres_data:
            for er in unmatched_escapes:
                er_kw = _extract_keywords(er["title"])
                er_stems = _extract_stems(er["title"])
                best_score = 0
                best_block_idx = -1
                for i, pd in enumerate(pres_data):
                    score = _match_score(pd["keywords"], er_kw, pd["stems"], er_stems)
                    if score > best_score and score >= 0.2:
                        best_score = score
                        best_block_idx = i
                if best_block_idx >= 0:
                    # Append to that presentation's block
                    study_blocks[best_block_idx].append(er)
                else:
                    # Truly unmatched - add at end
                    study_blocks.append([er])
        elif unmatched_escapes:
            study_blocks.append(unmatched_escapes)

        # --- Step 7: Flatten blocks into queue ---
        for block in study_blocks:
            for item in block:
                queue.append({**item, "area": area, "subtema": subtema})

    # --- Post-processing: Cross-subtema duplication rules ---
    # Rule: Duplicate diabetes content from "Medicina Interna (general)" after
    # the "Diabetes Mellitus" presentation in "Endocrinología"
    queue = _apply_cross_subtema_duplications(queue)

    return queue


# Cross-subtema duplication configuration
CROSS_SUBTEMA_RULES = [
    {
        "source_subtema": "Medicina Interna (general)",
        "keyword": "diabet",
        "target_presentation_subtema": "Endocrinología",
        "target_presentation_keyword": "diabet",
    },
]


def _apply_cross_subtema_duplications(queue: list) -> list:
    """Duplicate specific cuestionarios/escape rooms from one subtema to another,
    placing them after a matching presentation in the target subtema."""
    for rule in CROSS_SUBTEMA_RULES:
        # Find source items (cuestionarios + escape rooms matching keyword in source subtema)
        source_items = []
        for item in queue:
            if (item.get("subtema") == rule["source_subtema"]
                and item.get("type") in ("cuestionario", "escape_room")
                and rule["keyword"] in _normalize(item.get("title", ""))):
                source_items.append(item)

        if not source_items:
            continue

        # Find the target presentation index
        target_idx = None
        for i, item in enumerate(queue):
            if (item.get("subtema") == rule["target_presentation_subtema"]
                and item.get("type") == "presentacion"
                and rule["target_presentation_keyword"] in _normalize(item.get("title", ""))):
                target_idx = i
                break

        if target_idx is None:
            continue

        # Find the insertion point: after the target presentation and its already-matched content
        insert_at = target_idx + 1
        while insert_at < len(queue):
            next_item = queue[insert_at]
            # Stop when we hit another presentation or a different subtema
            if next_item.get("type") == "presentacion":
                break
            if next_item.get("subtema") != rule["target_presentation_subtema"]:
                break
            insert_at += 1

        # Create duplicated items with the target subtema
        duplicated = []
        for item in source_items:
            dup = {**item, "subtema": rule["target_presentation_subtema"]}
            duplicated.append(dup)

        # Insert duplicates
        queue = queue[:insert_at] + duplicated + queue[insert_at:]

    return queue


def generate_daily_plan(
    queue: list,
    simulacros: list,
    effective_days: int,
    vueltas: float,
    start_date: datetime,
    rest_day: bool,
    total_days: int,
):
    """Distribute activities across effective study days."""

    # Multiply queue by vueltas
    full_queue = []
    full_passes = int(vueltas)
    fractional = vueltas - full_passes

    for v in range(full_passes):
        for item in queue:
            full_queue.append({**item, "vuelta": v + 1})

    # Fractional pass: add items by priority until we fill the fraction
    if fractional > 0:
        fractional_count = int(len(queue) * fractional)
        priority_map = {t: i for i, t in enumerate(PRIORITY_ORDER)}
        sorted_queue = sorted(queue, key=lambda x: priority_map.get(x["type"], 99))
        for item in sorted_queue[:fractional_count]:
            full_queue.append({**item, "vuelta": full_passes + 1})

    # CRITICAL: Re-sort entire full_queue by (vuelta, AREA_ORDER).
    # This ensures each complete pass goes Cirugía → Gine → MedInt → Pedi → Otros,
    # and vuelta 2 starts only after vuelta 1 finishes all areas.
    # Python's sort is stable, so within (vuelta, area) the subtema/block order is preserved.
    full_queue.sort(key=lambda x: (x.get("vuelta", 1), AREA_ORDER.get(x.get("area", ""), 5), x.get("area", "")))

    # Simulacros: only in the second half, evenly distributed
    half_point = effective_days // 2
    second_half_days = effective_days - half_point
    sim_days = set()
    if simulacros and second_half_days > 0:
        num_sims = len(simulacros)
        sim_interval = max(1, second_half_days // num_sims)
        sim_idx = 0
        for d in range(half_point, effective_days, sim_interval):
            if sim_idx < num_sims:
                sim_days.add(d)
                sim_idx += 1

    # Calculate daily load target (in minutes)
    total_content_weight = sum(item["weight"] for item in full_queue)
    content_days = effective_days - len(sim_days)
    daily_target = total_content_weight / max(content_days, 1)

    # Build day-by-day plan
    daily_plan = []
    queue_index = 0
    sim_index = 0
    effective_day_counter = 0

    for day_num in range(total_days):
        day_date = start_date + timedelta(days=day_num)
        is_rest = rest_day and (day_num % 7 == 6)

        if is_rest:
            daily_plan.append({
                "day_number": day_num + 1,
                "date": day_date.strftime("%Y-%m-%d"),
                "is_rest": True,
                "activities": [],
                "total_minutes": 0,
            })
            continue

        activities = []
        day_minutes = 0

        # Check if this is a simulacro day (second half only)
        if effective_day_counter in sim_days and sim_index < len(simulacros):
            sim = simulacros[sim_index]
            activities.append({
                "type": "simulacro",
                "area": "Simulacro",
                "subtema": "",
                "title": sim["title"],
                "content_id": sim["id"],
                "weight": WEIGHTS["simulacro"],
                "completed": False,
                "vuelta": 1,
            })
            day_minutes += WEIGHTS["simulacro"]
            sim_index += 1

        # Regular study: fill to daily target, but NEVER mix different areas
        current_day_area = None
        while queue_index < len(full_queue) and day_minutes < daily_target:
            item = full_queue[queue_index]
            item_area = item.get("area", "")

            # If this item is from a different AREA than what we already have, stop
            if current_day_area and item_area and item_area != current_day_area and item_area != "Simulacro" and current_day_area != "Simulacro":
                break  # Don't add it, let the next day handle it

            activities.append({
                "type": item["type"],
                "area": item["area"],
                "subtema": item["subtema"],
                "title": item["title"],
                "content_id": item["id"],
                "weight": item["weight"],
                "completed": False,
                "vuelta": item.get("vuelta", 1),
            })
            day_minutes += item["weight"]
            queue_index += 1

            if not current_day_area and item_area and item_area != "Simulacro":
                current_day_area = item_area

        # --- Clean day breaks: minimize splitting subtemas within the same area ---
        if len(activities) >= 3:
            subtema_counts = {}
            for act in activities:
                st = act.get("subtema", "")
                if st:
                    subtema_counts[st] = subtema_counts.get(st, 0) + 1

            if subtema_counts:
                main_subtema = max(subtema_counts, key=subtema_counts.get)

                # Scan from end for tail of different subtema
                tail_start = len(activities)
                tail_subtema = None
                for i in range(len(activities) - 1, -1, -1):
                    act_st = activities[i].get("subtema", "")
                    if act_st and act_st != main_subtema:
                        if tail_subtema is None:
                            tail_subtema = act_st
                        if act_st == tail_subtema:
                            tail_start = i
                        else:
                            break
                    else:
                        break

                tail_count = len(activities) - tail_start

                if tail_count > 0 and tail_subtema:
                    remaining_same = sum(
                        1 for qi in range(queue_index, len(full_queue))
                        if full_queue[qi].get("subtema") == tail_subtema
                    )
                    total_items = tail_count + remaining_same

                    if total_items > 0 and tail_count / total_items < 0.4:
                        activities = activities[:tail_start]
                        day_minutes = sum(a["weight"] for a in activities)
                        queue_index -= tail_count

        daily_plan.append({
            "day_number": day_num + 1,
            "date": day_date.strftime("%Y-%m-%d"),
            "is_rest": False,
            "activities": activities,
            "total_minutes": round(day_minutes, 1),
        })
        effective_day_counter += 1

    # If there are leftover items, distribute them respecting area constraints
    while queue_index < len(full_queue):
        item = full_queue[queue_index]
        item_area = item.get("area", "")
        study_day_plans = [d for d in daily_plan if not d["is_rest"]]
        if not study_day_plans:
            break

        # Find lightest day that already has the same area (preferred)
        same_area_days = [
            d for d in study_day_plans
            if any(a.get("area") == item_area for a in d["activities"])
        ]
        if same_area_days:
            target = min(same_area_days, key=lambda d: d["total_minutes"])
        else:
            # Fallback: find lightest day with no activities (empty day)
            empty_days = [d for d in study_day_plans if not d["activities"]]
            if empty_days:
                target = min(empty_days, key=lambda d: d["total_minutes"])
            else:
                # Last resort: lightest day overall
                target = min(study_day_plans, key=lambda d: d["total_minutes"])

        target["activities"].append({
            "type": item["type"],
            "area": item["area"],
            "subtema": item["subtema"],
            "title": item["title"],
            "content_id": item["id"],
            "weight": item["weight"],
            "completed": False,
            "vuelta": item.get("vuelta", 1),
        })
        target["total_minutes"] = round(target["total_minutes"] + item["weight"], 1)
        queue_index += 1

    return daily_plan


# ── Dependency: get db ───────────────────────────────────────────────────────
# This will be set from server.py
_db = None

def set_db(database):
    global _db
    _db = database

def get_db():
    return _db


# ── Auth dependency (imported from server.py at runtime) ─────────────────────
_get_current_user = None

def set_auth_dependency(dep):
    global _get_current_user
    _get_current_user = dep


# ── Routes ───────────────────────────────────────────────────────────────────

@planner_router.get("/content-summary")
async def get_content_summary():
    db = get_db()
    structure, simulacros = await gather_content(db)

    # Build summary
    areas = {}
    totals = {"presentaciones": 0, "cuestionarios": 0, "escape_rooms": 0, "simulacros": len(simulacros)}

    AREA_SORT = AREA_ORDER
    for (area, subtema), content in sorted(structure.items(), key=lambda x: (AREA_SORT.get(x[0][0], 5), x[0][0], x[0][1])):
        if area not in areas:
            areas[area] = {"subtemas": {}, "totals": {"presentaciones": 0, "cuestionarios": 0, "escape_rooms": 0}}
        areas[area]["subtemas"][subtema] = {
            "presentaciones": len(content["presentaciones"]),
            "cuestionarios": len(content["cuestionarios"]),
            "escape_rooms": len(content["escape_rooms"]),
        }
        areas[area]["totals"]["presentaciones"] += len(content["presentaciones"])
        areas[area]["totals"]["cuestionarios"] += len(content["cuestionarios"])
        areas[area]["totals"]["escape_rooms"] += len(content["escape_rooms"])
        totals["presentaciones"] += len(content["presentaciones"])
        totals["cuestionarios"] += len(content["cuestionarios"])
        totals["escape_rooms"] += len(content["escape_rooms"])

    total_time_one_pass = (
        totals["presentaciones"] * WEIGHTS["presentacion"]
        + totals["cuestionarios"] * WEIGHTS["cuestionario"]
        + totals["escape_rooms"] * WEIGHTS["escape_room"]
        + totals["simulacros"] * WEIGHTS["simulacro"]
    )

    return {
        "areas": areas,
        "totals": totals,
        "total_time_one_pass_minutes": round(total_time_one_pass, 1),
        "weights": WEIGHTS,
    }


@planner_router.post("/generate")
async def generate_plan(req: PlanRequest):
    from fastapi import Request
    db = get_db()

    # Parse dates
    try:
        start = datetime.strptime(req.start_date, "%Y-%m-%d")
        end = datetime.strptime(req.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Formato de fecha inválido. Usar YYYY-MM-DD")

    if end <= start:
        raise HTTPException(400, "La fecha final debe ser posterior a la fecha de inicio")

    total_days = (end - start).days + 1
    total_weeks = math.ceil(total_days / 7)

    # Calculate effective days
    rest_days_count = total_weeks if req.rest_day else 0
    effective_days = total_days - rest_days_count

    if effective_days <= 0:
        raise HTTPException(400, "No hay días efectivos de estudio")

    # Gather content
    structure, simulacros = await gather_content(db)
    queue = build_study_queue(structure)

    if not queue:
        raise HTTPException(400, "No hay contenido disponible en la aplicación")

    # Calculate one-pass load
    one_pass_load = sum(item["weight"] for item in queue)
    # Add simulacro time to available capacity
    sim_time = len(simulacros) * WEIGHTS["simulacro"]
    available_minutes = effective_days * 480  # 8 hours max per day
    available_for_content = available_minutes - sim_time

    vueltas = get_vueltas(req.intensity, available_for_content, one_pass_load)
    vueltas = round(vueltas, 2)

    # Check if time is insufficient
    warning = None
    estimated_daily_hours = (one_pass_load * vueltas + sim_time) / effective_days / 60
    if vueltas < 1:
        warning = "El tiempo disponible es insuficiente para cubrir todo el contenido cómodamente. El plan priorizará contenido de alto rendimiento."

    # Generate daily plan
    daily_plan = generate_daily_plan(
        queue, simulacros, effective_days, vueltas, start, req.rest_day, total_days
    )

    # Count total activities
    total_activities = sum(len(d["activities"]) for d in daily_plan)
    avg_daily_minutes = round(sum(d["total_minutes"] for d in daily_plan if not d["is_rest"]) / max(effective_days, 1), 1)

    # Content totals
    totals = {"presentaciones": 0, "cuestionarios": 0, "escape_rooms": 0, "simulacros": 0}
    for (area, subtema), content in structure.items():
        totals["presentaciones"] += len(content["presentaciones"])
        totals["cuestionarios"] += len(content["cuestionarios"])
        totals["escape_rooms"] += len(content["escape_rooms"])
    totals["simulacros"] = len(simulacros)

    return {
        "plan": {
            "start_date": req.start_date,
            "end_date": req.end_date,
            "intensity": req.intensity,
            "rest_day": req.rest_day,
            "total_days": total_days,
            "total_weeks": total_weeks,
            "effective_days": effective_days,
            "estimated_vueltas": vueltas,
            "total_activities": total_activities,
            "avg_daily_minutes": avg_daily_minutes,
            "daily_plan": daily_plan,
            "content_totals": totals,
            "warning": warning,
        }
    }


@planner_router.post("/save")
async def save_plan(data: dict):
    db = get_db()
    # Extract user_id from the request (will be set by frontend)
    user_id = data.get("user_id")
    plan_data = data.get("plan")
    if not user_id or not plan_data:
        raise HTTPException(400, "user_id y plan son requeridos")

    # Delete existing plan for this user
    await db.study_plans.delete_many({"user_id": user_id})

    plan_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        **plan_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.study_plans.insert_one(plan_doc)

    return {"message": "Plan guardado exitosamente", "plan_id": plan_doc["id"]}


@planner_router.get("/my-plan/{user_id}")
async def get_my_plan(user_id: str):
    db = get_db()
    plan = await db.study_plans.find_one({"user_id": user_id}, {"_id": 0})
    if not plan:
        return {"plan": None}
    return {"plan": plan}


@planner_router.put("/complete-activity")
async def complete_activity(data: dict):
    db = get_db()
    user_id = data.get("user_id")
    day_number = data.get("day_number")
    activity_index = data.get("activity_index")
    completed = data.get("completed", True)

    if not user_id or day_number is None or activity_index is None:
        raise HTTPException(400, "user_id, day_number y activity_index son requeridos")

    plan = await db.study_plans.find_one({"user_id": user_id})
    if not plan:
        raise HTTPException(404, "Plan no encontrado")

    # Find the day and update activity
    for day in plan["daily_plan"]:
        if day["day_number"] == day_number:
            if 0 <= activity_index < len(day["activities"]):
                day["activities"][activity_index]["completed"] = completed
                break
            else:
                raise HTTPException(400, "Índice de actividad inválido")

    await db.study_plans.update_one(
        {"user_id": user_id},
        {"$set": {
            "daily_plan": plan["daily_plan"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    return {"message": "Actividad actualizada"}


@planner_router.get("/progress/{user_id}")
async def get_progress(user_id: str):
    db = get_db()
    plan = await db.study_plans.find_one({"user_id": user_id}, {"_id": 0})
    if not plan:
        return {"progress": None}

    daily_plan = plan.get("daily_plan", [])

    # Global progress
    total = 0
    completed = 0
    # By area
    area_progress = {}
    # By subtema
    subtema_progress = {}
    # By type
    type_progress = {}

    for day in daily_plan:
        for act in day.get("activities", []):
            total += 1
            is_done = act.get("completed", False)
            if is_done:
                completed += 1

            area = act.get("area", "Otros")
            subtema = act.get("subtema", "General")
            atype = act.get("type", "unknown")

            # Area
            if area not in area_progress:
                area_progress[area] = {"total": 0, "completed": 0}
            area_progress[area]["total"] += 1
            if is_done:
                area_progress[area]["completed"] += 1

            # Subtema
            key = f"{area}|{subtema}"
            if key not in subtema_progress:
                subtema_progress[key] = {"area": area, "subtema": subtema, "total": 0, "completed": 0}
            subtema_progress[key]["total"] += 1
            if is_done:
                subtema_progress[key]["completed"] += 1

            # Type
            if atype not in type_progress:
                type_progress[atype] = {"total": 0, "completed": 0}
            type_progress[atype]["total"] += 1
            if is_done:
                type_progress[atype]["completed"] += 1

    return {
        "progress": {
            "global": {"total": total, "completed": completed, "percent": round(completed / max(total, 1) * 100, 1)},
            "by_area": area_progress,
            "by_subtema": list(subtema_progress.values()),
            "by_type": type_progress,
        }
    }


@planner_router.post("/recalculate")
async def recalculate_plan(data: dict):
    db = get_db()
    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(400, "user_id es requerido")

    plan = await db.study_plans.find_one({"user_id": user_id}, {"_id": 0})
    if not plan:
        raise HTTPException(404, "Plan no encontrado")

    # Collect completed activities
    completed_ids = set()
    for day in plan.get("daily_plan", []):
        for act in day.get("activities", []):
            if act.get("completed"):
                completed_ids.add(f"{act['content_id']}_{act.get('vuelta', 1)}")

    # Adjust start date to today
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end_date = plan["end_date"]

    if today >= end_date:
        raise HTTPException(400, "El plan ya ha finalizado. Crea uno nuevo.")

    # Re-generate from today with same parameters
    new_start = max(today, plan["start_date"])

    req = PlanRequest(
        start_date=new_start,
        end_date=end_date,
        intensity=plan["intensity"],
        rest_day=plan["rest_day"],
    )

    # Gather content again
    structure, simulacros = await gather_content(db)
    queue = build_study_queue(structure)

    total_days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(new_start, "%Y-%m-%d")).days + 1
    total_weeks = math.ceil(total_days / 7)
    rest_days_count = total_weeks if req.rest_day else 0
    effective_days = total_days - rest_days_count

    if effective_days <= 0:
        raise HTTPException(400, "No quedan días efectivos")

    one_pass_load = sum(item["weight"] for item in queue)
    sim_time = len(simulacros) * WEIGHTS["simulacro"]
    available_minutes = effective_days * 480
    available_for_content = available_minutes - sim_time

    vueltas = get_vueltas(req.intensity, available_for_content, one_pass_load)
    vueltas = round(vueltas, 2)

    daily_plan = generate_daily_plan(
        queue, simulacros, effective_days, vueltas,
        datetime.strptime(new_start, "%Y-%m-%d"), req.rest_day, total_days
    )

    # Re-apply completed status
    for day in daily_plan:
        for act in day.get("activities", []):
            key = f"{act['content_id']}_{act.get('vuelta', 1)}"
            if key in completed_ids:
                act["completed"] = True

    total_activities = sum(len(d["activities"]) for d in daily_plan)
    avg_daily_minutes = round(sum(d["total_minutes"] for d in daily_plan if not d["is_rest"]) / max(effective_days, 1), 1)

    # Update plan
    await db.study_plans.update_one(
        {"user_id": user_id},
        {"$set": {
            "start_date": new_start,
            "total_days": total_days,
            "total_weeks": total_weeks,
            "effective_days": effective_days,
            "estimated_vueltas": vueltas,
            "total_activities": total_activities,
            "avg_daily_minutes": avg_daily_minutes,
            "daily_plan": daily_plan,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    updated_plan = await db.study_plans.find_one({"user_id": user_id}, {"_id": 0})
    return {"plan": updated_plan, "message": "Plan recalculado exitosamente"}


@planner_router.delete("/delete/{user_id}")
async def delete_plan(user_id: str):
    db = get_db()
    result = await db.study_plans.delete_many({"user_id": user_id})
    return {"message": "Plan eliminado", "deleted": result.deleted_count}
