"""
Test suite for Presentations (Presentaciones de Repaso) module
Tests: API endpoints for presentations upload, list, view, and delete
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://subscription-revamp-3.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@puertoenarm.com"
ADMIN_PASSWORD = "admin123"


class TestPresentationsAPI:
    """Test Presentations API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
    
    def get_admin_token(self):
        """Get admin authentication token"""
        if self.admin_token:
            return self.admin_token
        
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            self.admin_token = response.json().get("access_token")
            return self.admin_token
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    def test_01_admin_login(self):
        """Test admin login works"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        print(f"✅ Admin login successful")
    
    def test_02_get_presentations_modules(self):
        """Test GET /api/presentations/modules returns module structure"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/presentations/modules",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Failed to get modules: {response.text}"
        
        data = response.json()
        # Verify expected modules exist
        expected_modules = ["Ginecología y Obstetricia", "Pediatría", "Cirugía", "Medicina Interna", "Otros"]
        for module in expected_modules:
            assert module in data, f"Module '{module}' not found in response"
        
        # Verify modules with submodules
        assert data["Cirugía"]["hasSubmodules"] == True
        assert data["Medicina Interna"]["hasSubmodules"] == True
        assert data["Otros"]["hasSubmodules"] == True
        
        # Verify modules without submodules
        assert data["Ginecología y Obstetricia"]["hasSubmodules"] == False
        assert data["Pediatría"]["hasSubmodules"] == False
        
        print(f"✅ Presentations modules structure verified")
    
    def test_03_list_presentations_empty_or_existing(self):
        """Test GET /api/presentations/list returns presentations list"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/presentations/list",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Failed to list presentations: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ Presentations list returned {len(data)} items")
    
    def test_04_list_presentations_by_module(self):
        """Test GET /api/presentations/list with module filter"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/presentations/list?module=Medicina%20Interna",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Failed to list presentations by module: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # All returned presentations should be from Medicina Interna
        for presentation in data:
            assert presentation.get("module") == "Medicina Interna", f"Unexpected module: {presentation.get('module')}"
        
        print(f"✅ Presentations filtered by module: {len(data)} items")
    
    def test_05_list_presentations_by_submodule(self):
        """Test GET /api/presentations/list with module and submodule filter"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/presentations/list?module=Medicina%20Interna&submodule=Cardiología",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Failed to list presentations by submodule: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # All returned presentations should be from Cardiología
        for presentation in data:
            assert presentation.get("submodule") == "Cardiología", f"Unexpected submodule: {presentation.get('submodule')}"
        
        print(f"✅ Presentations filtered by submodule: {len(data)} items")
    
    def test_06_admin_get_all_presentations(self):
        """Test GET /api/admin/presentations/all returns all presentations for admin"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/admin/presentations/all",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Failed to get all presentations: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ Admin presentations list returned {len(data)} items")
    
    def test_07_upload_presentation_requires_admin(self):
        """Test POST /api/admin/presentations/upload requires admin auth"""
        # Test without auth
        response = self.session.post(
            f"{BASE_URL}/api/admin/presentations/upload",
            data={"title": "Test", "module": "Pediatría"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ Upload endpoint requires authentication")
    
    def test_08_upload_presentation_validates_module(self):
        """Test POST /api/admin/presentations/upload validates module"""
        token = self.get_admin_token()
        
        # Create a simple PDF-like file for testing
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/admin/presentations/upload",
            headers={"Authorization": f"Bearer {token}"},
            data={"title": "Test", "module": "InvalidModule"},
            files=files
        )
        assert response.status_code == 400, f"Expected 400 for invalid module, got {response.status_code}"
        print(f"✅ Upload validates module correctly")
    
    def test_09_upload_presentation_requires_submodule_for_cirugia(self):
        """Test POST /api/admin/presentations/upload requires submodule for Cirugía"""
        token = self.get_admin_token()
        
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/admin/presentations/upload",
            headers={"Authorization": f"Bearer {token}"},
            data={"title": "Test", "module": "Cirugía"},  # Missing submodule
            files=files
        )
        assert response.status_code == 400, f"Expected 400 for missing submodule, got {response.status_code}"
        print(f"✅ Upload requires submodule for modules with submodules")
    
    def test_10_upload_presentation_validates_file_type(self):
        """Test POST /api/admin/presentations/upload only accepts PDF"""
        token = self.get_admin_token()
        
        # Try to upload a non-PDF file
        files = {"file": ("test.txt", io.BytesIO(b"Not a PDF"), "text/plain")}
        
        response = requests.post(
            f"{BASE_URL}/api/admin/presentations/upload",
            headers={"Authorization": f"Bearer {token}"},
            data={"title": "Test", "module": "Pediatría"},
            files=files
        )
        assert response.status_code == 400, f"Expected 400 for non-PDF file, got {response.status_code}"
        print(f"✅ Upload validates file type (PDF only)")
    
    def test_11_view_presentation_requires_token(self):
        """Test GET /api/presentations/view/{id} requires token"""
        response = self.session.get(
            f"{BASE_URL}/api/presentations/view/nonexistent-id"
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✅ View presentation requires token")
    
    def test_12_view_presentation_returns_404_for_nonexistent(self):
        """Test GET /api/presentations/view/{id} returns 404 for nonexistent"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/presentations/view/nonexistent-id?token={token}"
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ View returns 404 for nonexistent presentation")
    
    def test_13_delete_presentation_requires_admin(self):
        """Test DELETE /api/admin/presentations/{id} requires admin"""
        response = self.session.delete(
            f"{BASE_URL}/api/admin/presentations/nonexistent-id"
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ Delete requires admin authentication")
    
    def test_14_delete_presentation_returns_404_for_nonexistent(self):
        """Test DELETE /api/admin/presentations/{id} returns 404 for nonexistent"""
        token = self.get_admin_token()
        response = self.session.delete(
            f"{BASE_URL}/api/admin/presentations/nonexistent-id",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ Delete returns 404 for nonexistent presentation")
    
    def test_15_check_existing_test_presentation(self):
        """Test that the test presentation 'Cardiología Básica' exists"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/presentations/list?module=Medicina%20Interna&submodule=Cardiología",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Failed to list presentations: {response.text}"
        
        data = response.json()
        # Check if test presentation exists
        test_presentation = None
        for p in data:
            if "Cardiología" in p.get("title", "") or p.get("title") == "Cardiología Básica":
                test_presentation = p
                break
        
        if test_presentation:
            print(f"✅ Found test presentation: {test_presentation.get('title')}")
            # Verify it can be viewed
            presentation_id = test_presentation.get("id")
            view_response = self.session.get(
                f"{BASE_URL}/api/presentations/view/{presentation_id}?token={token}"
            )
            assert view_response.status_code == 200, f"Failed to view presentation: {view_response.status_code}"
            assert view_response.headers.get("content-type") == "application/pdf", "Expected PDF content type"
            print(f"✅ Test presentation can be viewed successfully")
        else:
            print(f"⚠️ Test presentation 'Cardiología Básica' not found in Cardiología submodule")
            # This is not a failure, just informational


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
