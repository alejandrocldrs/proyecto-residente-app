"""
Tests for Landing Page, Payment, and Registration Features
- Landing page endpoints behavior
- MercadoPago payment integration (expected failures when not configured)
- Registration flow with new fields
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthCheck:
    """Basic API health verification"""
    
    def test_api_root_accessible(self):
        """Verify API is running"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        print("✓ API health check passed")


class TestMercadoPagoPayments:
    """Tests for MercadoPago payment endpoints - expected to fail without MP keys"""
    
    def test_create_preference_returns_500_when_mp_not_configured(self):
        """
        POST /api/payments/create-preference should return 500 when MP_ACCESS_TOKEN is not set.
        This is expected behavior documented in the review request.
        """
        # First need a valid user_id - create a test user
        test_email = f"test_mp_{uuid.uuid4().hex[:8]}@test.com"
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "Test MP User",
            "email": test_email,
            "password": "testpass123",
            "gender": "male",
            "universidad": "Test University"
        })
        assert register_response.status_code == 200
        user_id = register_response.json().get("user_id")
        assert user_id is not None
        print(f"✓ Test user created with ID: {user_id}")
        
        # Now try to create payment preference - should fail with 500
        response = requests.post(f"{BASE_URL}/api/payments/create-preference", json={
            "user_id": user_id
        })
        # Expected: 500 because MercadoPago is not configured
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        data = response.json()
        assert "MercadoPago not configured" in data.get("detail", "")
        print("✓ create-preference correctly returns 500 when MP not configured")
    
    def test_payment_status_returns_404_for_nonexistent_user(self):
        """GET /api/payments/status/{user_id} returns 404 for nonexistent user"""
        fake_user_id = "nonexistent-user-12345"
        response = requests.get(f"{BASE_URL}/api/payments/status/{fake_user_id}")
        assert response.status_code == 404
        data = response.json()
        assert "Usuario no encontrado" in data.get("detail", "")
        print("✓ payment status correctly returns 404 for nonexistent user")
    
    def test_payment_status_returns_none_for_new_user(self):
        """GET /api/payments/status/{user_id} returns 'none' status for new user without payment"""
        # Create a test user first
        test_email = f"test_status_{uuid.uuid4().hex[:8]}@test.com"
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "Test Status User",
            "email": test_email,
            "password": "testpass123",
            "gender": "female",
            "universidad": "Status Test University"
        })
        assert register_response.status_code == 200
        user_id = register_response.json().get("user_id")
        
        # Check payment status
        response = requests.get(f"{BASE_URL}/api/payments/status/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "none"
        assert "No se ha realizado ningún pago" in data.get("message", "")
        print("✓ payment status correctly returns 'none' for new user")
    
    def test_verify_and_approve_returns_404_for_nonexistent_user(self):
        """POST /api/payments/verify-and-approve/{user_id} returns 404 for nonexistent user"""
        fake_user_id = "nonexistent-user-verify-12345"
        response = requests.post(f"{BASE_URL}/api/payments/verify-and-approve/{fake_user_id}")
        assert response.status_code == 404
        data = response.json()
        assert "Usuario no encontrado" in data.get("detail", "")
        print("✓ verify-and-approve correctly returns 404 for nonexistent user")


class TestRegistrationFlow:
    """Tests for registration with new fields (gender, universidad)"""
    
    def test_register_with_gender_and_university(self):
        """Registration should accept gender and universidad fields"""
        test_email = f"test_reg_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "Dr. Test User",
            "email": test_email,
            "password": "testpass123",
            "gender": "male",
            "universidad": "Universidad Nacional Autónoma de México"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("user_id") is not None
        assert "registered successfully" in data.get("message", "").lower() or "Waiting for admin approval" in data.get("message", "")
        print("✓ Registration with gender and universidad succeeds")
    
    def test_register_with_female_gender(self):
        """Registration should accept female gender"""
        test_email = f"test_female_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "Dra. Test User",
            "email": test_email,
            "password": "testpass123",
            "gender": "female",
            "universidad": "Universidad de Guadalajara"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("user_id") is not None
        print("✓ Registration with female gender succeeds")
    
    def test_register_without_optional_fields(self):
        """Registration should work without gender and universidad (optional)"""
        test_email = f"test_minimal_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "Minimal User",
            "email": test_email,
            "password": "testpass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("user_id") is not None
        print("✓ Registration without optional fields succeeds")
    
    def test_register_duplicate_email_fails(self):
        """Registration with duplicate email should fail"""
        test_email = f"test_dup_{uuid.uuid4().hex[:8]}@test.com"
        
        # First registration
        response1 = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "First User",
            "email": test_email,
            "password": "testpass123"
        })
        assert response1.status_code == 200
        
        # Duplicate registration
        response2 = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "Second User",
            "email": test_email,
            "password": "testpass456"
        })
        assert response2.status_code == 400
        assert "already registered" in response2.json().get("detail", "").lower()
        print("✓ Duplicate email registration correctly fails")


class TestAdminLogin:
    """Tests for admin authentication"""
    
    def test_admin_login_works(self):
        """Admin login with correct credentials should succeed"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@puertoenarm.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        print("✓ Admin login succeeds with correct credentials")
        return data["access_token"]
    
    def test_admin_login_wrong_password_fails(self):
        """Admin login with wrong password should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@puertoenarm.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 400
        print("✓ Admin login fails with wrong password")
    
    def test_get_me_returns_admin_info(self):
        """GET /api/auth/me should return admin info with valid token"""
        # First login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@puertoenarm.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Get user info
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@puertoenarm.com"
        assert data["is_admin"] == True
        assert data["is_approved"] == True
        print("✓ GET /api/auth/me returns correct admin info")


class TestUnapprovedUserLogin:
    """Tests for login behavior with unapproved users"""
    
    def test_unapproved_user_cannot_login(self):
        """Unapproved user should not be able to login"""
        # Create a new user (will be unapproved by default)
        test_email = f"test_unapproved_{uuid.uuid4().hex[:8]}@test.com"
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "Unapproved User",
            "email": test_email,
            "password": "testpass123",
            "gender": "male",
            "universidad": "Test University"
        })
        assert register_response.status_code == 200
        
        # Try to login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": "testpass123"
        })
        assert login_response.status_code == 400
        assert "not approved" in login_response.json().get("detail", "").lower()
        print("✓ Unapproved user correctly cannot login")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
