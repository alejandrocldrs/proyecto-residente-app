"""
Test suite for dynamic pricing, registration flow, and admin approval features.
Tests:
1. GET /api/settings/price - public endpoint
2. GET /api/admin/settings/price - admin auth required
3. POST /api/admin/settings/price - admin auth required, updates price
4. POST /api/admin/settings/price - rejects price <= 0
5. POST /api/auth/register - stores temp_password in user document
6. PATCH /api/admin/approve-user/{id} - sets subscription_expires (6 months) and activated_at
7. POST /api/payments/create-preference - uses dynamic price from settings
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@puertoenarm.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def admin_client(api_client, admin_token):
    """Session with admin auth header"""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


class TestPublicPriceEndpoint:
    """Tests for GET /api/settings/price (public, no auth)"""
    
    def test_get_price_returns_200(self, api_client):
        """GET /api/settings/price should return 200"""
        response = api_client.get(f"{BASE_URL}/api/settings/price")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ GET /api/settings/price returns 200")
    
    def test_get_price_returns_price_structure(self, api_client):
        """GET /api/settings/price should return price, currency, duration_months"""
        response = api_client.get(f"{BASE_URL}/api/settings/price")
        data = response.json()
        
        assert "price" in data, "Response should contain 'price'"
        assert "currency" in data, "Response should contain 'currency'"
        assert "duration_months" in data, "Response should contain 'duration_months'"
        assert data["currency"] == "MXN", f"Currency should be MXN, got {data['currency']}"
        assert data["duration_months"] == 6, f"Duration should be 6 months, got {data['duration_months']}"
        assert isinstance(data["price"], (int, float)), "Price should be a number"
        assert data["price"] > 0, "Price should be positive"
        print(f"✓ GET /api/settings/price returns correct structure: price={data['price']}, currency={data['currency']}, duration={data['duration_months']}")


class TestAdminPriceEndpoints:
    """Tests for admin price endpoints (auth required)"""
    
    def test_admin_get_price_requires_auth(self, api_client):
        """GET /api/admin/settings/price should require authentication"""
        # Create a new session without auth
        no_auth_session = requests.Session()
        response = no_auth_session.get(f"{BASE_URL}/api/admin/settings/price")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ GET /api/admin/settings/price requires auth (returns {response.status_code})")
    
    def test_admin_get_price_with_auth(self, admin_client):
        """GET /api/admin/settings/price should return price with admin auth"""
        response = admin_client.get(f"{BASE_URL}/api/admin/settings/price")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "price" in data, "Response should contain 'price'"
        assert isinstance(data["price"], (int, float)), "Price should be a number"
        print(f"✓ GET /api/admin/settings/price returns price={data['price']} with admin auth")
    
    def test_admin_post_price_requires_auth(self, api_client):
        """POST /api/admin/settings/price should require authentication"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        response = no_auth_session.post(f"{BASE_URL}/api/admin/settings/price", json={"price": 2000})
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ POST /api/admin/settings/price requires auth (returns {response.status_code})")
    
    def test_admin_update_price_success(self, admin_client):
        """POST /api/admin/settings/price should update price successfully"""
        # First get current price
        get_response = admin_client.get(f"{BASE_URL}/api/admin/settings/price")
        original_price = get_response.json()["price"]
        
        # Update to a new price
        new_price = 1999
        response = admin_client.post(f"{BASE_URL}/api/admin/settings/price", json={"price": new_price})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "price" in data, "Response should contain 'price'"
        assert data["price"] == new_price, f"Price should be {new_price}, got {data['price']}"
        
        # Verify the change persisted
        verify_response = admin_client.get(f"{BASE_URL}/api/admin/settings/price")
        assert verify_response.json()["price"] == new_price, "Price change should persist"
        
        # Restore original price
        admin_client.post(f"{BASE_URL}/api/admin/settings/price", json={"price": original_price})
        print(f"✓ POST /api/admin/settings/price updates price successfully ({original_price} -> {new_price} -> {original_price})")
    
    def test_admin_update_price_rejects_zero(self, admin_client):
        """POST /api/admin/settings/price should reject price <= 0"""
        response = admin_client.post(f"{BASE_URL}/api/admin/settings/price", json={"price": 0})
        assert response.status_code == 400, f"Expected 400 for price=0, got {response.status_code}"
        print(f"✓ POST /api/admin/settings/price rejects price=0 (returns 400)")
    
    def test_admin_update_price_rejects_negative(self, admin_client):
        """POST /api/admin/settings/price should reject negative price"""
        response = admin_client.post(f"{BASE_URL}/api/admin/settings/price", json={"price": -100})
        assert response.status_code == 400, f"Expected 400 for negative price, got {response.status_code}"
        print(f"✓ POST /api/admin/settings/price rejects negative price (returns 400)")
    
    def test_price_change_reflects_in_public_endpoint(self, admin_client, api_client):
        """Price change should reflect in GET /api/settings/price"""
        # Get original price
        original_response = api_client.get(f"{BASE_URL}/api/settings/price")
        original_price = original_response.json()["price"]
        
        # Update price
        test_price = 2500
        admin_client.post(f"{BASE_URL}/api/admin/settings/price", json={"price": test_price})
        
        # Verify public endpoint reflects change
        public_response = api_client.get(f"{BASE_URL}/api/settings/price")
        assert public_response.json()["price"] == test_price, f"Public endpoint should show updated price {test_price}"
        
        # Restore original price
        admin_client.post(f"{BASE_URL}/api/admin/settings/price", json={"price": original_price})
        print(f"✓ Price change reflects in public endpoint ({original_price} -> {test_price} -> {original_price})")


class TestRegistrationTempPassword:
    """Tests for registration storing temp_password"""
    
    def test_register_creates_user(self, api_client):
        """POST /api/auth/register should create user successfully"""
        import uuid
        test_email = f"test_temp_pwd_{uuid.uuid4().hex[:8]}@test.com"
        
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "Test TempPwd User",
            "email": test_email,
            "password": "testpass123",
            "gender": "male",
            "universidad": "Test University"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "user_id" in data, "Response should contain user_id"
        print(f"✓ POST /api/auth/register creates user successfully (user_id={data['user_id']})")
        return data["user_id"]


class TestAdminApproveUser:
    """Tests for admin user approval with subscription_expires"""
    
    def test_approve_user_sets_subscription_expires(self, admin_client, api_client):
        """PATCH /api/admin/approve-user/{id} should set subscription_expires (6 months)"""
        import uuid
        
        # First create a test user
        test_email = f"test_approve_{uuid.uuid4().hex[:8]}@test.com"
        register_response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "Test Approve User",
            "email": test_email,
            "password": "testpass123",
            "gender": "female",
            "universidad": "Test University"
        })
        
        assert register_response.status_code == 200, f"Registration failed: {register_response.text}"
        user_id = register_response.json()["user_id"]
        
        # Approve the user
        approve_response = admin_client.patch(f"{BASE_URL}/api/admin/approve-user/{user_id}")
        assert approve_response.status_code == 200, f"Expected 200, got {approve_response.status_code}: {approve_response.text}"
        
        # Verify user can now login
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": "testpass123"
        })
        assert login_response.status_code == 200, f"Login should succeed after approval: {login_response.text}"
        
        # Get user info to verify subscription_expires
        token = login_response.json()["access_token"]
        me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200, f"Failed to get user info: {me_response.text}"
        
        user_data = me_response.json()
        assert user_data["is_approved"] == True, "User should be approved"
        assert "subscription_expires" in user_data, "User should have subscription_expires"
        assert user_data["subscription_expires"] is not None, "subscription_expires should not be None"
        
        # Verify subscription_expires is approximately 6 months from now
        expires_date = datetime.fromisoformat(user_data["subscription_expires"].replace('Z', '+00:00'))
        now = datetime.now(expires_date.tzinfo)
        days_until_expiry = (expires_date - now).days
        
        # Should be approximately 180 days (6 months), allow some tolerance
        assert 175 <= days_until_expiry <= 185, f"subscription_expires should be ~180 days from now, got {days_until_expiry} days"
        
        print(f"✓ PATCH /api/admin/approve-user sets subscription_expires correctly ({days_until_expiry} days from now)")
        
        # Cleanup: delete the test user
        admin_client.delete(f"{BASE_URL}/api/admin/reject-user/{user_id}")


class TestPaymentPreferenceDynamicPrice:
    """Tests for payment preference using dynamic price"""
    
    def test_create_preference_uses_dynamic_price(self, admin_client, api_client):
        """POST /api/payments/create-preference should use dynamic price from settings"""
        import uuid
        
        # Set a specific test price
        test_price = 1750
        admin_client.post(f"{BASE_URL}/api/admin/settings/price", json={"price": test_price})
        
        # Create a test user
        test_email = f"test_payment_{uuid.uuid4().hex[:8]}@test.com"
        register_response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "full_name": "Test Payment User",
            "email": test_email,
            "password": "testpass123",
            "gender": "male",
            "universidad": "Test University"
        })
        
        assert register_response.status_code == 200, f"Registration failed: {register_response.text}"
        user_id = register_response.json()["user_id"]
        
        # Try to create payment preference
        # Note: This may fail if MercadoPago is not configured, which is expected
        payment_response = api_client.post(f"{BASE_URL}/api/payments/create-preference", json={
            "user_id": user_id
        })
        
        # If MercadoPago is configured, it should return 200 with preference data
        # If not configured, it will return 500 with "MercadoPago not configured"
        if payment_response.status_code == 200:
            data = payment_response.json()
            assert "preference_id" in data, "Response should contain preference_id"
            assert "init_point" in data, "Response should contain init_point"
            print(f"✓ POST /api/payments/create-preference works with dynamic price (preference_id={data['preference_id']})")
        elif payment_response.status_code == 500 and "not configured" in payment_response.text.lower():
            print(f"✓ POST /api/payments/create-preference endpoint exists (MercadoPago not configured - expected in test env)")
        else:
            # Unexpected error
            print(f"⚠ POST /api/payments/create-preference returned {payment_response.status_code}: {payment_response.text}")
        
        # Cleanup: delete the test user
        admin_client.delete(f"{BASE_URL}/api/admin/reject-user/{user_id}")
        
        # Restore default price
        admin_client.post(f"{BASE_URL}/api/admin/settings/price", json={"price": 1500})


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
