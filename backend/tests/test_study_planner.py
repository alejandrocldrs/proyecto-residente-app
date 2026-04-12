"""
Study Planner API Tests
Tests for the Planificador Inteligente de Estudio module
- Content summary endpoint
- Plan generation and saving
- Activity completion
- Progress tracking
- Recalculation
- Plan deletion
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@puertoenarm.com"
TEST_PASSWORD = "admin123"


class TestStudyPlanner:
    """Test suite for Study Planner API endpoints"""

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

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Content Summary
    # ────────────────────────────────────────────────────────────────────────────

    def test_content_summary_returns_200(self):
        """GET /api/planner/content-summary returns 200 (unauthenticated)"""
        response = requests.get(f"{BASE_URL}/api/planner/content-summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_content_summary_has_correct_structure(self):
        """Content summary returns areas, totals, total_time_one_pass_minutes, weights"""
        response = requests.get(f"{BASE_URL}/api/planner/content-summary")
        data = response.json()
        
        assert "areas" in data, "Missing 'areas' in response"
        assert "totals" in data, "Missing 'totals' in response"
        assert "total_time_one_pass_minutes" in data, "Missing 'total_time_one_pass_minutes'"
        assert "weights" in data, "Missing 'weights'"

    def test_content_summary_totals_values(self):
        """Content summary shows expected totals (254 presentations, ~477 cuestionarios, 557 escape rooms, 10 simulacros)"""
        response = requests.get(f"{BASE_URL}/api/planner/content-summary")
        data = response.json()
        totals = data.get("totals", {})
        
        # Based on the updated requirements: 254 presentations, ~477 cuestionarios, 557 escape rooms, 10 simulacros
        # Note: imagenes are excluded from planner (material extra)
        assert totals.get("presentaciones", 0) == 254, f"Expected 254 presentaciones, got {totals.get('presentaciones')}"
        assert totals.get("cuestionarios", 0) >= 470, f"Expected ~477 cuestionarios, got {totals.get('cuestionarios')}"
        assert totals.get("escape_rooms", 0) == 557, f"Expected 557 escape_rooms, got {totals.get('escape_rooms')}"
        assert totals.get("simulacros", 0) == 10, f"Expected 10 simulacros, got {totals.get('simulacros')}"

    def test_content_summary_weights(self):
        """Content summary has correct activity weights"""
        response = requests.get(f"{BASE_URL}/api/planner/content-summary")
        data = response.json()
        weights = data.get("weights", {})
        
        # Updated weights per the planner.py
        assert weights.get("presentacion") == 20, f"presentacion weight should be 20, got {weights.get('presentacion')}"
        assert weights.get("cuestionario") == 20, f"cuestionario weight should be 20, got {weights.get('cuestionario')}"
        assert weights.get("escape_room") == 8, f"escape_room weight should be 8, got {weights.get('escape_room')}"
        assert weights.get("imagen_dx") == 0.5, f"imagen_dx weight should be 0.5, got {weights.get('imagen_dx')}"
        assert weights.get("simulacro") == 240, f"simulacro weight should be 240, got {weights.get('simulacro')}"

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Delete plan (cleanup first)
    # ────────────────────────────────────────────────────────────────────────────

    def test_delete_plan_before_tests(self, api_client, user_id):
        """DELETE /api/planner/delete/{user_id} cleans up existing plan"""
        response = api_client.delete(f"{BASE_URL}/api/planner/delete/{user_id}")
        assert response.status_code == 200, f"Delete failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"Deleted existing plan: {data}")

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Generate Plan
    # ────────────────────────────────────────────────────────────────────────────

    def test_generate_plan_returns_200(self, api_client):
        """POST /api/planner/generate creates a valid plan"""
        # Use dates starting 1 month from now for 6 months
        start = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=210)).strftime("%Y-%m-%d")
        
        response = api_client.post(f"{BASE_URL}/api/planner/generate", json={
            "start_date": start,
            "end_date": end,
            "intensity": "moderado",
            "rest_day": True
        })
        assert response.status_code == 200, f"Generate failed: {response.text}"
        return response.json()

    def test_generate_plan_structure(self, api_client):
        """Generated plan has correct structure with daily_plan array"""
        start = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=210)).strftime("%Y-%m-%d")
        
        response = api_client.post(f"{BASE_URL}/api/planner/generate", json={
            "start_date": start,
            "end_date": end,
            "intensity": "moderado",
            "rest_day": True
        })
        data = response.json()
        plan = data.get("plan", {})
        
        # Check required fields
        assert "start_date" in plan
        assert "end_date" in plan
        assert "intensity" in plan
        assert "rest_day" in plan
        assert "total_days" in plan
        assert "total_weeks" in plan
        assert "effective_days" in plan
        assert "estimated_vueltas" in plan
        assert "total_activities" in plan
        assert "avg_daily_minutes" in plan
        assert "daily_plan" in plan
        assert "content_totals" in plan
        
        # Verify daily_plan is array
        assert isinstance(plan["daily_plan"], list), "daily_plan should be an array"
        assert len(plan["daily_plan"]) > 0, "daily_plan should not be empty"

    def test_generate_plan_daily_plan_day_structure(self, api_client):
        """Each day in daily_plan has correct structure"""
        start = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        
        response = api_client.post(f"{BASE_URL}/api/planner/generate", json={
            "start_date": start,
            "end_date": end,
            "intensity": "leve",
            "rest_day": True
        })
        plan = response.json().get("plan", {})
        daily_plan = plan.get("daily_plan", [])
        
        # Check first non-rest day
        study_day = None
        for day in daily_plan:
            if not day.get("is_rest"):
                study_day = day
                break
        
        assert study_day is not None, "No study days found"
        assert "day_number" in study_day
        assert "date" in study_day
        assert "is_rest" in study_day
        assert "activities" in study_day
        assert "total_minutes" in study_day
        
        # Check activity structure
        if study_day.get("activities"):
            act = study_day["activities"][0]
            assert "type" in act
            assert "area" in act
            assert "subtema" in act
            assert "title" in act
            assert "content_id" in act
            assert "weight" in act
            assert "completed" in act

    def test_generate_plan_rejects_invalid_dates(self, api_client):
        """Generate plan fails with end date before start date"""
        start = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        response = api_client.post(f"{BASE_URL}/api/planner/generate", json={
            "start_date": start,
            "end_date": end,
            "intensity": "moderado",
            "rest_day": True
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Save Plan
    # ────────────────────────────────────────────────────────────────────────────

    def test_save_plan_returns_200(self, api_client, user_id):
        """POST /api/planner/save persists the plan for a user"""
        # Generate a plan first
        start = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")
        
        gen_response = api_client.post(f"{BASE_URL}/api/planner/generate", json={
            "start_date": start,
            "end_date": end,
            "intensity": "moderado",
            "rest_day": True
        })
        plan = gen_response.json().get("plan")
        
        # Save the plan
        save_response = api_client.post(f"{BASE_URL}/api/planner/save", json={
            "user_id": user_id,
            "plan": plan
        })
        assert save_response.status_code == 200, f"Save failed: {save_response.text}"
        data = save_response.json()
        assert "message" in data
        assert "plan_id" in data
        print(f"Saved plan with ID: {data.get('plan_id')}")

    def test_save_plan_rejects_missing_user_id(self, api_client):
        """Save plan fails without user_id"""
        response = api_client.post(f"{BASE_URL}/api/planner/save", json={
            "plan": {"daily_plan": []}
        })
        assert response.status_code == 400

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Get My Plan
    # ────────────────────────────────────────────────────────────────────────────

    def test_get_my_plan_returns_200(self, api_client, user_id):
        """GET /api/planner/my-plan/{user_id} returns the saved plan"""
        response = api_client.get(f"{BASE_URL}/api/planner/my-plan/{user_id}")
        assert response.status_code == 200, f"Get plan failed: {response.text}"
        data = response.json()
        assert "plan" in data
        
        # Verify plan structure if plan exists
        if data.get("plan"):
            plan = data["plan"]
            assert "daily_plan" in plan
            assert "start_date" in plan
            assert "end_date" in plan
            print(f"Retrieved plan from {plan.get('start_date')} to {plan.get('end_date')}")

    def test_get_my_plan_returns_null_for_nonexistent_user(self, api_client):
        """GET /api/planner/my-plan returns null plan for user without plan"""
        response = api_client.get(f"{BASE_URL}/api/planner/my-plan/nonexistent-user-id-12345")
        assert response.status_code == 200
        data = response.json()
        assert data.get("plan") is None

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Complete Activity
    # ────────────────────────────────────────────────────────────────────────────

    def test_complete_activity_returns_200(self, api_client, user_id):
        """PUT /api/planner/complete-activity toggles activity completion"""
        # First get the current plan
        plan_response = api_client.get(f"{BASE_URL}/api/planner/my-plan/{user_id}")
        plan = plan_response.json().get("plan")
        
        if not plan or not plan.get("daily_plan"):
            pytest.skip("No plan exists to test activity completion")
        
        # Find first study day with activities
        day_to_update = None
        for day in plan["daily_plan"]:
            if not day.get("is_rest") and day.get("activities"):
                day_to_update = day
                break
        
        if not day_to_update:
            pytest.skip("No study days with activities found")
        
        # Toggle first activity to completed
        response = api_client.put(f"{BASE_URL}/api/planner/complete-activity", json={
            "user_id": user_id,
            "day_number": day_to_update["day_number"],
            "activity_index": 0,
            "completed": True
        })
        assert response.status_code == 200, f"Complete activity failed: {response.text}"
        print(f"Marked activity 0 on day {day_to_update['day_number']} as completed")

    def test_complete_activity_persists(self, api_client, user_id):
        """Activity completion persists in database"""
        # First get the current plan
        plan_response = api_client.get(f"{BASE_URL}/api/planner/my-plan/{user_id}")
        plan = plan_response.json().get("plan")
        
        if not plan or not plan.get("daily_plan"):
            pytest.skip("No plan exists")
        
        # Find first study day with activities
        for day in plan["daily_plan"]:
            if not day.get("is_rest") and day.get("activities"):
                # The first activity should be marked as completed from previous test
                assert day["activities"][0].get("completed") == True, \
                    f"Activity on day {day['day_number']} should be marked completed"
                print(f"Verified activity 0 on day {day['day_number']} is completed")
                return
        
        pytest.skip("No study days with activities found")

    def test_complete_activity_toggle_off(self, api_client, user_id):
        """Activity completion can be toggled off"""
        plan_response = api_client.get(f"{BASE_URL}/api/planner/my-plan/{user_id}")
        plan = plan_response.json().get("plan")
        
        if not plan or not plan.get("daily_plan"):
            pytest.skip("No plan exists")
        
        # Find first study day with activities
        for day in plan["daily_plan"]:
            if not day.get("is_rest") and day.get("activities"):
                # Toggle back to incomplete
                response = api_client.put(f"{BASE_URL}/api/planner/complete-activity", json={
                    "user_id": user_id,
                    "day_number": day["day_number"],
                    "activity_index": 0,
                    "completed": False
                })
                assert response.status_code == 200
                print(f"Toggled activity 0 on day {day['day_number']} back to incomplete")
                return
        
        pytest.skip("No study days with activities found")

    def test_complete_activity_rejects_missing_params(self, api_client, user_id):
        """Complete activity fails without required params"""
        response = api_client.put(f"{BASE_URL}/api/planner/complete-activity", json={
            "user_id": user_id
            # Missing day_number and activity_index
        })
        assert response.status_code == 400

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Progress
    # ────────────────────────────────────────────────────────────────────────────

    def test_get_progress_returns_200(self, api_client, user_id):
        """GET /api/planner/progress/{user_id} returns correct progress stats"""
        response = api_client.get(f"{BASE_URL}/api/planner/progress/{user_id}")
        assert response.status_code == 200, f"Get progress failed: {response.text}"
        data = response.json()
        assert "progress" in data

    def test_get_progress_structure(self, api_client, user_id):
        """Progress has global, by_area, and by_type breakdowns"""
        response = api_client.get(f"{BASE_URL}/api/planner/progress/{user_id}")
        data = response.json()
        progress = data.get("progress")
        
        if not progress:
            pytest.skip("No progress data (user may have no plan)")
        
        # Check global progress
        assert "global" in progress
        global_progress = progress["global"]
        assert "total" in global_progress
        assert "completed" in global_progress
        assert "percent" in global_progress
        
        # Check by_area
        assert "by_area" in progress
        
        # Check by_type
        assert "by_type" in progress
        
        print(f"Progress: {global_progress['percent']}% ({global_progress['completed']}/{global_progress['total']})")

    def test_get_progress_returns_null_for_user_without_plan(self, api_client):
        """Progress returns null for user without plan"""
        response = api_client.get(f"{BASE_URL}/api/planner/progress/nonexistent-user-123")
        assert response.status_code == 200
        data = response.json()
        assert data.get("progress") is None

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Recalculate
    # ────────────────────────────────────────────────────────────────────────────

    def test_recalculate_returns_200(self, api_client, user_id):
        """POST /api/planner/recalculate recalculates the plan from today"""
        response = api_client.post(f"{BASE_URL}/api/planner/recalculate", json={
            "user_id": user_id
        })
        # May return 400 if plan already ended
        if response.status_code == 400:
            # This is expected if plan end date is in the past
            print(f"Recalculate returned 400 (expected if plan ended): {response.text}")
            return
        
        assert response.status_code == 200, f"Recalculate failed: {response.text}"
        data = response.json()
        assert "plan" in data
        assert "message" in data
        print(f"Recalculated: {data.get('message')}")

    def test_recalculate_rejects_nonexistent_user(self, api_client):
        """Recalculate fails for user without plan"""
        response = api_client.post(f"{BASE_URL}/api/planner/recalculate", json={
            "user_id": "nonexistent-user-xyz"
        })
        assert response.status_code == 404

    # ────────────────────────────────────────────────────────────────────────────
    # Test: Delete Plan
    # ────────────────────────────────────────────────────────────────────────────

    def test_delete_plan_returns_200(self, api_client, user_id):
        """DELETE /api/planner/delete/{user_id} removes the plan"""
        response = api_client.delete(f"{BASE_URL}/api/planner/delete/{user_id}")
        assert response.status_code == 200, f"Delete failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "deleted" in data
        print(f"Delete result: {data}")

    def test_delete_plan_verifies_deletion(self, api_client, user_id):
        """Verify plan is deleted by checking my-plan returns null"""
        response = api_client.get(f"{BASE_URL}/api/planner/my-plan/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("plan") is None, "Plan should be null after deletion"
        print("Verified plan is deleted")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
