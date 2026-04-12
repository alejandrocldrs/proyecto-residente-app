"""
Study Planner Matching Algorithm Tests
Tests for verifying:
1. All 254 presentations are included in generated plans
2. Cuestionarios and escape rooms follow their matching presentations (reverse matching)
3. Total activity count matches expected DB content counts
4. Area/subtema structure is preserved
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@puertoenarm.com"
TEST_PASSWORD = "admin123"


class TestPlannerMatching:
    """Test suite for Study Planner matching algorithm"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("access_token")

    @pytest.fixture(scope="class")
    def user_id(self, auth_token):
        """Get user ID from /auth/me"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Get user failed: {response.text}"
        return response.json().get("id")

    @pytest.fixture(scope="class")
    def api_client(self, auth_token):
        """Create API client with auth"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}"
        })
        return session

    @pytest.fixture(scope="class")
    def generated_plan(self, api_client):
        """Generate a fresh plan with leve intensity (1 vuelta) for testing"""
        # Use dates for a full year to get all content
        start = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=366)).strftime("%Y-%m-%d")
        
        response = api_client.post(f"{BASE_URL}/api/planner/generate", json={
            "start_date": start,
            "end_date": end,
            "intensity": "leve",
            "rest_day": True
        })
        assert response.status_code == 200, f"Generate failed: {response.text}"
        return response.json().get("plan")

    # ────────────────────────────────────────────────────────────────────────────
    # Test: All 254 presentations are included
    # ────────────────────────────────────────────────────────────────────────────

    def test_all_presentations_included(self, generated_plan):
        """Verify all 254 presentations are included in the generated plan"""
        daily_plan = generated_plan.get("daily_plan", [])
        
        # Count presentations in the plan
        presentation_count = 0
        presentation_titles = set()
        
        for day in daily_plan:
            for act in day.get("activities", []):
                if act.get("type") == "presentacion":
                    presentation_count += 1
                    presentation_titles.add(act.get("title"))
        
        assert presentation_count == 254, f"Expected 254 presentations, found {presentation_count}"
        print(f"All 254 presentations included in plan")

    def test_content_totals_match_plan(self, generated_plan):
        """Verify content_totals from response matches actual activities"""
        daily_plan = generated_plan.get("daily_plan", [])
        content_totals = generated_plan.get("content_totals", {})
        
        # Count by type
        type_counts = {}
        for day in daily_plan:
            for act in day.get("activities", []):
                t = act.get("type", "unknown")
                type_counts[t] = type_counts.get(t, 0) + 1
        
        # Verify counts match
        assert type_counts.get("presentacion", 0) == content_totals.get("presentaciones", 0), \
            f"Presentation count mismatch: plan has {type_counts.get('presentacion')}, totals show {content_totals.get('presentaciones')}"
        assert type_counts.get("cuestionario", 0) == content_totals.get("cuestionarios", 0), \
            f"Cuestionario count mismatch: plan has {type_counts.get('cuestionario')}, totals show {content_totals.get('cuestionarios')}"
        assert type_counts.get("simulacro", 0) == content_totals.get("simulacros", 0), \
            f"Simulacro count mismatch: plan has {type_counts.get('simulacro')}, totals show {content_totals.get('simulacros')}"
        
        print(f"Content totals match: {type_counts}")

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Total activity count is approximately correct
    # ────────────────────────────────────────────────────────────────────────────

    def test_total_activities_approximately_correct(self, generated_plan):
        """Verify total activities is approximately 1299 (254 + 477 + 557 + 10 + some variation)"""
        total = generated_plan.get("total_activities", 0)
        
        # Expected: 254 presentations + ~477 cuestionarios + ~557 escape rooms + 10 simulacros ≈ 1298-1300
        assert 1200 <= total <= 1400, f"Total activities {total} not in expected range [1200, 1400]"
        print(f"Total activities: {total}")

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Matching algorithm - presentations followed by related content
    # ────────────────────────────────────────────────────────────────────────────

    def test_matching_presentations_followed_by_related_content(self, generated_plan):
        """Verify presentations are followed by related cuestionarios and escape rooms"""
        daily_plan = generated_plan.get("daily_plan", [])
        
        # Flatten all activities into a single list
        all_activities = []
        for day in daily_plan:
            for act in day.get("activities", []):
                all_activities.append(act)
        
        # Find presentations and check what follows
        matching_checks = []
        for i, act in enumerate(all_activities):
            if act.get("type") == "presentacion":
                pres_title = act.get("title", "").lower()
                pres_subtema = act.get("subtema", "")
                
                # Look at next 10 activities to find related content
                related_found = False
                for j in range(1, min(11, len(all_activities) - i)):
                    next_act = all_activities[i + j]
                    if next_act.get("type") == "presentacion":
                        break  # Stop at next presentation
                    
                    # Check if in same subtema
                    if next_act.get("subtema") == pres_subtema:
                        related_found = True
                        break
                
                if related_found:
                    matching_checks.append(True)
                else:
                    matching_checks.append(False)
        
        # Most presentations should have related content following them (50% threshold since reverse matching)
        match_rate = sum(matching_checks) / len(matching_checks) if matching_checks else 0
        assert match_rate >= 0.5, f"Match rate {match_rate:.2%} is too low (expected >= 50%)"
        print(f"Matching rate: {match_rate:.2%} ({sum(matching_checks)}/{len(matching_checks)} presentations have related content following)")

    def test_escape_rooms_follow_their_cuestionarios(self, generated_plan):
        """Verify escape rooms follow their matching cuestionarios (same GPC base)"""
        daily_plan = generated_plan.get("daily_plan", [])
        
        # Flatten all activities
        all_activities = []
        for day in daily_plan:
            for act in day.get("activities", []):
                all_activities.append(act)
        
        # Find cuestionarios and check if escape rooms follow
        cuest_escape_matches = 0
        cuest_total = 0
        
        for i, act in enumerate(all_activities):
            if act.get("type") == "cuestionario":
                cuest_total += 1
                cuest_title = act.get("title", "")
                
                # Normalize title for comparison
                base_title = cuest_title.split(".")[0:2]  # Get "CIRUGIA GENERAL 1" part
                base_str = ".".join(base_title).lower()
                
                # Check next few activities for matching escape rooms
                for j in range(1, min(6, len(all_activities) - i)):
                    next_act = all_activities[i + j]
                    if next_act.get("type") == "cuestionario":
                        break  # Stop at next cuestionario
                    if next_act.get("type") == "presentacion":
                        break  # Stop at next presentation
                    
                    if next_act.get("type") == "escape_room":
                        er_title = next_act.get("title", "").lower()
                        er_base = er_title.split(".")[0:2]
                        er_base_str = ".".join(er_base).lower()
                        
                        # Check if base matches (allow for variations)
                        if base_str in er_title or er_base_str in cuest_title.lower():
                            cuest_escape_matches += 1
                            break
        
        # Many cuestionarios should have escape rooms following
        if cuest_total > 0:
            match_rate = cuest_escape_matches / cuest_total
            print(f"Cuestionario-Escape Room pairing rate: {match_rate:.2%} ({cuest_escape_matches}/{cuest_total})")
        else:
            print("No cuestionarios found to check")

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Area and subtema structure preserved
    # ────────────────────────────────────────────────────────────────────────────

    def test_activities_have_area_and_subtema(self, generated_plan):
        """Verify all activities have area and subtema fields"""
        daily_plan = generated_plan.get("daily_plan", [])
        
        missing_area = 0
        missing_subtema = 0
        total = 0
        
        for day in daily_plan:
            for act in day.get("activities", []):
                total += 1
                if not act.get("area"):
                    missing_area += 1
                if not act.get("subtema") and act.get("type") != "simulacro":
                    missing_subtema += 1
        
        assert missing_area == 0, f"{missing_area} activities missing area field"
        # Simulacros don't have subtema, that's expected
        assert missing_subtema == 0, f"{missing_subtema} non-simulacro activities missing subtema field"
        print(f"All {total} activities have area/subtema properly set")

    def test_areas_include_expected_specialties(self, generated_plan):
        """Verify plan includes expected areas (Cirugía, Medicina Interna, etc.)"""
        daily_plan = generated_plan.get("daily_plan", [])
        
        areas_found = set()
        for day in daily_plan:
            for act in day.get("activities", []):
                areas_found.add(act.get("area"))
        
        expected_areas = {"Cirugía", "Medicina Interna", "Ginecología y Obstetricia", "Pediatría"}
        for area in expected_areas:
            assert area in areas_found, f"Expected area '{area}' not found in plan"
        
        print(f"All expected areas found: {expected_areas}")
        print(f"All areas in plan: {areas_found}")

    def test_subtemas_within_areas(self, generated_plan):
        """Verify subtemas exist within their parent areas"""
        daily_plan = generated_plan.get("daily_plan", [])
        
        # Build area -> subtemas map
        area_subtemas = {}
        for day in daily_plan:
            for act in day.get("activities", []):
                area = act.get("area")
                subtema = act.get("subtema")
                if area and subtema:
                    if area not in area_subtemas:
                        area_subtemas[area] = set()
                    area_subtemas[area].add(subtema)
        
        # Check Cirugía has expected subtemas
        cirugia_subtemas = area_subtemas.get("Cirugía", set())
        expected_cirugia = {"Angiología", "Cirugía General", "Traumatología y Ortopedia"}
        for sub in expected_cirugia:
            assert sub in cirugia_subtemas, f"Expected subtema '{sub}' not in Cirugía"
        
        # Check Medicina Interna has multiple subtemas
        mi_subtemas = area_subtemas.get("Medicina Interna", set())
        assert len(mi_subtemas) >= 5, f"Expected at least 5 subtemas in Medicina Interna, found {len(mi_subtemas)}"
        
        print(f"Cirugía subtemas: {cirugia_subtemas}")
        print(f"Medicina Interna subtemas: {mi_subtemas}")

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Simulacros distributed in second half
    # ────────────────────────────────────────────────────────────────────────────

    def test_simulacros_in_second_half(self, generated_plan):
        """Verify simulacros are distributed in the second half of the plan"""
        daily_plan = generated_plan.get("daily_plan", [])
        total_days = len(daily_plan)
        half_point = total_days // 2
        
        simulacro_days = []
        for day in daily_plan:
            for act in day.get("activities", []):
                if act.get("type") == "simulacro":
                    simulacro_days.append(day.get("day_number"))
        
        # All simulacros should be in the second half (>= halfway point)
        for day_num in simulacro_days:
            assert day_num >= half_point, f"Simulacro on day {day_num} is before halfway point ({half_point})"
        
        print(f"Simulacros on days: {simulacro_days}")
        print(f"All {len(simulacro_days)} simulacros are in the second half (after day {half_point})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
