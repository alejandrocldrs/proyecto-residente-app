"""
ENARM Match API Tests
Tests for ENARM Match module endpoints:
- GET /api/enarm-match/progress
- POST /api/enarm-match/progress
- DELETE /api/enarm-match/progress
- GET /api/enarm-match/results
- POST /api/enarm-match/results
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://subscription-revamp-3.preview.emergentagent.com').rstrip('/')

class TestENARMMatchAPI:
    """ENARM Match endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@puertoenarm.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping tests")
    
    def test_auth_login(self):
        """Test authentication endpoint works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", 
            headers={"Content-Type": "application/json"},
            json={
                "email": "admin@puertoenarm.com",
                "password": "admin123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print("AUTH LOGIN - PASS")
    
    # =========================================================================
    # ENARM Match Progress Endpoints
    # =========================================================================
    
    def test_get_progress_initial(self):
        """Test GET /api/enarm-match/progress - returns empty or existing progress"""
        response = self.session.get(f"{BASE_URL}/api/enarm-match/progress")
        assert response.status_code == 200
        data = response.json()
        # Should return empty dict {} or existing progress
        assert isinstance(data, dict)
        print(f"GET PROGRESS - PASS (data: {data.get('paso', 'empty')})")
    
    def test_post_progress_step0(self):
        """Test POST /api/enarm-match/progress - save initial step"""
        payload = {
            "paso": 0,
            "respuestasPares": [],
            "tolerancias": {
                "guardias": 2,
                "quirofano_sangre": 2,
                "urgencias": 2,
                "rutina": 2,
                "incertidumbre": 2,
                "emocional_intenso": 2,
                "ninos": 2,
                "radiacion": 2
            },
            "subsObjetivo": [],
            "destinoSeleccionado": None,
            "confirmacionTronco": None,
            "noTolerancias": []
        }
        
        response = self.session.post(f"{BASE_URL}/api/enarm-match/progress", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("POST PROGRESS STEP0 - PASS")
    
    def test_post_progress_with_pairs(self):
        """Test POST /api/enarm-match/progress - save progress with pairs answered"""
        payload = {
            "paso": 1,
            "respuestasPares": [
                {"preguntaId": 1, "seleccion": "A", "mapeoA": {"cognitivo": 1}, "mapeoB": {"procedimientos": 1}},
                {"preguntaId": 2, "seleccion": "B", "mapeoA": {"agudo": 1}, "mapeoB": {"longitudinal": 1}}
            ],
            "tolerancias": {
                "guardias": 2,
                "quirofano_sangre": 2,
                "urgencias": 2,
                "rutina": 2,
                "incertidumbre": 2,
                "emocional_intenso": 2,
                "ninos": 2,
                "radiacion": 2
            },
            "subsObjetivo": [],
            "destinoSeleccionado": None,
            "confirmacionTronco": None,
            "noTolerancias": []
        }
        
        response = self.session.post(f"{BASE_URL}/api/enarm-match/progress", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("POST PROGRESS WITH PAIRS - PASS")
        
        # Verify the progress was saved by GET
        get_response = self.session.get(f"{BASE_URL}/api/enarm-match/progress")
        assert get_response.status_code == 200
        saved_data = get_response.json()
        assert saved_data.get("paso") == 1
        assert len(saved_data.get("respuestasPares", [])) == 2
        print("VERIFY PROGRESS SAVED - PASS")
    
    def test_post_progress_full_wizard(self):
        """Test POST /api/enarm-match/progress - save complete wizard progress"""
        payload = {
            "paso": 4,
            "respuestasPares": [
                {"preguntaId": i, "seleccion": "A" if i % 2 == 0 else "B", 
                 "mapeoA": {"cognitivo": 1}, "mapeoB": {"procedimientos": 1}}
                for i in range(1, 11)  # 10 questions
            ],
            "tolerancias": {
                "guardias": 3,
                "quirofano_sangre": 2,
                "urgencias": 3,
                "rutina": 1,
                "incertidumbre": 2,
                "emocional_intenso": 2,
                "ninos": 3,
                "radiacion": 1
            },
            "subsObjetivo": ["Cardiología", "Gastroenterología", "Neonatología"],
            "destinoSeleccionado": {"destino_id": "D02", "destino_nombre": "Cardiología Clínica"},
            "confirmacionTronco": None,
            "noTolerancias": []
        }
        
        response = self.session.post(f"{BASE_URL}/api/enarm-match/progress", json=payload)
        assert response.status_code == 200
        print("POST PROGRESS FULL WIZARD - PASS")
    
    def test_delete_progress(self):
        """Test DELETE /api/enarm-match/progress - clear progress"""
        # First save some progress
        payload = {"paso": 1, "respuestasPares": [], "tolerancias": {}, "subsObjetivo": []}
        self.session.post(f"{BASE_URL}/api/enarm-match/progress", json=payload)
        
        # Delete progress
        response = self.session.delete(f"{BASE_URL}/api/enarm-match/progress")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("DELETE PROGRESS - PASS")
        
        # Verify deleted
        get_response = self.session.get(f"{BASE_URL}/api/enarm-match/progress")
        assert get_response.status_code == 200
        assert get_response.json() == {} or "paso" not in get_response.json()
        print("VERIFY PROGRESS DELETED - PASS")
    
    # =========================================================================
    # ENARM Match Results Endpoints
    # =========================================================================
    
    def test_get_results_initial(self):
        """Test GET /api/enarm-match/results - returns results history"""
        response = self.session.get(f"{BASE_URL}/api/enarm-match/results")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"GET RESULTS - PASS (count: {len(data)})")
    
    def test_post_results(self):
        """Test POST /api/enarm-match/results - save final results"""
        payload = {
            "respuestasPares": [
                {"preguntaId": i, "seleccion": "A" if i % 2 == 0 else "B", 
                 "mapeoA": {"cognitivo": 1}, "mapeoB": {"procedimientos": 1}}
                for i in range(1, 11)
            ],
            "tolerancias": {
                "guardias": 3,
                "quirofano_sangre": 2,
                "urgencias": 3,
                "rutina": 1,
                "incertidumbre": 2,
                "emocional_intenso": 2,
                "ninos": 3,
                "radiacion": 1
            },
            "subsObjetivo": ["Cardiología", "Neonatología", "Nefrología"],
            "destinoSeleccionado": "D02",
            "confirmacionTronco": None,
            "noTolerancias": [],
            "perfilUsuario": {
                "agudo": 1.5,
                "longitudinal": 2.0,
                "cognitivo": 2.5,
                "procedimientos": 1.0,
                "quirofano": 0.5,
                "emocional": 1.5,
                "imagen": 1.0,
                "sistema": 0.5,
                "pediatria": 1.5
            },
            "flags": {"no_guardias": False, "aversion_quirofano": False},
            "top2": [
                {"especialidadId": "medicina_interna", "nombre": "Medicina Interna", "scoreFinal": 45.2},
                {"especialidadId": "pediatria", "nombre": "Pediatría", "scoreFinal": 42.1}
            ],
            "confianza": {
                "nivel": "alta",
                "motivos": ["Tus respuestas son consistentes."],
                "accionSugerida": "Siguiente paso: valida con 1 día de shadowing."
            },
            "completado_at": "2026-02-14T20:00:00.000Z"
        }
        
        response = self.session.post(f"{BASE_URL}/api/enarm-match/results", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "id" in data
        print(f"POST RESULTS - PASS (id: {data.get('id')[:8]}...)")
        
        # Verify result was saved
        get_response = self.session.get(f"{BASE_URL}/api/enarm-match/results")
        assert get_response.status_code == 200
        results = get_response.json()
        assert len(results) > 0
        # Latest result should have our data
        latest = results[0]
        assert "perfilUsuario" in latest
        assert "top2" in latest
        print("VERIFY RESULT SAVED - PASS")
    
    def test_progress_unauthorized(self):
        """Test endpoints return 401/403 without auth"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.get(f"{BASE_URL}/api/enarm-match/progress")
        assert response.status_code in [401, 403]  # Either Unauthorized or Forbidden is acceptable
        print("UNAUTHORIZED ACCESS TEST - PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
