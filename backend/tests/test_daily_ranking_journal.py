"""
Tests for Daily Ranking System and Journal separation features.
- GET /api/ranking/daily-top10: Returns top 10 users by daily score since last 9 PM CDMX
- GET /api/journal/today: Returns current article WITH authors array
- GET /api/journal/history: Returns last 30 published journals
- POST /api/admin/journal/rotate: Rotates article and snapshots authors
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@puertoenarm.com"
ADMIN_PASSWORD = "admin123"


def get_admin_token():
    """Get admin authentication token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    return None


class TestDailyRanking:
    """Tests for GET /api/ranking/daily-top10 endpoint."""

    def test_daily_ranking_returns_200(self):
        """Test that daily ranking endpoint returns 200 for authenticated user."""
        token = get_admin_token()
        assert token, "Failed to get admin token"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/ranking/daily-top10", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Daily ranking endpoint returns 200")

    def test_daily_ranking_returns_list(self):
        """Test that daily ranking returns a list."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/ranking/daily-top10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ Daily ranking returns list with {len(data)} entries")

    def test_daily_ranking_entry_structure(self):
        """Test that each ranking entry has correct structure (if entries exist)."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/ranking/daily-top10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            entry = data[0]
            expected_fields = ["user_id", "full_name", "universidad", "score", 
                            "quiz_count", "duel_win_count", "escape_room_count", 
                            "simulacro_count", "imagendx_count"]
            for field in expected_fields:
                assert field in entry, f"Missing field: {field}"
            print(f"✓ Ranking entry has all expected fields: {list(entry.keys())}")
        else:
            print(f"✓ Daily ranking is empty (expected - no activities since 9 PM CDMX)")

    def test_daily_ranking_max_10_entries(self):
        """Test that ranking returns at most 10 entries."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/ranking/daily-top10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10, f"Expected max 10 entries, got {len(data)}"
        print(f"✓ Daily ranking has {len(data)} entries (max 10)")

    def test_daily_ranking_requires_auth(self):
        """Test that daily ranking requires authentication."""
        response = requests.get(f"{BASE_URL}/api/ranking/daily-top10")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Daily ranking requires authentication (status: {response.status_code})")


class TestJournalToday:
    """Tests for GET /api/journal/today endpoint."""

    def test_journal_today_returns_200(self):
        """Test that journal today endpoint returns 200."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/journal/today", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Journal today endpoint returns 200")

    def test_journal_today_has_article_fields(self):
        """Test that journal today has required article fields."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/journal/today", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if data is None:
            print(f"✓ No current journal (expected if no articles uploaded)")
            return
        
        expected_fields = ["tema", "antecedentes", "metodos", "resultados", "conclusiones"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        print(f"✓ Journal today has all article fields. Tema: {data['tema'][:50]}...")

    def test_journal_today_has_authors_array(self):
        """Test that journal today has authors array."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/journal/today", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if data is None:
            print(f"✓ No current journal - cannot check authors")
            return
        
        assert "authors" in data, "Missing 'authors' field in journal"
        assert isinstance(data["authors"], list), f"Authors should be list, got {type(data['authors'])}"
        print(f"✓ Journal has authors array with {len(data['authors'])} authors")

    def test_journal_today_has_issue_number_and_date(self):
        """Test that journal today has issue_number and date_str."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/journal/today", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if data is None:
            print(f"✓ No current journal - cannot check issue_number/date_str")
            return
        
        assert "issue_number" in data, "Missing 'issue_number' field"
        assert isinstance(data["issue_number"], int), f"issue_number should be int"
        assert "date_str" in data, "Missing 'date_str' field"
        print(f"✓ Journal has issue_number: {data['issue_number']}, date: {data['date_str']}")

    def test_journal_today_requires_auth(self):
        """Test that journal today requires authentication."""
        response = requests.get(f"{BASE_URL}/api/journal/today")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Journal today requires authentication (status: {response.status_code})")


class TestJournalHistory:
    """Tests for GET /api/journal/history endpoint."""

    def test_journal_history_returns_200(self):
        """Test that journal history endpoint returns 200."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/journal/history", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Journal history endpoint returns 200")

    def test_journal_history_returns_list(self):
        """Test that journal history returns a list."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/journal/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ Journal history returns list with {len(data)} entries")

    def test_journal_history_max_30_entries(self):
        """Test that journal history returns at most 30 entries."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/journal/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 30, f"Expected max 30 entries, got {len(data)}"
        print(f"✓ Journal history has {len(data)} entries (max 30)")

    def test_journal_history_entry_structure(self):
        """Test that each history entry has correct structure."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/journal/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            entry = data[0]
            expected_fields = ["tema", "issue_number"]
            for field in expected_fields:
                assert field in entry, f"Missing field: {field}"
            print(f"✓ History entry has expected fields. Issue: {entry.get('issue_number')}")
        else:
            print(f"✓ Journal history is empty (expected if no rotations)")

    def test_journal_history_requires_auth(self):
        """Test that journal history requires authentication."""
        response = requests.get(f"{BASE_URL}/api/journal/history")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Journal history requires authentication (status: {response.status_code})")


class TestAdminJournalRotate:
    """Tests for POST /api/admin/journal/rotate endpoint."""

    def test_journal_rotate_returns_200_for_admin(self):
        """Test that journal rotate returns 200 for admin."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/api/admin/journal/rotate", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Journal rotate returns 200 for admin")

    def test_journal_rotate_requires_auth(self):
        """Test that journal rotate requires authentication."""
        response = requests.post(f"{BASE_URL}/api/admin/journal/rotate")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Journal rotate requires authentication (status: {response.status_code})")


class TestAdminJournalStatus:
    """Tests for GET /api/admin/journal/status endpoint."""

    def test_journal_status_returns_200_for_admin(self):
        """Test that journal status returns 200 for admin."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/admin/journal/status", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Journal status returns 200 for admin")

    def test_journal_status_has_required_fields(self):
        """Test that journal status has required fields."""
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/admin/journal/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["total_articles", "used_articles", "remaining_articles", "current_article"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Journal status has: {data['total_articles']} total, {data['used_articles']} used, {data['remaining_articles']} remaining")

    def test_journal_status_requires_auth(self):
        """Test that journal status requires authentication."""
        response = requests.get(f"{BASE_URL}/api/admin/journal/status")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Journal status requires authentication (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
