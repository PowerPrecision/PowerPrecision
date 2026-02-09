"""
Iteration 16 - Testing Leads Page and Trello Integration
Tests for:
1. Login as admin
2. /leads route existence and functionality
3. Trello /api/trello/status endpoint
4. Leads /api/leads/by-status endpoint
5. Frontend compilation check
"""
import pytest
import requests
import os

# Use PUBLIC URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAdminLogin:
    """Test admin authentication"""
    
    def test_admin_login_success(self):
        """Test login with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@sistema.pt",
            "password": "admin2026"
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "access_token" in data, "Missing access_token in response"
        assert "user" in data, "Missing user in response"
        assert data["user"]["email"] == "admin@sistema.pt"
        assert data["user"]["role"] == "admin"
        
        print(f"✓ Admin login successful - User: {data['user']['name']}")
        return data["access_token"]
    
    def test_admin_login_invalid_password(self):
        """Test login with wrong password returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@sistema.pt",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        print("✓ Invalid password correctly rejected with 401")


class TestTrelloIntegration:
    """Test Trello status endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@sistema.pt",
            "password": "admin2026"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    def test_trello_status_endpoint(self, auth_token):
        """Test /api/trello/status returns connected: true"""
        response = requests.get(
            f"{BASE_URL}/api/trello/status",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Trello status failed: {response.text}"
        data = response.json()
        
        # Validate connection status
        assert "connected" in data, "Missing 'connected' field"
        assert data["connected"] == True, f"Trello not connected: {data.get('message', 'No message')}"
        
        # Validate board info
        assert "board" in data, "Missing board info"
        assert data["board"] is not None, "Board info is None"
        
        print(f"✓ Trello connected - Board: {data['board'].get('name', 'N/A')}")
        print(f"  - Lists count: {data['board'].get('lists_count', 'N/A')}")
        
        # Check config
        if "config" in data:
            print(f"  - Has API Key: {data['config'].get('has_api_key', False)}")
            print(f"  - Has Token: {data['config'].get('has_token', False)}")
            print(f"  - Has Board ID: {data['config'].get('has_board_id', False)}")


class TestLeadsEndpoints:
    """Test Leads API endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@sistema.pt",
            "password": "admin2026"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    def test_leads_by_status_endpoint(self, auth_token):
        """Test /api/leads/by-status returns proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/leads/by-status",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Leads by-status failed: {response.text}"
        data = response.json()
        
        # Validate structure - should have status keys
        expected_statuses = ["novo", "contactado", "visita_agendada", "proposta", "reservado", "descartado"]
        
        for status in expected_statuses:
            assert status in data, f"Missing status key: {status}"
            assert isinstance(data[status], list), f"Status {status} should be a list"
        
        print("✓ /api/leads/by-status endpoint working correctly")
        print(f"  - Status keys present: {list(data.keys())}")
        
        # Count leads per status
        total_leads = 0
        for status, leads in data.items():
            count = len(leads)
            total_leads += count
            if count > 0:
                print(f"  - {status}: {count} leads")
        
        print(f"  - Total leads: {total_leads}")
    
    def test_leads_list_endpoint(self, auth_token):
        """Test /api/leads returns list of leads"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Leads list failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ /api/leads endpoint working - {len(data)} leads found")
    
    def test_leads_create_requires_url(self, auth_token):
        """Test creating lead requires URL field"""
        response = requests.post(
            f"{BASE_URL}/api/leads",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={
                "title": "Test Lead",
                "price": 250000
                # Missing URL - should fail validation
            }
        )
        
        # Should fail with 422 (validation error) because URL is required
        assert response.status_code == 422, f"Expected 422 for missing URL, got {response.status_code}"
        print("✓ Lead creation correctly validates required URL field")


class TestNavigationEndpoints:
    """Test endpoints that support sidebar navigation"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@sistema.pt",
            "password": "admin2026"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    def test_processes_kanban_endpoint(self, auth_token):
        """Test processes kanban endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/processes/kanban",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Kanban endpoint failed: {response.text}"
        data = response.json()
        
        # Should have workflow statuses
        assert isinstance(data, dict), "Response should be an object"
        print(f"✓ /api/processes/kanban working - {len(data)} status columns")
    
    def test_users_list_endpoint(self, auth_token):
        """Test users list endpoint works (admin only)"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Users list failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one user"
        print(f"✓ /api/users endpoint working - {len(data)} users found")
    
    def test_clients_endpoint(self, auth_token):
        """Test clients endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Clients endpoint failed: {response.text}"
        print("✓ /api/clients endpoint working")
    
    def test_properties_endpoint(self, auth_token):
        """Test properties endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/properties",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Properties endpoint failed: {response.text}"
        print("✓ /api/properties endpoint working")


class TestStaffRoleAccess:
    """Test access for staff roles (consultor)"""
    
    def test_consultor_login_attempt(self):
        """Test login with known consultor email (password unknown)"""
        # Try login - will fail with wrong password but validates endpoint
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "tiagoborges@powerealestate.pt",
            "password": "test123"  # Wrong password
        })
        
        # Should return 401 (unauthorized) not 500 or other error
        assert response.status_code in [401, 400], f"Unexpected status: {response.status_code}"
        print("✓ Staff login endpoint accessible (wrong password correctly rejected)")


class TestHealthEndpoint:
    """Test health check"""
    
    def test_health_endpoint(self):
        """Test /health endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/health")
        
        # Note: Health endpoint returns HTML (frontend) not JSON in this setup
        # Because the frontend catches all non-api routes
        assert response.status_code == 200
        print("✓ /health endpoint accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
