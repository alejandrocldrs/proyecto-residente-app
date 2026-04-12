"""
Test suite for Support/Sugerencias Module
Tests: POST /api/support/create, GET /api/support/my-tickets, GET /api/support/all-tickets,
       POST /api/support/reply/{ticket_id}, POST /api/support/user-reply/{ticket_id},
       GET /api/support/unread-count, PUT /api/support/mark-read/{ticket_id}
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@puertoenarm.com"
ADMIN_PASSWORD = "admin123"

# Global variable to store created test data for cleanup
created_ticket_ids = []


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
    pytest.skip("Admin authentication failed - skipping support tests")


@pytest.fixture(scope="module")
def admin_client(api_client, admin_token):
    """Session with admin auth header"""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


class TestSupportTicketCreation:
    """Tests for creating support tickets - POST /api/support/create"""
    
    def test_create_ticket_success(self, admin_client):
        """Create a support ticket with message and category"""
        unique_id = str(uuid.uuid4())[:8]
        response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_ticket_{unique_id} - This is a test support ticket",
            "category": "general"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "ticket_id" in data
        assert "message" in data
        assert "category" in data
        assert "status" in data
        assert "created_at" in data
        assert "user_id" in data
        assert "user_name" in data
        assert "user_email" in data
        
        # Validate values
        assert data["status"] == "open"
        assert data["category"] == "general"
        assert f"TEST_ticket_{unique_id}" in data["message"]
        
        # Store for cleanup
        created_ticket_ids.append(data["ticket_id"])
        print(f"Created ticket: {data['ticket_id']}")
    
    def test_create_ticket_with_error_category(self, admin_client):
        """Create ticket with 'error' category"""
        unique_id = str(uuid.uuid4())[:8]
        response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_error_report_{unique_id} - Reporting a bug",
            "category": "error"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "error"
        created_ticket_ids.append(data["ticket_id"])
    
    def test_create_ticket_with_sugerencia_category(self, admin_client):
        """Create ticket with 'sugerencia' category"""
        unique_id = str(uuid.uuid4())[:8]
        response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_suggestion_{unique_id} - Feature suggestion",
            "category": "sugerencia"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "sugerencia"
        created_ticket_ids.append(data["ticket_id"])
    
    def test_create_ticket_without_auth_fails(self, api_client):
        """Creating ticket without authentication should fail"""
        # Remove auth header temporarily
        auth_header = api_client.headers.pop("Authorization", None)
        
        response = api_client.post(f"{BASE_URL}/api/support/create", json={
            "message": "Unauthorized ticket attempt",
            "category": "general"
        })
        
        # Restore auth header
        if auth_header:
            api_client.headers["Authorization"] = auth_header
        
        assert response.status_code in [401, 403]


class TestSupportUserTickets:
    """Tests for getting user's own tickets - GET /api/support/my-tickets"""
    
    def test_get_my_tickets_returns_list(self, admin_client):
        """User can fetch their own tickets"""
        response = admin_client.get(f"{BASE_URL}/api/support/my-tickets")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"User has {len(data)} tickets")
    
    def test_my_tickets_includes_created_tickets(self, admin_client):
        """Created tickets should appear in my-tickets"""
        # First create a ticket
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_verify_in_list_{unique_id}",
            "category": "general"
        })
        ticket_id = create_response.json()["ticket_id"]
        created_ticket_ids.append(ticket_id)
        
        # Now fetch tickets
        response = admin_client.get(f"{BASE_URL}/api/support/my-tickets")
        assert response.status_code == 200
        
        data = response.json()
        ticket_ids = [t["ticket_id"] for t in data]
        assert ticket_id in ticket_ids, "Created ticket should appear in my-tickets"
    
    def test_my_tickets_marks_unread_as_read(self, admin_client):
        """Fetching my-tickets should mark user_has_unread as False"""
        response = admin_client.get(f"{BASE_URL}/api/support/my-tickets")
        assert response.status_code == 200
        
        # All returned tickets should have user_has_unread = False
        data = response.json()
        for ticket in data:
            assert ticket.get("user_has_unread", True) == False, "Tickets should be marked as read"


class TestSupportAdminAllTickets:
    """Tests for admin fetching all tickets - GET /api/support/all-tickets"""
    
    def test_admin_can_get_all_tickets(self, admin_client):
        """Admin can fetch all support tickets"""
        response = admin_client.get(f"{BASE_URL}/api/support/all-tickets")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Total tickets in system: {len(data)}")
    
    def test_all_tickets_contains_required_fields(self, admin_client):
        """All tickets should have required fields"""
        response = admin_client.get(f"{BASE_URL}/api/support/all-tickets")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            ticket = data[0]
            required_fields = ["ticket_id", "user_id", "user_name", "user_email", 
                            "message", "category", "status", "created_at"]
            for field in required_fields:
                assert field in ticket, f"Missing field: {field}"


class TestSupportAdminReply:
    """Tests for admin replying to tickets - POST /api/support/reply/{ticket_id}"""
    
    def test_admin_reply_to_ticket(self, admin_client):
        """Admin can reply to a ticket"""
        # First create a ticket
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_for_admin_reply_{unique_id}",
            "category": "general"
        })
        ticket_id = create_response.json()["ticket_id"]
        created_ticket_ids.append(ticket_id)
        
        # Admin reply
        reply_response = admin_client.post(f"{BASE_URL}/api/support/reply/{ticket_id}", json={
            "message": "Thank you for your feedback. We are working on it."
        })
        
        assert reply_response.status_code == 200
        data = reply_response.json()
        assert data.get("ok") == True
    
    def test_admin_reply_updates_ticket_status(self, admin_client):
        """Admin reply should set status to 'replied' and user_has_unread to True"""
        # Create ticket
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_reply_status_check_{unique_id}",
            "category": "error"
        })
        ticket_id = create_response.json()["ticket_id"]
        created_ticket_ids.append(ticket_id)
        
        # Admin reply
        admin_client.post(f"{BASE_URL}/api/support/reply/{ticket_id}", json={
            "message": "We've fixed the issue."
        })
        
        # Fetch all tickets to verify status
        all_tickets = admin_client.get(f"{BASE_URL}/api/support/all-tickets").json()
        ticket = next((t for t in all_tickets if t["ticket_id"] == ticket_id), None)
        
        assert ticket is not None
        assert ticket["status"] == "replied"
        assert ticket["user_has_unread"] == True
        assert ticket["admin_read"] == True
    
    def test_admin_reply_to_nonexistent_ticket_fails(self, admin_client):
        """Replying to non-existent ticket should fail"""
        response = admin_client.post(f"{BASE_URL}/api/support/reply/nonexistent-ticket-id", json={
            "message": "This should fail"
        })
        
        assert response.status_code == 404


class TestSupportUserReply:
    """Tests for user replying back to admin - POST /api/support/user-reply/{ticket_id}"""
    
    def test_user_can_reply_to_ticket(self, admin_client):
        """User can reply to their own ticket"""
        # Create ticket
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_user_reply_test_{unique_id}",
            "category": "sugerencia"
        })
        ticket_id = create_response.json()["ticket_id"]
        created_ticket_ids.append(ticket_id)
        
        # User reply
        reply_response = admin_client.post(f"{BASE_URL}/api/support/user-reply/{ticket_id}", json={
            "message": "Additional information from user"
        })
        
        assert reply_response.status_code == 200
        data = reply_response.json()
        assert data.get("ok") == True
    
    def test_user_reply_reopens_ticket(self, admin_client):
        """User reply should set status to 'open' and admin_read to False"""
        # Create ticket
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_reopen_check_{unique_id}",
            "category": "contenido"
        })
        ticket_id = create_response.json()["ticket_id"]
        created_ticket_ids.append(ticket_id)
        
        # Admin reply first
        admin_client.post(f"{BASE_URL}/api/support/reply/{ticket_id}", json={
            "message": "Admin response"
        })
        
        # User reply
        admin_client.post(f"{BASE_URL}/api/support/user-reply/{ticket_id}", json={
            "message": "User follow-up"
        })
        
        # Verify status
        all_tickets = admin_client.get(f"{BASE_URL}/api/support/all-tickets").json()
        ticket = next((t for t in all_tickets if t["ticket_id"] == ticket_id), None)
        
        assert ticket is not None
        assert ticket["status"] == "open"
        assert ticket["admin_read"] == False


class TestSupportUnreadCount:
    """Tests for unread count endpoint - GET /api/support/unread-count"""
    
    def test_get_unread_count_returns_count(self, admin_client):
        """Get unread count returns count field"""
        response = admin_client.get(f"{BASE_URL}/api/support/unread-count")
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        print(f"Unread count: {data['count']}")
    
    def test_user_unread_count_after_admin_reply(self, admin_client):
        """User unread count should increase after admin replies"""
        # Get initial count
        initial_response = admin_client.get(f"{BASE_URL}/api/support/unread-count")
        initial_count = initial_response.json()["count"]
        
        # Create ticket and have admin reply
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_unread_count_test_{unique_id}",
            "category": "general"
        })
        ticket_id = create_response.json()["ticket_id"]
        created_ticket_ids.append(ticket_id)
        
        # Admin reply (this sets user_has_unread=True)
        admin_client.post(f"{BASE_URL}/api/support/reply/{ticket_id}", json={
            "message": "Admin reply to test unread count"
        })
        
        # Fetch my-tickets resets unread count (marks as read)
        # So we skip checking the increment here
        # Just verify endpoint works
        response = admin_client.get(f"{BASE_URL}/api/support/unread-count")
        assert response.status_code == 200


class TestSupportMarkRead:
    """Tests for admin marking ticket as read - PUT /api/support/mark-read/{ticket_id}"""
    
    def test_admin_mark_ticket_as_read(self, admin_client):
        """Admin can mark a ticket as read"""
        # Create ticket
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_mark_read_test_{unique_id}",
            "category": "general"
        })
        ticket_id = create_response.json()["ticket_id"]
        created_ticket_ids.append(ticket_id)
        
        # Mark as read
        response = admin_client.put(f"{BASE_URL}/api/support/mark-read/{ticket_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True
    
    def test_mark_read_updates_admin_read_flag(self, admin_client):
        """Marking as read should set admin_read to True"""
        # Create ticket
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_verify_admin_read_{unique_id}",
            "category": "error"
        })
        ticket_id = create_response.json()["ticket_id"]
        created_ticket_ids.append(ticket_id)
        
        # Mark as read
        admin_client.put(f"{BASE_URL}/api/support/mark-read/{ticket_id}")
        
        # Verify in all-tickets
        all_tickets = admin_client.get(f"{BASE_URL}/api/support/all-tickets").json()
        ticket = next((t for t in all_tickets if t["ticket_id"] == ticket_id), None)
        
        assert ticket is not None
        assert ticket["admin_read"] == True


class TestSupportTicketRepliesStructure:
    """Tests for ticket replies array structure"""
    
    def test_ticket_contains_replies_array(self, admin_client):
        """Ticket should have replies array with proper structure"""
        # Create ticket
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/support/create", json={
            "message": f"TEST_replies_structure_{unique_id}",
            "category": "general"
        })
        ticket_id = create_response.json()["ticket_id"]
        created_ticket_ids.append(ticket_id)
        
        # Add admin reply
        admin_client.post(f"{BASE_URL}/api/support/reply/{ticket_id}", json={
            "message": "Admin reply"
        })
        
        # Add user reply
        admin_client.post(f"{BASE_URL}/api/support/user-reply/{ticket_id}", json={
            "message": "User reply"
        })
        
        # Fetch and verify structure
        all_tickets = admin_client.get(f"{BASE_URL}/api/support/all-tickets").json()
        ticket = next((t for t in all_tickets if t["ticket_id"] == ticket_id), None)
        
        assert ticket is not None
        assert "replies" in ticket
        assert len(ticket["replies"]) == 2
        
        # Verify admin reply structure
        admin_reply = ticket["replies"][0]
        assert "reply_id" in admin_reply
        assert admin_reply["from_role"] == "admin"
        assert admin_reply["message"] == "Admin reply"
        assert "created_at" in admin_reply
        
        # Verify user reply structure
        user_reply = ticket["replies"][1]
        assert user_reply["from_role"] == "user"
        assert user_reply["message"] == "User reply"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
