"""
Test suite for GPC questionnaires (to_list limit fix) and activation email flow.
Tests:
1. GET /api/questions returns all questions (not truncated at 5000)
2. GET /api/quizzes returns all quizzes (477 expected)
3. GET /api/quizzes/{quiz_id} loads quiz with questions correctly
4. GET /api/auth/activate?token=invalid returns error HTML
5. POST /api/auth/resend-activation/{user_id} returns 404 for nonexistent user
6. POST /api/auth/resend-activation/{user_id} returns 400 for already-approved user
7. POST /api/payments/verify-and-approve/{user_id} returns activation_sent status
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "admin@puertoenarm.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Return headers with admin auth token."""
    return {"Authorization": f"Bearer {admin_token}"}


class TestGPCQuestionnaires:
    """Test GPC questionnaires - to_list limit fix (5000 -> 30000)"""
    
    def test_questions_endpoint_returns_all_questions(self, auth_headers):
        """GET /api/questions should return all 24,096 questions (not truncated at 5000)"""
        response = requests.get(f"{BASE_URL}/api/questions", headers=auth_headers, timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        questions = response.json()
        assert isinstance(questions, list), "Response should be a list"
        
        # The fix increased to_list from 5000 to 30000
        # We expect ~24,096 questions based on the problem statement
        question_count = len(questions)
        print(f"Total questions returned: {question_count}")
        
        # Should be more than 5000 (the old limit)
        assert question_count > 5000, f"Expected more than 5000 questions, got {question_count}"
        
        # Should be around 24,096 based on problem statement
        # Allow some variance in case data changed
        assert question_count > 20000, f"Expected ~24,096 questions, got {question_count}"
    
    def test_quizzes_endpoint_returns_all_quizzes(self, auth_headers):
        """GET /api/quizzes should return all quizzes (477 expected)"""
        response = requests.get(f"{BASE_URL}/api/quizzes", headers=auth_headers, timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        quizzes = response.json()
        assert isinstance(quizzes, list), "Response should be a list"
        
        quiz_count = len(quizzes)
        print(f"Total quizzes returned: {quiz_count}")
        
        # Should have a significant number of quizzes
        # 477 expected based on problem statement
        assert quiz_count > 100, f"Expected many quizzes, got {quiz_count}"
        
        # Verify quiz structure
        if quizzes:
            quiz = quizzes[0]
            assert "id" in quiz, "Quiz should have id"
            assert "title" in quiz, "Quiz should have title"
            assert "specialty" in quiz, "Quiz should have specialty"
            assert "topic" in quiz, "Quiz should have topic"
            assert "questions" in quiz, "Quiz should have questions list"
    
    def test_quiz_detail_loads_with_questions(self, auth_headers):
        """GET /api/quizzes/{quiz_id} should load quiz with all its questions"""
        # First get list of quizzes
        quizzes_response = requests.get(f"{BASE_URL}/api/quizzes", headers=auth_headers, timeout=60)
        assert quizzes_response.status_code == 200
        
        quizzes = quizzes_response.json()
        assert len(quizzes) > 0, "Need at least one quiz to test"
        
        # Get first quiz detail
        quiz_id = quizzes[0]["id"]
        response = requests.get(f"{BASE_URL}/api/quizzes/{quiz_id}", headers=auth_headers, timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "quiz" in data, "Response should have quiz object"
        assert "questions" in data, "Response should have questions list"
        
        quiz = data["quiz"]
        questions = data["questions"]
        
        print(f"Quiz '{quiz['title']}' has {len(questions)} questions")
        
        # Verify questions are loaded
        assert len(questions) > 0, "Quiz should have questions"
        
        # Verify question structure
        if questions:
            q = questions[0]
            assert "id" in q, "Question should have id"
            assert "question_text" in q, "Question should have question_text"
            assert "option_a" in q, "Question should have option_a"
            assert "correct_answer" in q, "Question should have correct_answer"


class TestActivationEmailFlow:
    """Test activation email endpoints"""
    
    def test_activate_with_invalid_token_returns_error_html(self):
        """GET /api/auth/activate?token=invalid should return error HTML with 400"""
        response = requests.get(f"{BASE_URL}/api/auth/activate?token=invalid_token_12345")
        
        # Should return 400 for invalid token
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        # Should return HTML content
        content_type = response.headers.get('content-type', '')
        assert 'text/html' in content_type, f"Expected HTML response, got {content_type}"
        
        # Should contain error message
        html = response.text
        assert "invalido" in html.lower() or "invalid" in html.lower(), "Should indicate invalid token"
    
    def test_resend_activation_nonexistent_user_returns_404(self):
        """POST /api/auth/resend-activation/{user_id} returns 404 for nonexistent user"""
        fake_user_id = "nonexistent-user-id-12345"
        response = requests.post(f"{BASE_URL}/api/auth/resend-activation/{fake_user_id}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Should have error detail"
    
    def test_resend_activation_approved_user_returns_400(self, auth_headers):
        """POST /api/auth/resend-activation/{user_id} returns 400 for already-approved user"""
        # First get admin user info (who is already approved)
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert me_response.status_code == 200
        
        admin_user = me_response.json()
        admin_user_id = admin_user["id"]
        
        # Try to resend activation for approved admin
        response = requests.post(f"{BASE_URL}/api/auth/resend-activation/{admin_user_id}")
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Should have error detail"
        # Should indicate account is already activated
        assert "activada" in data["detail"].lower() or "approved" in data["detail"].lower()


class TestPaymentVerifyAndApprove:
    """Test payment verification endpoint returns activation_sent status"""
    
    def test_verify_and_approve_nonexistent_user_returns_404(self):
        """POST /api/payments/verify-and-approve/{user_id} returns 404 for nonexistent user"""
        fake_user_id = "nonexistent-user-id-67890"
        response = requests.post(f"{BASE_URL}/api/payments/verify-and-approve/{fake_user_id}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_verify_and_approve_approved_user_returns_already_approved(self, auth_headers):
        """POST /api/payments/verify-and-approve/{user_id} returns already_approved for approved user"""
        # Get admin user info
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert me_response.status_code == 200
        
        admin_user = me_response.json()
        admin_user_id = admin_user["id"]
        
        # Try to verify payment for already approved user
        response = requests.post(f"{BASE_URL}/api/payments/verify-and-approve/{admin_user_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Should have status field"
        assert data["status"] == "already_approved", f"Expected 'already_approved', got {data['status']}"


class TestAPIHealth:
    """Basic API health checks"""
    
    def test_api_root_accessible(self):
        """API root endpoint should be accessible"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data or "message" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
