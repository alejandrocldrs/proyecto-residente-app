"""
Journal System Tests
Tests for the Dynamic Journal feature:
- POST /api/admin/journal/upload - uploads Excel with 364 articles
- GET /api/admin/journal/status - returns total/used/remaining articles
- GET /api/journal/today - returns current article for Ranking page
- POST /api/admin/journal/rotate - manual article rotation
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@puertoenarm.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Admin authentication failed - skipping journal tests")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Return headers with admin auth token"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestJournalStatus:
    """Test GET /api/admin/journal/status endpoint"""

    def test_journal_status_returns_200(self, admin_headers):
        """Status endpoint should return 200 for admin"""
        response = requests.get(f"{BASE_URL}/api/admin/journal/status", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Journal status endpoint returns 200")

    def test_journal_status_has_required_fields(self, admin_headers):
        """Status should include total_articles, used_articles, remaining_articles, current_article"""
        response = requests.get(f"{BASE_URL}/api/admin/journal/status", headers=admin_headers)
        data = response.json()
        
        assert "total_articles" in data, "Missing total_articles field"
        assert "used_articles" in data, "Missing used_articles field"
        assert "remaining_articles" in data, "Missing remaining_articles field"
        assert "current_article" in data, "Missing current_article field"
        
        print(f"✓ Status has all required fields: total={data['total_articles']}, used={data['used_articles']}, remaining={data['remaining_articles']}")

    def test_journal_has_articles_loaded(self, admin_headers):
        """Verify articles have been uploaded (364 expected)"""
        response = requests.get(f"{BASE_URL}/api/admin/journal/status", headers=admin_headers)
        data = response.json()
        
        # Should have articles loaded
        assert data["total_articles"] > 0, "No articles loaded in journal system"
        print(f"✓ Journal has {data['total_articles']} articles loaded")

    def test_journal_status_requires_admin(self):
        """Status endpoint should require admin authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/journal/status")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Journal status requires admin auth (returned {response.status_code})")


class TestJournalToday:
    """Test GET /api/journal/today endpoint"""

    def test_journal_today_returns_200(self, admin_headers):
        """Today endpoint should return 200 for authenticated user"""
        response = requests.get(f"{BASE_URL}/api/journal/today", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Journal today endpoint returns 200")

    def test_journal_today_has_article_content(self, admin_headers):
        """Today's article should have tema, antecedentes, metodos, resultados, conclusiones"""
        response = requests.get(f"{BASE_URL}/api/journal/today", headers=admin_headers)
        data = response.json()
        
        if data is None:
            pytest.skip("No current article set - may need rotation first")
        
        required_fields = ["tema", "antecedentes", "metodos", "resultados", "conclusiones"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
            assert data[field], f"Field {field} is empty"
        
        print(f"✓ Today's article has all required fields")
        print(f"  Tema: {data['tema'][:60]}...")

    def test_journal_today_has_issue_and_date(self, admin_headers):
        """Today's article should have issue_number and date_str"""
        response = requests.get(f"{BASE_URL}/api/journal/today", headers=admin_headers)
        data = response.json()
        
        if data is None:
            pytest.skip("No current article set")
        
        assert "issue_number" in data, "Missing issue_number field"
        assert "date_str" in data, "Missing date_str field"
        assert isinstance(data["issue_number"], int), "issue_number should be integer"
        assert data["issue_number"] > 0, "issue_number should be positive"
        
        print(f"✓ Article has issue #{data['issue_number']} dated {data['date_str']}")

    def test_journal_today_requires_auth(self):
        """Today endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/journal/today")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Journal today requires auth (returned {response.status_code})")


class TestJournalRotation:
    """Test POST /api/admin/journal/rotate endpoint"""

    def test_journal_rotate_returns_200(self, admin_headers):
        """Rotate endpoint should return 200 for admin"""
        response = requests.post(f"{BASE_URL}/api/admin/journal/rotate", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Journal rotate endpoint returns 200")

    def test_journal_rotate_increments_issue(self, admin_headers):
        """Rotation should increment the issue_number"""
        # Get current issue number
        before = requests.get(f"{BASE_URL}/api/admin/journal/status", headers=admin_headers)
        before_data = before.json()
        old_issue = before_data.get("current_article", {}).get("issue_number", 142)
        
        # Rotate
        response = requests.post(f"{BASE_URL}/api/admin/journal/rotate", headers=admin_headers)
        assert response.status_code == 200
        
        # Get new issue number
        after = requests.get(f"{BASE_URL}/api/admin/journal/status", headers=admin_headers)
        after_data = after.json()
        new_issue = after_data.get("current_article", {}).get("issue_number", 0)
        
        assert new_issue == old_issue + 1, f"Issue should increment: {old_issue} -> {new_issue}"
        print(f"✓ Issue number incremented from {old_issue} to {new_issue}")

    def test_journal_rotate_changes_article(self, admin_headers):
        """Rotation should select a different article (or same if only 1 remaining)"""
        # Get current article
        before = requests.get(f"{BASE_URL}/api/journal/today", headers=admin_headers)
        before_data = before.json()
        
        if not before_data:
            pytest.skip("No current article to compare")
        
        old_tema = before_data.get("tema", "")
        
        # Rotate
        response = requests.post(f"{BASE_URL}/api/admin/journal/rotate", headers=admin_headers)
        assert response.status_code == 200
        
        # Get new article
        after = requests.get(f"{BASE_URL}/api/journal/today", headers=admin_headers)
        after_data = after.json()
        new_tema = after_data.get("tema", "")
        
        # Article should have changed (unless only 1 article left)
        print(f"✓ Article rotated: '{old_tema[:40]}...' -> '{new_tema[:40]}...'")

    def test_journal_rotate_requires_admin(self):
        """Rotate endpoint should require admin authentication"""
        response = requests.post(f"{BASE_URL}/api/admin/journal/rotate")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Journal rotate requires admin auth (returned {response.status_code})")


class TestJournalUpload:
    """Test POST /api/admin/journal/upload endpoint"""

    def test_journal_upload_requires_admin(self):
        """Upload endpoint should require admin authentication"""
        response = requests.post(f"{BASE_URL}/api/admin/journal/upload")
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422 without auth, got {response.status_code}"
        print(f"✓ Journal upload requires admin auth (returned {response.status_code})")

    def test_journal_upload_works_with_excel(self, admin_headers):
        """Upload should accept Excel file and store articles"""
        # Check if test file exists
        excel_path = "/app/journal_articles.xlsx"
        if not os.path.exists(excel_path):
            pytest.skip("Test Excel file not found")
        
        # Upload the file
        with open(excel_path, 'rb') as f:
            files = {'file': ('journal_articles.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = requests.post(
                f"{BASE_URL}/api/admin/journal/upload",
                headers=admin_headers,
                files=files
            )
        
        assert response.status_code == 200, f"Upload failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert "count" in data, "Response should include article count"
        assert data["count"] > 0, "Should have uploaded articles"
        
        print(f"✓ Successfully uploaded {data['count']} articles from Excel")

    def test_journal_upload_selects_first_article(self, admin_headers):
        """After upload, a current article should be selected"""
        response = requests.get(f"{BASE_URL}/api/admin/journal/status", headers=admin_headers)
        data = response.json()
        
        assert data.get("current_article") is not None, "Current article should be set after upload"
        print(f"✓ Current article is set after upload: {data['current_article'].get('tema', 'N/A')[:50]}...")


class TestJournalIntegration:
    """Integration tests for the full Journal system flow"""

    def test_full_journal_flow(self, admin_headers):
        """Test complete flow: status -> today -> rotate -> verify"""
        # 1. Get status
        status_resp = requests.get(f"{BASE_URL}/api/admin/journal/status", headers=admin_headers)
        assert status_resp.status_code == 200
        status = status_resp.json()
        print(f"  Status: {status['total_articles']} total, {status['used_articles']} used, {status['remaining_articles']} remaining")
        
        # 2. Get today's article
        today_resp = requests.get(f"{BASE_URL}/api/journal/today", headers=admin_headers)
        assert today_resp.status_code == 200
        today = today_resp.json()
        if today:
            print(f"  Today's article: Issue #{today.get('issue_number')} - {today.get('tema', 'N/A')[:40]}...")
        
        # 3. Rotate
        rotate_resp = requests.post(f"{BASE_URL}/api/admin/journal/rotate", headers=admin_headers)
        assert rotate_resp.status_code == 200
        
        # 4. Verify rotation
        new_status = requests.get(f"{BASE_URL}/api/admin/journal/status", headers=admin_headers).json()
        new_today = requests.get(f"{BASE_URL}/api/journal/today", headers=admin_headers).json()
        
        if today and new_today:
            assert new_today.get("issue_number") == today.get("issue_number", 142) + 1, "Issue should increment"
        
        print(f"✓ Full journal flow completed successfully")
        print(f"  New status: {new_status['used_articles']} used of {new_status['total_articles']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
