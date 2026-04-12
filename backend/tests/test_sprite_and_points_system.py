"""
Test file for Camino del Médico - Sprite and Points System Testing

Tests:
1. All 34 sprite files (17 ranks x 2 genders) are accessible via HTTP
2. GET /api/points/me returns correct rank based on user points
3. POST /api/admin/set-points correctly changes user points and returns new rank
4. POST /api/auth/update-gender switches between male/female
5. All 17 rank thresholds map to correct rank keys
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# All 17 ranks with their thresholds and keys
RANKS = [
    {"key": "estudiante_de_medicina", "name": "Estudiante de Medicina", "points": 0},
    {"key": "interno_de_pregrado", "name": "Interno de Pregrado", "points": 200},
    {"key": "medico_pasante", "name": "Médico Pasante de Servicio Social", "points": 600},
    {"key": "medico_general", "name": "Médico General", "points": 1200},
    {"key": "residente_primer_ano", "name": "Residente de Primer Año", "points": 2000},
    {"key": "residente_ultimo_ano", "name": "Residente de Último Año", "points": 3200},
    {"key": "jefe_de_residentes", "name": "Jefe de Residentes", "points": 5000},
    {"key": "medico_especialista", "name": "Médico Especialista", "points": 8000},
    {"key": "subespecialista", "name": "Subespecialista", "points": 14000},
    {"key": "alta_especialidad", "name": "Alta Especialidad", "points": 30000},
    {"key": "maestria_ciencias", "name": "Maestría en Ciencias Médicas", "points": 50000},
    {"key": "doctorado_ciencias", "name": "Doctorado en Ciencias Médicas", "points": 80000},
    {"key": "jefe_de_servicio", "name": "Jefe de Servicio", "points": 120000},
    {"key": "director_hospital", "name": "Director de Hospital", "points": 180000},
    {"key": "secretario_salud", "name": "Secretario de Salud", "points": 260000},
    {"key": "director_oms", "name": "Director General de la OMS", "points": 400000},
    {"key": "premio_nobel", "name": "Premio Nobel de Medicina", "points": 700000},
]

GENDERS = ["male", "female"]

@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@puertoenarm.com",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, f"No access_token in response: {data}"
    return data["access_token"]


class TestSpriteAccessibility:
    """Test all 34 sprite files are accessible via HTTP"""
    
    @pytest.mark.parametrize("rank", RANKS)
    @pytest.mark.parametrize("gender", GENDERS)
    def test_sprite_accessible(self, rank, gender):
        """Test that each sprite file is accessible at /sprites/{rank_key}_{gender}.png"""
        sprite_url = f"{BASE_URL}/sprites/{rank['key']}_{gender}.png"
        response = requests.get(sprite_url)
        assert response.status_code == 200, f"Sprite not found: {sprite_url}"
        assert response.headers.get('content-type', '').startswith('image/'), \
            f"Invalid content type for {sprite_url}: {response.headers.get('content-type')}"
        assert len(response.content) > 1000, f"Sprite file too small: {sprite_url}"
        print(f"✓ Sprite accessible: {rank['key']}_{gender}.png ({len(response.content)} bytes)")


class TestPointsAPI:
    """Test the points/rank API endpoints"""
    
    def test_get_points_me_returns_rank_info(self, admin_token):
        """GET /api/points/me returns correct rank based on user points"""
        response = requests.get(
            f"{BASE_URL}/api/points/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "total_points" in data, "Missing total_points"
        assert "current_rank" in data, "Missing current_rank"
        assert "next_rank" in data, "Missing next_rank"
        assert "all_ranks" in data, "Missing all_ranks"
        
        # Verify rank structure
        current_rank = data["current_rank"]
        assert "key" in current_rank, "Missing key in current_rank"
        assert "name" in current_rank, "Missing name in current_rank"
        assert "points" in current_rank, "Missing points in current_rank"
        
        print(f"✓ GET /api/points/me: total_points={data['total_points']}, rank={current_rank['name']}")
    
    def test_all_17_ranks_present_in_response(self, admin_token):
        """Verify all 17 ranks are returned in the all_ranks field"""
        response = requests.get(
            f"{BASE_URL}/api/points/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        all_ranks = data["all_ranks"]
        assert len(all_ranks) == 17, f"Expected 17 ranks, got {len(all_ranks)}"
        
        # Verify each rank key and threshold matches
        for i, expected_rank in enumerate(RANKS):
            actual_rank = all_ranks[i]
            assert actual_rank["key"] == expected_rank["key"], \
                f"Rank {i} key mismatch: expected {expected_rank['key']}, got {actual_rank['key']}"
            assert actual_rank["points"] == expected_rank["points"], \
                f"Rank {expected_rank['key']} points mismatch: expected {expected_rank['points']}, got {actual_rank['points']}"
        
        print(f"✓ All 17 ranks present with correct keys and thresholds")


class TestAdminSetPoints:
    """Test the admin set-points endpoint"""
    
    def test_admin_set_points_basic(self, admin_token):
        """POST /api/admin/set-points correctly changes user points"""
        # Set points to a specific value
        test_points = 5500  # Should be Jefe de Residentes (5000-7999)
        
        response = requests.post(
            f"{BASE_URL}/api/admin/set-points",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"points": test_points}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["total_points"] == test_points, f"Points not set correctly: {data}"
        assert "current_rank" in data, "Missing current_rank"
        assert data["current_rank"]["key"] == "jefe_de_residentes", \
            f"Wrong rank for {test_points} points: {data['current_rank']}"
        
        print(f"✓ Admin set points to {test_points}, rank={data['current_rank']['name']}")
    
    @pytest.mark.parametrize("rank", RANKS)
    def test_admin_set_points_all_ranks(self, admin_token, rank):
        """Test setting points for each rank threshold returns correct rank"""
        # Use exact threshold + 1 to ensure we're in that rank
        test_points = rank["points"] + 1 if rank["points"] > 0 else 0
        
        response = requests.post(
            f"{BASE_URL}/api/admin/set-points",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"points": test_points}
        )
        assert response.status_code == 200, f"Failed for {rank['key']}: {response.text}"
        data = response.json()
        
        assert data["current_rank"]["key"] == rank["key"], \
            f"Wrong rank for {test_points} points: expected {rank['key']}, got {data['current_rank']['key']}"
        
        print(f"✓ Points {test_points} -> Rank {rank['key']}")
    
    def test_admin_set_points_returns_new_rank(self, admin_token):
        """Verify set-points returns the new rank information"""
        response = requests.post(
            f"{BASE_URL}/api/admin/set-points",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"points": 89000}  # Doctorado en Ciencias Médicas
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "message" in data
        assert "previous_points" in data
        assert "total_points" in data
        assert "current_rank" in data
        assert "next_rank" in data
        
        # Verify rank
        assert data["current_rank"]["key"] == "doctorado_ciencias"
        assert data["next_rank"]["key"] == "jefe_de_servicio"
        
        print(f"✓ Set points to 89000, rank=doctorado_ciencias, next=jefe_de_servicio")


class TestGenderUpdate:
    """Test the gender update endpoint"""
    
    def test_update_gender_to_male(self, admin_token):
        """POST /api/auth/update-gender switches to male"""
        response = requests.post(
            f"{BASE_URL}/api/auth/update-gender",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"gender": "male"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["gender"] == "male", f"Gender not updated: {data}"
        print(f"✓ Gender updated to male")
    
    def test_update_gender_to_female(self, admin_token):
        """POST /api/auth/update-gender switches to female"""
        response = requests.post(
            f"{BASE_URL}/api/auth/update-gender",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"gender": "female"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["gender"] == "female", f"Gender not updated: {data}"
        print(f"✓ Gender updated to female")
    
    def test_update_gender_invalid_value(self, admin_token):
        """POST /api/auth/update-gender with invalid value returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/auth/update-gender",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"gender": "other"}
        )
        assert response.status_code == 400, f"Expected 400 for invalid gender: {response.status_code}"
        print(f"✓ Invalid gender rejected with 400")
    
    def test_gender_persists_after_update(self, admin_token):
        """Verify gender change persists in /api/auth/me"""
        # Set to male
        requests.post(
            f"{BASE_URL}/api/auth/update-gender",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"gender": "male"}
        )
        
        # Verify in /auth/me
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["gender"] == "male", f"Gender not persisted: {data}"
        
        # Set to female
        requests.post(
            f"{BASE_URL}/api/auth/update-gender",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"gender": "female"}
        )
        
        # Verify changed
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["gender"] == "female", f"Gender not updated to female: {data}"
        
        print(f"✓ Gender persists correctly after updates")


class TestRankThresholds:
    """Verify all 17 rank thresholds map correctly"""
    
    def test_rank_threshold_mappings(self, admin_token):
        """Test all rank thresholds from the requirements:
        0=estudiante_de_medicina, 200=interno_de_pregrado, 600=medico_pasante, 
        1200=medico_general, 2000=residente_primer_ano, 3200=residente_ultimo_ano, 
        5000=jefe_de_residentes, 8000=medico_especialista, 14000=subespecialista, 
        30000=alta_especialidad, 50000=maestria_ciencias, 80000=doctorado_ciencias, 
        120000=jefe_de_servicio, 180000=director_hospital, 260000=secretario_salud, 
        400000=director_oms, 700000=premio_nobel
        """
        expected_mappings = {
            0: "estudiante_de_medicina",
            200: "interno_de_pregrado",
            600: "medico_pasante",
            1200: "medico_general",
            2000: "residente_primer_ano",
            3200: "residente_ultimo_ano",
            5000: "jefe_de_residentes",
            8000: "medico_especialista",
            14000: "subespecialista",
            30000: "alta_especialidad",
            50000: "maestria_ciencias",
            80000: "doctorado_ciencias",
            120000: "jefe_de_servicio",
            180000: "director_hospital",
            260000: "secretario_salud",
            400000: "director_oms",
            700000: "premio_nobel"
        }
        
        for points, expected_key in expected_mappings.items():
            response = requests.post(
                f"{BASE_URL}/api/admin/set-points",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"points": points}
            )
            assert response.status_code == 200, f"Failed for {points} points"
            data = response.json()
            
            assert data["current_rank"]["key"] == expected_key, \
                f"Points {points}: expected {expected_key}, got {data['current_rank']['key']}"
            
            print(f"✓ {points} points -> {expected_key}")
        
        print(f"✓ All 17 rank thresholds verified")


# Cleanup: reset admin points to a known state
@pytest.fixture(scope="module", autouse=True)
def cleanup(admin_token):
    """Reset admin points after all tests"""
    yield
    # Reset to initial state (89000 points per agent context)
    requests.post(
        f"{BASE_URL}/api/admin/set-points",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"points": 89000}
    )
    # Reset gender to female (per agent context)
    requests.post(
        f"{BASE_URL}/api/auth/update-gender",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"gender": "female"}
    )
