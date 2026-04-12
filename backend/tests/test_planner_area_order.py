"""
Study Planner Area Order Tests - Bug Fix Verification
Tests for verifying the AREA_ORDER fix that was breaking with 'moderado' and 'intenso' intensity.

BUG: When intensity was 'moderado' or 'intenso', multiple 'vueltas' (passes) were concatenated 
without global re-sorting by AREA_ORDER, causing mixed areas within days.

FIX: 
1. Moved AREA_ORDER to module-level constant
2. Added full_queue.sort() by AREA_ORDER after building all vueltas
3. Made leftover distribution prefer same-area days

AREA_ORDER sequence MUST be strictly: 
- Cirugía (0) → Ginecología y Obstetricia (1) → Medicina Interna (2) → Pediatría (3) → Otros (4)

Tests:
- 'leve' intensity: 1 vuelta - verify area order
- 'moderado' intensity: 2 vueltas - THIS WAS THE BUG - verify same strict area order
- 'intenso' intensity: 7+ vueltas - THIS WAS THE BUG - verify same strict area order
- Verify NO day has activities from 2+ different main areas (excluding Simulacro)
"""

import pytest
import requests
import os
from datetime import datetime, timedelta
from collections import defaultdict

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@puertoenarm.com"
TEST_PASSWORD = "admin123"

# The expected strict area order
EXPECTED_AREA_ORDER = ["Cirugía", "Ginecología y Obstetricia", "Medicina Interna", "Pediatría", "Otros"]


class TestPlannerAreaOrder:
    """Test suite for verifying area order bug fix in Study Planner"""

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
    def api_client(self, auth_token):
        """Create API client with auth"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}"
        })
        return session

    def generate_plan_with_intensity(self, api_client, intensity):
        """Generate a plan with specific intensity for testing"""
        # Use the test dates from the bug report: 2026-03-01 to 2027-03-01
        start_date = "2026-03-01"
        end_date = "2027-03-01"
        
        response = api_client.post(f"{BASE_URL}/api/planner/generate", json={
            "start_date": start_date,
            "end_date": end_date,
            "intensity": intensity,
            "rest_day": True
        })
        assert response.status_code == 200, f"Generate plan with intensity '{intensity}' failed: {response.text}"
        return response.json().get("plan")

    def get_area_sequence_from_plan(self, plan):
        """
        Extract the sequence of areas from the plan in order.
        Returns list of (area, day_number) tuples showing area transitions.
        """
        daily_plan = plan.get("daily_plan", [])
        area_sequence = []
        current_area = None
        
        for day in daily_plan:
            if day.get("is_rest"):
                continue
            for act in day.get("activities", []):
                area = act.get("area", "")
                if area == "Simulacro":
                    continue  # Skip simulacros for area order check
                if area != current_area:
                    area_sequence.append((area, day.get("day_number")))
                    current_area = area
        
        return area_sequence

    def verify_strict_area_order(self, area_sequence):
        """
        Verify the area sequence follows the strict AREA_ORDER.
        Returns (is_valid, error_message)
        """
        expected_idx = 0
        for area, day_num in area_sequence:
            if area not in EXPECTED_AREA_ORDER:
                # Unknown area - skip
                continue
            
            actual_idx = EXPECTED_AREA_ORDER.index(area)
            
            # Allow staying at same area or moving forward, NOT backward
            if actual_idx < expected_idx:
                return (False, f"Area '{area}' on day {day_num} breaks order: expected {EXPECTED_AREA_ORDER[expected_idx]} or later, but got {area} (index {actual_idx} < {expected_idx})")
            
            expected_idx = actual_idx
        
        return (True, None)

    def verify_no_mixed_areas_in_days(self, plan):
        """
        Verify no day has activities from 2+ different main areas (excluding Simulacro).
        Returns (is_valid, error_details)
        """
        daily_plan = plan.get("daily_plan", [])
        violations = []
        
        for day in daily_plan:
            if day.get("is_rest"):
                continue
            
            day_num = day.get("day_number")
            areas_in_day = set()
            
            for act in day.get("activities", []):
                area = act.get("area", "")
                if area and area != "Simulacro":
                    areas_in_day.add(area)
            
            if len(areas_in_day) > 1:
                violations.append({
                    "day_number": day_num,
                    "areas_found": list(areas_in_day),
                    "activity_count": len(day.get("activities", []))
                })
        
        return (len(violations) == 0, violations)

    # ────────────────────────────────────────────────────────────────────────────
    # Test: LEVE intensity (1 vuelta) - baseline
    # ────────────────────────────────────────────────────────────────────────────

    def test_leve_intensity_area_order(self, api_client):
        """
        LEVE intensity (1 vuelta) should follow strict area order:
        Cirugía → Ginecología y Obstetricia → Medicina Interna → Pediatría → Otros
        """
        plan = self.generate_plan_with_intensity(api_client, "leve")
        
        # Check vueltas is 1
        vueltas = plan.get("estimated_vueltas", 0)
        assert vueltas == 1.0, f"Expected 1 vuelta for leve intensity, got {vueltas}"
        print(f"✓ Leve intensity: {vueltas} vuelta(s)")
        
        # Get area sequence
        area_sequence = self.get_area_sequence_from_plan(plan)
        areas_seen = [a for a, _ in area_sequence]
        print(f"Area transitions: {areas_seen}")
        
        # Verify strict order
        is_valid, error_msg = self.verify_strict_area_order(area_sequence)
        assert is_valid, f"LEVE intensity broke area order: {error_msg}"
        print(f"✓ Leve intensity maintains strict area order")

    def test_leve_intensity_no_mixed_areas(self, api_client):
        """LEVE intensity should have no days with mixed areas"""
        plan = self.generate_plan_with_intensity(api_client, "leve")
        
        is_valid, violations = self.verify_no_mixed_areas_in_days(plan)
        
        if not is_valid:
            print(f"Found {len(violations)} days with mixed areas:")
            for v in violations[:5]:  # Show first 5
                print(f"  Day {v['day_number']}: {v['areas_found']}")
        
        assert is_valid, f"LEVE intensity has {len(violations)} days with mixed areas"
        print(f"✓ Leve intensity: No days with mixed areas")

    # ────────────────────────────────────────────────────────────────────────────
    # Test: MODERADO intensity (2 vueltas) - THIS WAS THE BUG
    # ────────────────────────────────────────────────────────────────────────────

    def test_moderado_intensity_area_order(self, api_client):
        """
        MODERADO intensity (2 vueltas) should follow SAME strict area order:
        Cirugía → Ginecología y Obstetricia → Medicina Interna → Pediatría → Otros
        
        BUG: Previously, multiple vueltas were concatenated without re-sorting,
        causing Cirugía v1 → Ginecología v1 → ... → Cirugía v2 → Ginecología v2
        
        FIX: Now all Cirugía (v1+v2) comes first, then all Ginecología (v1+v2), etc.
        """
        plan = self.generate_plan_with_intensity(api_client, "moderado")
        
        # Check vueltas is approximately 2
        vueltas = plan.get("estimated_vueltas", 0)
        assert 1.5 <= vueltas <= 2.5, f"Expected ~2 vueltas for moderado intensity, got {vueltas}"
        print(f"✓ Moderado intensity: {vueltas} vuelta(s)")
        
        # Get area sequence
        area_sequence = self.get_area_sequence_from_plan(plan)
        areas_seen = [a for a, _ in area_sequence]
        print(f"Area transitions (first 15): {areas_seen[:15]}")
        
        # Verify strict order
        is_valid, error_msg = self.verify_strict_area_order(area_sequence)
        assert is_valid, f"MODERADO intensity broke area order (THE BUG): {error_msg}"
        print(f"✓ Moderado intensity maintains strict area order (BUG FIXED)")

    def test_moderado_intensity_no_mixed_areas(self, api_client):
        """MODERADO intensity should have no days with mixed areas"""
        plan = self.generate_plan_with_intensity(api_client, "moderado")
        
        is_valid, violations = self.verify_no_mixed_areas_in_days(plan)
        
        if not is_valid:
            print(f"Found {len(violations)} days with mixed areas:")
            for v in violations[:5]:  # Show first 5
                print(f"  Day {v['day_number']}: {v['areas_found']}")
        
        assert is_valid, f"MODERADO intensity has {len(violations)} days with mixed areas"
        print(f"✓ Moderado intensity: No days with mixed areas")

    # ────────────────────────────────────────────────────────────────────────────
    # Test: INTENSO intensity (7+ vueltas) - THIS WAS THE BUG
    # ────────────────────────────────────────────────────────────────────────────

    def test_intenso_intensity_area_order(self, api_client):
        """
        INTENSO intensity (7+ vueltas) should follow SAME strict area order:
        Cirugía → Ginecología y Obstetricia → Medicina Interna → Pediatría → Otros
        
        BUG: Previously, multiple vueltas were concatenated without re-sorting.
        FIX: Now all content is globally sorted by AREA_ORDER after vuelta multiplication.
        """
        plan = self.generate_plan_with_intensity(api_client, "intenso")
        
        # Check vueltas is high
        vueltas = plan.get("estimated_vueltas", 0)
        assert vueltas >= 3, f"Expected 3+ vueltas for intenso intensity, got {vueltas}"
        print(f"✓ Intenso intensity: {vueltas} vuelta(s)")
        
        # Get area sequence
        area_sequence = self.get_area_sequence_from_plan(plan)
        areas_seen = [a for a, _ in area_sequence]
        print(f"Area transitions (first 15): {areas_seen[:15]}")
        
        # Verify strict order
        is_valid, error_msg = self.verify_strict_area_order(area_sequence)
        assert is_valid, f"INTENSO intensity broke area order (THE BUG): {error_msg}"
        print(f"✓ Intenso intensity maintains strict area order (BUG FIXED)")

    def test_intenso_intensity_no_mixed_areas(self, api_client):
        """INTENSO intensity should have no days with mixed areas"""
        plan = self.generate_plan_with_intensity(api_client, "intenso")
        
        is_valid, violations = self.verify_no_mixed_areas_in_days(plan)
        
        if not is_valid:
            print(f"Found {len(violations)} days with mixed areas:")
            for v in violations[:10]:  # Show first 10
                print(f"  Day {v['day_number']}: {v['areas_found']}")
        
        assert is_valid, f"INTENSO intensity has {len(violations)} days with mixed areas"
        print(f"✓ Intenso intensity: No days with mixed areas")

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Plan structure still correct after fix
    # ────────────────────────────────────────────────────────────────────────────

    def test_plan_structure_still_correct(self, api_client):
        """Verify plan generation still returns correct structure after fix"""
        plan = self.generate_plan_with_intensity(api_client, "moderado")
        
        # Check required fields exist
        assert "daily_plan" in plan, "Missing daily_plan"
        assert "start_date" in plan, "Missing start_date"
        assert "end_date" in plan, "Missing end_date"
        assert "intensity" in plan, "Missing intensity"
        assert "total_activities" in plan, "Missing total_activities"
        assert "content_totals" in plan, "Missing content_totals"
        
        # Check daily_plan structure
        daily_plan = plan.get("daily_plan", [])
        assert len(daily_plan) > 0, "daily_plan is empty"
        
        # Check first study day structure
        for day in daily_plan:
            if not day.get("is_rest") and day.get("activities"):
                act = day["activities"][0]
                assert "type" in act, "Activity missing type"
                assert "area" in act, "Activity missing area"
                assert "subtema" in act, "Activity missing subtema"
                assert "title" in act, "Activity missing title"
                assert "content_id" in act, "Activity missing content_id"
                assert "weight" in act, "Activity missing weight"
                assert "completed" in act, "Activity missing completed"
                print(f"✓ Activity structure correct: {act['type']} - {act['area']}")
                break
        
        print(f"✓ Plan structure verified")

    def test_content_counts_still_correct(self, api_client):
        """Verify content counts are still correct (~254 presentations, ~477 cuestionarios, ~557 escape rooms, 10 simulacros)"""
        plan = self.generate_plan_with_intensity(api_client, "leve")  # Use leve for 1 vuelta
        
        content_totals = plan.get("content_totals", {})
        
        assert content_totals.get("presentaciones") == 254, \
            f"Expected 254 presentations, got {content_totals.get('presentaciones')}"
        assert content_totals.get("cuestionarios", 0) >= 470, \
            f"Expected ~477 cuestionarios, got {content_totals.get('cuestionarios')}"
        assert content_totals.get("escape_rooms") == 557, \
            f"Expected 557 escape rooms, got {content_totals.get('escape_rooms')}"
        assert content_totals.get("simulacros") == 10, \
            f"Expected 10 simulacros, got {content_totals.get('simulacros')}"
        
        print(f"✓ Content counts correct: {content_totals}")


class TestPlannerOtherEndpoints:
    """Test other planner endpoints still work after the fix"""

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
        assert response.status_code == 200
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

    def test_save_plan_works(self, api_client, user_id):
        """POST /api/planner/save still works"""
        # First generate a plan
        response = api_client.post(f"{BASE_URL}/api/planner/generate", json={
            "start_date": "2026-03-01",
            "end_date": "2026-06-01",
            "intensity": "leve",
            "rest_day": True
        })
        plan = response.json().get("plan")
        
        # Save it
        save_response = api_client.post(f"{BASE_URL}/api/planner/save", json={
            "user_id": user_id,
            "plan": plan
        })
        assert save_response.status_code == 200, f"Save failed: {save_response.text}"
        print(f"✓ Save plan works")

    def test_get_my_plan_works(self, api_client, user_id):
        """GET /api/planner/my-plan/{user_id} still works"""
        response = api_client.get(f"{BASE_URL}/api/planner/my-plan/{user_id}")
        assert response.status_code == 200, f"Get my-plan failed: {response.text}"
        data = response.json()
        assert "plan" in data
        print(f"✓ Get my-plan works")

    def test_complete_activity_works(self, api_client, user_id):
        """PUT /api/planner/complete-activity still works"""
        # Get the plan
        plan_response = api_client.get(f"{BASE_URL}/api/planner/my-plan/{user_id}")
        plan = plan_response.json().get("plan")
        
        if not plan or not plan.get("daily_plan"):
            pytest.skip("No plan to test")
        
        # Find first study day
        for day in plan["daily_plan"]:
            if not day.get("is_rest") and day.get("activities"):
                response = api_client.put(f"{BASE_URL}/api/planner/complete-activity", json={
                    "user_id": user_id,
                    "day_number": day["day_number"],
                    "activity_index": 0,
                    "completed": True
                })
                assert response.status_code == 200, f"Complete activity failed: {response.text}"
                
                # Toggle back
                api_client.put(f"{BASE_URL}/api/planner/complete-activity", json={
                    "user_id": user_id,
                    "day_number": day["day_number"],
                    "activity_index": 0,
                    "completed": False
                })
                print(f"✓ Complete activity works")
                return
        
        pytest.skip("No study days found")

    def test_get_progress_works(self, api_client, user_id):
        """GET /api/planner/progress/{user_id} still works"""
        response = api_client.get(f"{BASE_URL}/api/planner/progress/{user_id}")
        assert response.status_code == 200, f"Get progress failed: {response.text}"
        data = response.json()
        assert "progress" in data
        print(f"✓ Get progress works")

    def test_delete_plan_works(self, api_client, user_id):
        """DELETE /api/planner/delete/{user_id} still works"""
        response = api_client.delete(f"{BASE_URL}/api/planner/delete/{user_id}")
        assert response.status_code == 200, f"Delete failed: {response.text}"
        print(f"✓ Delete plan works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
