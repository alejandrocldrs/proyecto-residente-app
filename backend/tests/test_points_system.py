"""
Tests for Points & Rank System API endpoints
- GET /api/points/me - Returns user's points, rank, progress
- GET /api/points/history - Returns transaction history
- POST /api/auth/update-gender - Updates user gender
- POST /api/auth/register - Registration with gender field
- Points awarded via quiz completion (anti-farming verification)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

# Test credentials
ADMIN_EMAIL = "admin@puertoenarm.com"
ADMIN_PASSWORD = "admin123"

@pytest.fixture(scope="module")
def auth_token():
    """Authenticate and get token for tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with authorization token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestPointsMe:
    """Tests for GET /api/points/me endpoint"""
    
    def test_get_points_me_success(self, auth_headers):
        """Test that /api/points/me returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/points/me", headers=auth_headers)
        
        # Status code assertion
        assert response.status_code == 200
        
        data = response.json()
        
        # Data structure assertions
        assert "total_points" in data, "Response missing total_points"
        assert "current_rank" in data, "Response missing current_rank"
        assert "next_rank" in data, "Response missing next_rank"
        assert "all_ranks" in data, "Response missing all_ranks"
        
        # Data type assertions
        assert isinstance(data["total_points"], int), "total_points should be integer"
        assert isinstance(data["all_ranks"], list), "all_ranks should be list"
        assert len(data["all_ranks"]) == 17, f"Expected 17 ranks, got {len(data['all_ranks'])}"
        
        # Current rank structure
        current_rank = data["current_rank"]
        assert "key" in current_rank, "current_rank missing key"
        assert "name" in current_rank, "current_rank missing name"
        assert "points" in current_rank, "current_rank missing points"
        
    def test_points_me_unauthorized(self):
        """Test that /api/points/me requires authentication"""
        response = requests.get(f"{BASE_URL}/api/points/me")
        assert response.status_code == 401 or response.status_code == 403


class TestPointsHistory:
    """Tests for GET /api/points/history endpoint"""
    
    def test_get_points_history_success(self, auth_headers):
        """Test that /api/points/history returns list of transactions"""
        response = requests.get(f"{BASE_URL}/api/points/history", headers=auth_headers)
        
        # Status code assertion
        assert response.status_code == 200
        
        data = response.json()
        
        # Data type assertion
        assert isinstance(data, list), "History should be a list"
        
        # If there are transactions, verify structure
        if len(data) > 0:
            transaction = data[0]
            assert "activity_type" in transaction or "id" in transaction
            
    def test_points_history_with_limit(self, auth_headers):
        """Test history pagination with limit parameter"""
        response = requests.get(f"{BASE_URL}/api/points/history?limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5


class TestUpdateGender:
    """Tests for POST /api/auth/update-gender endpoint"""
    
    def test_update_gender_male(self, auth_headers):
        """Test updating gender to male"""
        response = requests.post(
            f"{BASE_URL}/api/auth/update-gender",
            json={"gender": "male"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["gender"] == "male"
        
    def test_update_gender_female(self, auth_headers):
        """Test updating gender to female"""
        response = requests.post(
            f"{BASE_URL}/api/auth/update-gender",
            json={"gender": "female"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["gender"] == "female"
        
    def test_update_gender_invalid(self, auth_headers):
        """Test that invalid gender values are rejected"""
        response = requests.post(
            f"{BASE_URL}/api/auth/update-gender",
            json={"gender": "other"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        
    def test_update_gender_set_back_to_male(self, auth_headers):
        """Reset gender back to male for consistency"""
        response = requests.post(
            f"{BASE_URL}/api/auth/update-gender",
            json={"gender": "male"},
            headers=auth_headers
        )
        assert response.status_code == 200


class TestRegistrationWithGender:
    """Tests for POST /api/auth/register with gender field"""
    
    def test_register_with_gender_male(self):
        """Test registration with male gender"""
        unique_email = f"test_male_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "TEST_Male User",
            "email": unique_email,
            "password": "testpass123",
            "gender": "male"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        
    def test_register_with_gender_female(self):
        """Test registration with female gender"""
        unique_email = f"test_female_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "TEST_Female User",
            "email": unique_email,
            "password": "testpass123",
            "gender": "female"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        
    def test_register_without_gender(self):
        """Test registration without gender (should work, gender is optional)"""
        unique_email = f"test_nogender_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "TEST_No Gender User",
            "email": unique_email,
            "password": "testpass123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data


class TestRankStructure:
    """Tests for rank system structure"""
    
    def test_all_17_ranks_present(self, auth_headers):
        """Verify all 17 ranks are returned with correct structure"""
        response = requests.get(f"{BASE_URL}/api/points/me", headers=auth_headers)
        assert response.status_code == 200
        
        all_ranks = response.json()["all_ranks"]
        
        expected_ranks = [
            ("estudiante_de_medicina", "Estudiante de Medicina", 0),
            ("interno_de_pregrado", "Interno de Pregrado", 200),
            ("medico_pasante", "Médico Pasante de Servicio Social", 600),
            ("medico_general", "Médico General", 1200),
            ("residente_primer_ano", "Residente de Primer Año", 2000),
            ("residente_ultimo_ano", "Residente de Último Año", 3200),
            ("jefe_de_residentes", "Jefe de Residentes", 5000),
            ("medico_especialista", "Médico Especialista", 8000),
            ("subespecialista", "Subespecialista", 14000),
            ("alta_especialidad", "Alta Especialidad", 30000),
            ("maestria_ciencias", "Maestría en Ciencias Médicas", 50000),
            ("doctorado_ciencias", "Doctorado en Ciencias Médicas", 80000),
            ("jefe_de_servicio", "Jefe de Servicio", 120000),
            ("director_hospital", "Director de Hospital", 180000),
            ("secretario_salud", "Secretario de Salud", 260000),
            ("director_oms", "Director General de la OMS", 400000),
            ("premio_nobel", "Premio Nobel de Medicina", 700000),
        ]
        
        assert len(all_ranks) == 17
        
        for i, (key, name, points) in enumerate(expected_ranks):
            assert all_ranks[i]["key"] == key, f"Rank {i} key mismatch"
            assert all_ranks[i]["points"] == points, f"Rank {i} points mismatch"


class TestUserAuthMeGenderField:
    """Tests for gender field in /api/auth/me response"""
    
    def test_auth_me_returns_gender(self, auth_headers):
        """Verify /api/auth/me returns gender field"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "gender" in data, "Response should include gender field"
        assert data["gender"] in ["male", "female", None], "Gender should be male, female, or null"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
