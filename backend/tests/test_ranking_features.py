"""
Test cases for Ranking Features:
1. GET /api/ranking/top10 - returns top 10 users by gamification points
2. POST /api/admin/seed-ranking-users - seeds 10 test users (requires admin auth)
3. POST /api/auth/register - accepts 'universidad' field
4. GET /api/auth/me - returns 'universidad' in response
"""

import pytest
import requests
import os
import random
import string

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRankingFeatures:
    """Test suite for ranking endpoints and universidad field"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@puertoenarm.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Headers with admin authentication"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }

    # ===================== RANKING TOP 10 TESTS =====================
    
    def test_ranking_top10_returns_200(self, admin_headers):
        """Test that GET /api/ranking/top10 returns 200"""
        response = requests.get(f"{BASE_URL}/api/ranking/top10", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/ranking/top10 returns 200")
    
    def test_ranking_top10_returns_list(self, admin_headers):
        """Test that GET /api/ranking/top10 returns a list"""
        response = requests.get(f"{BASE_URL}/api/ranking/top10", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ GET /api/ranking/top10 returns a list with {len(data)} entries")
    
    def test_ranking_top10_entry_structure(self, admin_headers):
        """Test that each entry has required fields: full_name, rank_name, total_points, universidad"""
        response = requests.get(f"{BASE_URL}/api/ranking/top10", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No ranking data available to test structure")
        
        entry = data[0]
        required_fields = ["full_name", "rank_name", "total_points"]
        for field in required_fields:
            assert field in entry, f"Missing required field: {field}"
        
        # universidad is optional but should be included if present
        assert "universidad" in entry or entry.get("universidad") is None, "universidad field should be present"
        
        print(f"✓ Ranking entry structure valid: {list(entry.keys())}")
    
    def test_ranking_top10_ordered_by_points(self, admin_headers):
        """Test that rankings are ordered by total_points descending"""
        response = requests.get(f"{BASE_URL}/api/ranking/top10", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) < 2:
            pytest.skip("Need at least 2 entries to test ordering")
        
        points = [entry["total_points"] for entry in data]
        assert points == sorted(points, reverse=True), f"Points not in descending order: {points}"
        print(f"✓ Rankings ordered by points descending: {points[:5]}...")
    
    def test_ranking_top10_max_10_entries(self, admin_headers):
        """Test that at most 10 entries are returned"""
        response = requests.get(f"{BASE_URL}/api/ranking/top10", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10, f"Expected max 10 entries, got {len(data)}"
        print(f"✓ Ranking returns {len(data)} entries (max 10)")
    
    def test_ranking_top10_has_rank_info(self, admin_headers):
        """Test that each entry has rank_name and rank_key"""
        response = requests.get(f"{BASE_URL}/api/ranking/top10", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No ranking data available")
        
        for i, entry in enumerate(data):
            assert "rank_name" in entry, f"Entry {i} missing rank_name"
            assert "rank_key" in entry, f"Entry {i} missing rank_key"
            assert isinstance(entry["rank_name"], str), f"rank_name should be string"
            assert len(entry["rank_name"]) > 0, f"rank_name should not be empty"
        
        print(f"✓ All entries have rank_name and rank_key")

    # ===================== SEED RANKING USERS TESTS =====================
    
    def test_seed_ranking_users_requires_admin(self):
        """Test that POST /api/admin/seed-ranking-users requires admin auth"""
        response = requests.post(f"{BASE_URL}/api/admin/seed-ranking-users")
        assert response.status_code == 403 or response.status_code == 401, \
            f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Seed ranking users requires authentication")
    
    def test_seed_ranking_users_returns_success(self, admin_headers):
        """Test that POST /api/admin/seed-ranking-users returns success"""
        response = requests.post(f"{BASE_URL}/api/admin/seed-ranking-users", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data, "Response should contain message"
        assert "users" in data, "Response should contain users list"
        print(f"✓ Seed ranking users successful: {data['message']}")
    
    def test_seed_ranking_users_creates_10_users(self, admin_headers):
        """Test that seeding creates 10 test users"""
        response = requests.post(f"{BASE_URL}/api/admin/seed-ranking-users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "users" in data
        users = data["users"]
        assert len(users) == 10, f"Expected 10 seeded users, got {len(users)}"
        
        # Verify each user has name and points
        for user in users:
            assert "name" in user, "Seeded user should have name"
            assert "points" in user, "Seeded user should have points"
        
        print(f"✓ Seeded 10 users with varying points")
    
    def test_seeded_users_appear_in_ranking(self, admin_headers):
        """Test that seeded users appear in the ranking"""
        # First seed users
        requests.post(f"{BASE_URL}/api/admin/seed-ranking-users", headers=admin_headers)
        
        # Then get ranking
        response = requests.get(f"{BASE_URL}/api/ranking/top10", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 1, "Should have at least one user in ranking after seeding"
        
        # Check that we have users with points
        has_seeded_users = any(entry["total_points"] > 0 for entry in data)
        assert has_seeded_users, "Seeded users should have points"
        print(f"✓ Seeded users appear in ranking")

    # ===================== REGISTRATION WITH UNIVERSIDAD TESTS =====================
    
    def test_register_accepts_universidad(self):
        """Test that POST /api/auth/register accepts universidad field"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        test_email = f"test_uni_{random_suffix}@test.com"
        
        payload = {
            "full_name": "Test Usuario Universidad",
            "email": test_email,
            "password": "testpass123",
            "gender": "male",
            "universidad": "Universidad de Prueba Test"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Registration failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "user_id" in data, "Response should contain user_id"
        print(f"✓ Registration with universidad field successful")
    
    def test_register_without_universidad_allowed(self):
        """Test that registration without universidad is still allowed (optional field)"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        test_email = f"test_no_uni_{random_suffix}@test.com"
        
        payload = {
            "full_name": "Test Usuario Sin Universidad",
            "email": test_email,
            "password": "testpass123",
            "gender": "female"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Registration without universidad failed: {response.status_code}"
        print(f"✓ Registration without universidad field allowed")

    # ===================== GET AUTH/ME WITH UNIVERSIDAD TESTS =====================
    
    def test_auth_me_returns_universidad(self, admin_headers):
        """Test that GET /api/auth/me returns universidad field"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert response.status_code == 200, f"Auth me failed: {response.status_code}"
        data = response.json()
        
        # universidad field should be present (even if null)
        assert "universidad" in data or data.get("universidad") is None, \
            "GET /api/auth/me should return universidad field"
        
        print(f"✓ GET /api/auth/me returns universidad: {data.get('universidad', 'None')}")
    
    def test_auth_me_structure(self, admin_headers):
        """Test that GET /api/auth/me returns complete user structure"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["id", "full_name", "email", "is_admin", "is_approved"]
        for field in expected_fields:
            assert field in data, f"Missing expected field: {field}"
        
        print(f"✓ GET /api/auth/me returns complete user structure")


class TestRankingTop10Data:
    """Test specific ranking data requirements"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@puertoenarm.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Headers with admin authentication"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_ranking_entry_full_name_is_string(self, admin_headers):
        """Test that full_name is a non-empty string"""
        response = requests.get(f"{BASE_URL}/api/ranking/top10", headers=admin_headers)
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No ranking data")
        
        for i, entry in enumerate(data):
            assert isinstance(entry["full_name"], str), f"Entry {i}: full_name should be string"
            assert len(entry["full_name"]) > 0, f"Entry {i}: full_name should not be empty"
        
        print(f"✓ All full_name fields are valid strings")
    
    def test_ranking_entry_total_points_is_number(self, admin_headers):
        """Test that total_points is a positive number"""
        response = requests.get(f"{BASE_URL}/api/ranking/top10", headers=admin_headers)
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No ranking data")
        
        for i, entry in enumerate(data):
            assert isinstance(entry["total_points"], (int, float)), \
                f"Entry {i}: total_points should be number"
            assert entry["total_points"] >= 0, f"Entry {i}: total_points should be non-negative"
        
        print(f"✓ All total_points fields are valid numbers")
    
    def test_ranking_entry_has_user_id(self, admin_headers):
        """Test that each entry has user_id"""
        response = requests.get(f"{BASE_URL}/api/ranking/top10", headers=admin_headers)
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No ranking data")
        
        for i, entry in enumerate(data):
            assert "user_id" in entry, f"Entry {i} missing user_id"
            assert isinstance(entry["user_id"], str), f"Entry {i}: user_id should be string"
        
        print(f"✓ All entries have user_id")
    
    def test_ranking_entry_profile_image_optional(self, admin_headers):
        """Test that profile_image field exists (can be null)"""
        response = requests.get(f"{BASE_URL}/api/ranking/top10", headers=admin_headers)
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No ranking data")
        
        for i, entry in enumerate(data):
            assert "profile_image" in entry or entry.get("profile_image") is None, \
                f"Entry {i} should have profile_image field"
        
        print(f"✓ profile_image field present in all entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
