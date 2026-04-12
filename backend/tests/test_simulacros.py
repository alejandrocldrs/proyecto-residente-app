"""
Test suite for Simulacros (Mock Exams) Module

Features tested:
- Admin endpoints: POST /admin/simulacros/import, GET /admin/simulacros, DELETE /admin/simulacros/{id}
- User endpoints: GET /simulacros, GET /simulacros/{id}, POST /simulacros/{id}/start, 
                  POST /simulacros/{id}/save, POST /simulacros/{id}/finish
- GET /simulacros/attempts/{attempt_id}

Note: Simulacro 1 with 280 questions/100 cases already exists.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

class TestSimulacrosAPI:
    """Test Simulacros endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@puertoenarm.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        assert token, "No access token received"
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.admin_token = token
    
    # ==== User Endpoints ====
    
    def test_get_simulacros_list(self):
        """GET /api/simulacros - Should return list of simulacros with user_attempt info"""
        resp = self.session.get(f"{BASE_URL}/api/simulacros")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 1, "Should have at least 1 simulacro (Simulacro 1)"
        
        # Validate simulacro structure
        sim = data[0]
        assert "id" in sim, "Simulacro should have id"
        assert "title" in sim, "Simulacro should have title"
        assert "total_questions" in sim, "Simulacro should have total_questions"
        assert "total_cases" in sim, "Simulacro should have total_cases"
        # user_attempt can be None or object
        print(f"Found {len(data)} simulacro(s): {[s['title'] for s in data]}")
        return data[0]  # Return first simulacro for other tests
    
    def test_get_single_simulacro(self):
        """GET /api/simulacros/{id} - Should return simulacro with questions (no correct_answer)"""
        # First get the list to find a simulacro ID
        list_resp = self.session.get(f"{BASE_URL}/api/simulacros")
        assert list_resp.status_code == 200
        simulacros = list_resp.json()
        assert len(simulacros) > 0, "No simulacros found"
        
        sim_id = simulacros[0]["id"]
        resp = self.session.get(f"{BASE_URL}/api/simulacros/{sim_id}")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        assert "id" in data
        assert "title" in data
        assert "questions" in data
        assert isinstance(data["questions"], list)
        
        # Verify correct_answer is stripped
        if len(data["questions"]) > 0:
            q = data["questions"][0]
            assert "correct_answer" not in q, "correct_answer should be stripped from user-facing endpoint"
            assert "question_text" in q
            assert "option_a" in q
            print(f"Simulacro '{data['title']}' has {len(data['questions'])} questions")
        return sim_id
    
    def test_start_simulacro_creates_attempt(self):
        """POST /api/simulacros/{id}/start - Should create or resume attempt"""
        # Get a simulacro
        list_resp = self.session.get(f"{BASE_URL}/api/simulacros")
        simulacros = list_resp.json()
        sim_id = simulacros[0]["id"]
        
        resp = self.session.post(f"{BASE_URL}/api/simulacros/{sim_id}/start")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        assert "id" in data, "Attempt should have id"
        assert "simulacro_id" in data, "Attempt should have simulacro_id"
        assert "status" in data, "Attempt should have status"
        assert "started_at" in data, "Attempt should have started_at"
        assert "time_limit_seconds" in data, "Attempt should have time_limit_seconds"
        assert data["time_limit_seconds"] == 5 * 3600, "Time limit should be 5 hours"
        
        print(f"Attempt status: {data['status']}, ID: {data['id']}")
        return data
    
    def test_save_simulacro_progress(self):
        """POST /api/simulacros/{id}/save - Should persist answers and marked questions"""
        # Get a simulacro and start attempt
        list_resp = self.session.get(f"{BASE_URL}/api/simulacros")
        sim_id = list_resp.json()[0]["id"]
        
        # Start/resume attempt
        self.session.post(f"{BASE_URL}/api/simulacros/{sim_id}/start")
        
        # Save some progress
        test_answers = {"0": "A", "1": "B", "2": "C"}
        test_marked = [0, 5, 10]
        
        resp = self.session.post(f"{BASE_URL}/api/simulacros/{sim_id}/save", json={
            "answers": test_answers,
            "marked": test_marked
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        assert "message" in resp.json()
        print(f"Progress saved: {test_answers}")
    
    def test_finish_simulacro_calculates_results(self):
        """POST /api/simulacros/{id}/finish - Should calculate and return results"""
        # Get a simulacro
        list_resp = self.session.get(f"{BASE_URL}/api/simulacros")
        sim_id = list_resp.json()[0]["id"]
        
        # Start a fresh attempt (need to handle existing in-progress or completed)
        attempt_resp = self.session.post(f"{BASE_URL}/api/simulacros/{sim_id}/start")
        attempt = attempt_resp.json()
        
        # If already completed, skip this test
        if attempt.get("status") == "completed":
            pytest.skip("Attempt already completed - cannot re-finish")
        
        # Finish with some answers
        test_answers = {"0": "A", "1": "B", "2": "C", "3": "D", "4": "A"}
        
        resp = self.session.post(f"{BASE_URL}/api/simulacros/{sim_id}/finish", json={
            "answers": test_answers
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        # Check results structure
        assert "total_questions" in data, "Results should have total_questions"
        assert "correct_answers" in data, "Results should have correct_answers"
        assert "score_percentage" in data, "Results should have score_percentage"
        assert "by_especialidad" in data, "Results should have by_especialidad breakdown"
        assert "by_tema" in data, "Results should have by_tema breakdown"
        
        print(f"Results: {data['correct_answers']}/{data['total_questions']} ({data['score_percentage']}%)")
        print(f"Especialidades: {list(data['by_especialidad'].keys())}")
    
    # ==== Admin Endpoints ====
    
    def test_admin_get_simulacros(self):
        """GET /api/admin/simulacros - Should return list of all simulacros"""
        resp = self.session.get(f"{BASE_URL}/api/admin/simulacros")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        assert isinstance(data, list)
        print(f"Admin sees {len(data)} simulacro(s)")
        if len(data) > 0:
            assert "id" in data[0]
            assert "title" in data[0]
    
    # ==== Edge Cases ====
    
    def test_get_simulacro_not_found(self):
        """GET /api/simulacros/nonexistent - Should return 404"""
        resp = self.session.get(f"{BASE_URL}/api/simulacros/nonexistent-id-12345")
        assert resp.status_code == 404
    
    def test_simulacro_questions_structure(self):
        """Verify simulacro questions have correct structure"""
        list_resp = self.session.get(f"{BASE_URL}/api/simulacros")
        simulacros = list_resp.json()
        if not simulacros:
            pytest.skip("No simulacros available")
        
        sim_id = simulacros[0]["id"]
        resp = self.session.get(f"{BASE_URL}/api/simulacros/{sim_id}")
        data = resp.json()
        
        questions = data.get("questions", [])
        assert len(questions) > 0, "Should have questions"
        
        # Check question structure
        q = questions[0]
        required_fields = ["index", "question_text", "option_a", "option_b", "option_c", "option_d"]
        for field in required_fields:
            assert field in q, f"Question missing field: {field}"
        
        # Check case_text present
        assert "case_text" in q, "Question should have case_text"
        assert "case_number" in q, "Question should have case_number"
        assert "especialidad" in q, "Question should have especialidad"
        assert "tema" in q, "Question should have tema"
        
        print(f"Question structure verified: index={q['index']}, case={q['case_number']}")


class TestSimulacrosResultsBreakdown:
    """Test results breakdown functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@puertoenarm.com",
            "password": "admin123"
        })
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_results_by_especialidad_structure(self):
        """Verify results by_especialidad has correct format"""
        list_resp = self.session.get(f"{BASE_URL}/api/simulacros")
        simulacros = list_resp.json()
        if not simulacros:
            pytest.skip("No simulacros available")
        
        sim_id = simulacros[0]["id"]
        
        # Check if there's a completed attempt
        attempt_resp = self.session.post(f"{BASE_URL}/api/simulacros/{sim_id}/start")
        attempt = attempt_resp.json()
        
        if attempt.get("status") == "completed" and attempt.get("results"):
            results = attempt["results"]
        else:
            # Finish to get results
            finish_resp = self.session.post(f"{BASE_URL}/api/simulacros/{sim_id}/finish", json={
                "answers": {}
            })
            if finish_resp.status_code == 200:
                results = finish_resp.json()
            else:
                pytest.skip("Cannot get results - attempt status issue")
                return
        
        # Verify by_especialidad structure
        by_esp = results.get("by_especialidad", {})
        for esp_name, esp_data in by_esp.items():
            assert "total" in esp_data, f"Especialidad {esp_name} missing 'total'"
            assert "correct" in esp_data, f"Especialidad {esp_name} missing 'correct'"
            assert "percentage" in esp_data, f"Especialidad {esp_name} missing 'percentage'"
            print(f"  {esp_name}: {esp_data['correct']}/{esp_data['total']} ({esp_data['percentage']}%)")
    
    def test_results_by_tema_structure(self):
        """Verify results by_tema has correct format"""
        list_resp = self.session.get(f"{BASE_URL}/api/simulacros")
        simulacros = list_resp.json()
        if not simulacros:
            pytest.skip("No simulacros available")
        
        sim_id = simulacros[0]["id"]
        
        # Try to finish and get results
        finish_resp = self.session.post(f"{BASE_URL}/api/simulacros/{sim_id}/finish", json={
            "answers": {}
        })
        
        if finish_resp.status_code != 200:
            # May be already completed - try starting to see results
            attempt_resp = self.session.post(f"{BASE_URL}/api/simulacros/{sim_id}/start")
            attempt = attempt_resp.json()
            if attempt.get("results"):
                results = attempt["results"]
            else:
                pytest.skip("Cannot verify tema structure - no results available")
                return
        else:
            results = finish_resp.json()
        
        # Verify by_tema structure
        by_tema = results.get("by_tema", [])
        assert isinstance(by_tema, list), "by_tema should be a list"
        
        if len(by_tema) > 0:
            tema_data = by_tema[0]
            assert "especialidad" in tema_data
            assert "tema" in tema_data
            assert "total" in tema_data
            assert "correct" in tema_data
            assert "percentage" in tema_data
            print(f"Found {len(by_tema)} temas in results")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
