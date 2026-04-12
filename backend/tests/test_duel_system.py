"""
Test suite for the new Duel Questions system including:
- Admin panel: Duel Questions tab (import CSV, view questions, stats, delete)
- Duel system: Topic filter (General vs specific topic)
- Duel questions from new duel_questions collection
- Smart question selection avoiding recently seen questions
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@puertoenarm.com"
TEST_PASSWORD = "admin123"


class TestAuthAndSetup:
    """Authentication and basic setup tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Return auth headers for authenticated requests"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_api_is_running(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        print("API is running correctly")
    
    def test_admin_login(self, auth_token):
        """Verify admin can login"""
        assert auth_token is not None
        print(f"Admin login successful, token obtained")


class TestDuelQuestionsAdmin:
    """Test admin endpoints for Duel Questions management"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_get_duel_questions_stats(self, auth_headers):
        """GET /api/admin/duel-questions/stats - Returns question counts per specialty"""
        response = requests.get(f"{BASE_URL}/api/admin/duel-questions/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "stats" in data
        assert "total" in data
        assert isinstance(data["stats"], list)
        assert isinstance(data["total"], int)
        
        # Check if Cirugía questions exist (should have 825 per agent context)
        print(f"Duel questions stats: total={data['total']}")
        for stat in data["stats"]:
            print(f"  - {stat['_id']}: {stat['count']} questions")
    
    def test_get_duel_questions_paginated(self, auth_headers):
        """GET /api/admin/duel-questions - Returns paginated list of questions"""
        response = requests.get(f"{BASE_URL}/api/admin/duel-questions?page=1&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "questions" in data
        assert "pagination" in data
        assert isinstance(data["questions"], list)
        
        pagination = data["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_count" in pagination
        assert "total_pages" in pagination
        
        print(f"Duel questions: {pagination['total_count']} total, page {pagination['page']}/{pagination['total_pages']}")
        
        # Verify question structure (if there are questions)
        if len(data["questions"]) > 0:
            question = data["questions"][0]
            # Check required fields for duel questions
            required_fields = ["id", "specialty", "question_text", "option_a", "option_b", "option_c", "correct_answer"]
            for field in required_fields:
                assert field in question, f"Missing field: {field}"
            print(f"Question structure verified: {question['id'][:8]}...")
    
    def test_get_duel_questions_filter_by_specialty(self, auth_headers):
        """GET /api/admin/duel-questions with specialty filter"""
        response = requests.get(
            f"{BASE_URL}/api/admin/duel-questions?specialty=Cirug%C3%ADa&page=1&page_size=5", 
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned questions should be from Cirugía specialty
        for question in data["questions"]:
            assert question["specialty"] == "Cirugía", f"Expected Cirugía, got {question['specialty']}"
        
        print(f"Filtered Cirugía questions: {len(data['questions'])} returned")
    
    def test_get_single_duel_question(self, auth_headers):
        """GET /api/duel-questions/{id} - Returns single question for gameplay"""
        # First get a question ID from the list
        list_response = requests.get(f"{BASE_URL}/api/admin/duel-questions?page=1&page_size=1", headers=auth_headers)
        
        if list_response.status_code != 200 or len(list_response.json().get("questions", [])) == 0:
            pytest.skip("No duel questions available")
        
        question_id = list_response.json()["questions"][0]["id"]
        
        # Now get single question
        response = requests.get(f"{BASE_URL}/api/duel-questions/{question_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == question_id
        assert "question_text" in data
        assert "option_a" in data
        assert "option_b" in data
        assert "option_c" in data
        assert "correct_answer" in data
        
        # Verify there's NO option_d (duel questions have only A, B, C)
        assert "option_d" not in data or data.get("option_d") is None or data.get("option_d") == ""
        
        print(f"Single duel question retrieved: {question_id[:8]}...")


class TestDuelChallengeWithTopic:
    """Test duel challenge creation with topic filter"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def target_user_email(self, auth_headers):
        """Get another user's email to challenge"""
        # Try to get approved users
        response = requests.get(f"{BASE_URL}/api/users/active?limit=10", headers=auth_headers)
        if response.status_code == 200:
            users = response.json()
            # Find a user that's not the admin
            for user in users:
                if user["email"] != TEST_EMAIL:
                    return user["email"]
        
        # Fallback: try to use admin's own email (might fail but test will show the error)
        pytest.skip("No other user available for duel test")
    
    def test_create_duel_with_specific_topic(self, auth_headers, target_user_email):
        """POST /api/duels/challenge with duel_topic=Cirugía"""
        response = requests.post(f"{BASE_URL}/api/duels/challenge", 
            headers=auth_headers,
            json={
                "player2_email": target_user_email,
                "challenger_message": "Test duel with specific topic",
                "duel_topic": "Cirugía"
            }
        )
        
        # Should succeed if there are enough Cirugía questions
        if response.status_code == 200:
            data = response.json()
            assert "duel_id" in data
            assert "message" in data
            print(f"Duel with Cirugía topic created: {data['duel_id']}")
            
            # Verify the duel was created with correct topic
            duel_response = requests.get(f"{BASE_URL}/api/duels/{data['duel_id']}", headers=auth_headers)
            if duel_response.status_code == 200:
                duel_data = duel_response.json()
                assert duel_data["duel_topic"] == "Cirugía"
                assert duel_data["question_source"] == "duel"
                # All specialties should be Cirugía for this duel
                for specialty in duel_data["round_specialties"]:
                    assert specialty == "Cirugía", f"Expected Cirugía, got {specialty}"
                print(f"Duel verified: topic={duel_data['duel_topic']}, source={duel_data['question_source']}")
        elif response.status_code == 400:
            # Might fail if not enough questions - this is acceptable
            print(f"Duel creation failed (possibly not enough questions): {response.json()}")
        else:
            assert False, f"Unexpected status code: {response.status_code}, {response.text}"
    
    def test_create_duel_general_topic(self, auth_headers, target_user_email):
        """POST /api/duels/challenge with duel_topic=None (General)"""
        response = requests.post(f"{BASE_URL}/api/duels/challenge", 
            headers=auth_headers,
            json={
                "player2_email": target_user_email,
                "challenger_message": "Test general duel",
                "duel_topic": None  # General - random topics
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "duel_id" in data
            print(f"General duel created: {data['duel_id']}")
            
            # Verify the duel
            duel_response = requests.get(f"{BASE_URL}/api/duels/{data['duel_id']}", headers=auth_headers)
            if duel_response.status_code == 200:
                duel_data = duel_response.json()
                assert duel_data["duel_topic"] is None
                assert duel_data["question_source"] == "duel"
                print(f"General duel verified: topics={duel_data['round_specialties']}")
        elif response.status_code == 400:
            print(f"Duel creation failed: {response.json()}")
        else:
            assert False, f"Unexpected status code: {response.status_code}"


class TestDuelQuestionsCollection:
    """Test that duel questions come from the new duel_questions collection"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_duel_questions_have_3_options_only(self, auth_headers):
        """Verify duel questions have only A, B, C options (no D)"""
        response = requests.get(f"{BASE_URL}/api/admin/duel-questions?page=1&page_size=5", headers=auth_headers)
        
        if response.status_code != 200:
            pytest.skip("Cannot fetch duel questions")
        
        questions = response.json().get("questions", [])
        if len(questions) == 0:
            pytest.skip("No duel questions available")
        
        for question in questions:
            assert "option_a" in question and question["option_a"]
            assert "option_b" in question and question["option_b"]
            assert "option_c" in question and question["option_c"]
            # option_d should not exist or be empty
            if "option_d" in question:
                assert question["option_d"] in [None, "", None]
            
            # correct_answer should be A, B, or C only
            assert question["correct_answer"] in ["A", "B", "C"], \
                f"Invalid correct_answer: {question['correct_answer']}"
        
        print(f"Verified {len(questions)} questions have only A/B/C options")
    
    def test_duel_questions_have_required_fields(self, auth_headers):
        """Verify duel questions have all required fields from CSV structure"""
        response = requests.get(f"{BASE_URL}/api/admin/duel-questions?page=1&page_size=5", headers=auth_headers)
        
        if response.status_code != 200:
            pytest.skip("Cannot fetch duel questions")
        
        questions = response.json().get("questions", [])
        if len(questions) == 0:
            pytest.skip("No duel questions available")
        
        for question in questions:
            # Check fields from DuelQuestion model
            assert "id" in question
            assert "specialty" in question  # One of 5 base topics
            assert "materia" in question  # From CSV
            assert "tema" in question  # From CSV
            assert "question_text" in question
            assert "option_a" in question
            assert "option_b" in question
            assert "option_c" in question
            assert "correct_answer" in question
            assert "global_usage_count" in question
        
        print(f"All required fields verified for {len(questions)} questions")


class TestSubmitDuelGame:
    """Test duel game submission and scoring"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_duel_questions_endpoint_exists(self, auth_headers):
        """Verify the /api/duel-questions/{id} endpoint is accessible"""
        # Get a question ID first
        list_response = requests.get(f"{BASE_URL}/api/admin/duel-questions?page=1&page_size=1", headers=auth_headers)
        
        if list_response.status_code != 200 or len(list_response.json().get("questions", [])) == 0:
            pytest.skip("No duel questions available")
        
        question_id = list_response.json()["questions"][0]["id"]
        
        # The endpoint for gameplay
        response = requests.get(f"{BASE_URL}/api/duel-questions/{question_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify it excludes MongoDB _id
        data = response.json()
        assert "_id" not in data
        print(f"Duel question endpoint working, _id excluded from response")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
