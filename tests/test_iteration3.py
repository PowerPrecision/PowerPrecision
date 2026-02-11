"""
Backend API Tests for Power Real Estate & Precision Client Registration System
Iteration 3 - Testing:
1. Admin login and dashboard
2. Calendar events with consultor/mediador assignments
3. Workflow statuses (verify 'autorização bancária' removed)
4. User count verification (should be ~10, not 40+)
5. Consultor and Mediador login
6. Public form submission
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://real-estate-crm-9.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@sistema.pt"
ADMIN_PASSWORD = "admin123"
CONSULTOR_EMAIL = "consultor@sistema.pt"
CONSULTOR_PASSWORD = "consultor123"
MEDIADOR_EMAIL = "mediador@sistema.pt"
MEDIADOR_PASSWORD = "mediador123"


class TestHealthCheck:
    """Health check tests"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ API health check passed")


class TestAuthentication:
    """Authentication tests for all user roles"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful: {data['user']['name']}")
    
    def test_consultor_login(self):
        """Test consultor login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CONSULTOR_EMAIL,
            "password": CONSULTOR_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "consultor"
        print(f"✓ Consultor login successful: {data['user']['name']}")
    
    def test_mediador_login(self):
        """Test mediador login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MEDIADOR_EMAIL,
            "password": MEDIADOR_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "mediador"
        print(f"✓ Mediador login successful: {data['user']['name']}")
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@email.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected")


class TestWorkflowStatuses:
    """Workflow status tests - verify 'autorização bancária' removed"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_workflow_statuses_exist(self, admin_token):
        """Test that workflow statuses exist"""
        response = requests.get(
            f"{BASE_URL}/api/workflow-statuses",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        statuses = response.json()
        assert len(statuses) >= 4
        print(f"✓ Found {len(statuses)} workflow statuses")
    
    def test_autorizacao_bancaria_removed(self, admin_token):
        """Test that 'autorização bancária' status has been removed"""
        response = requests.get(
            f"{BASE_URL}/api/workflow-statuses",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        statuses = response.json()
        status_names = [s["name"] for s in statuses]
        
        # Verify 'autorizacao_bancaria' is NOT in the list
        assert "autorizacao_bancaria" not in status_names, \
            f"'autorizacao_bancaria' should be removed but found in: {status_names}"
        
        # Verify expected statuses exist
        expected_statuses = ["pedido_inicial", "em_analise", "aprovado", "rejeitado"]
        for expected in expected_statuses:
            assert expected in status_names, f"Expected status '{expected}' not found"
        
        print(f"✓ 'autorização bancária' correctly removed. Current statuses: {status_names}")


class TestUserManagement:
    """User management tests - verify cleanup"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_user_count_cleaned_up(self, admin_token):
        """Test that test users have been cleaned up (should be ~10, not 40+)"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users = response.json()
        
        # Should be around 10-15 users, not 40+
        assert len(users) <= 20, f"Expected ~10 users but found {len(users)} - cleanup may not have worked"
        
        # Count by role
        roles = {}
        for user in users:
            role = user["role"]
            roles[role] = roles.get(role, 0) + 1
        
        print(f"✓ User count verified: {len(users)} total users")
        print(f"  - Roles breakdown: {roles}")
    
    def test_required_users_exist(self, admin_token):
        """Test that required users exist"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users = response.json()
        
        emails = [u["email"] for u in users]
        
        # Check required users exist
        assert ADMIN_EMAIL in emails, "Admin user not found"
        assert CONSULTOR_EMAIL in emails, "Consultor user not found"
        assert MEDIADOR_EMAIL in emails, "Mediador user not found"
        
        print("✓ Required users (admin, consultor, mediador) exist")


class TestCalendarDeadlines:
    """Calendar and deadline tests with consultor/mediador assignments"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def consultor_id(self, admin_token):
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        users = response.json()
        for user in users:
            if user["role"] == "consultor":
                return user["id"]
        return None
    
    @pytest.fixture
    def mediador_id(self, admin_token):
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        users = response.json()
        for user in users:
            if user["role"] == "mediador":
                return user["id"]
        return None
    
    def test_get_calendar_deadlines(self, admin_token):
        """Test getting calendar deadlines"""
        response = requests.get(
            f"{BASE_URL}/api/deadlines/calendar",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        deadlines = response.json()
        assert isinstance(deadlines, list)
        print(f"✓ Calendar deadlines retrieved: {len(deadlines)} events")
    
    def test_create_deadline_with_assignments(self, admin_token, consultor_id, mediador_id):
        """Test creating a deadline with consultor and mediador assignments"""
        deadline_data = {
            "title": "TEST_Pytest Event with Assignments",
            "description": "Testing consultor and mediador assignment via pytest",
            "due_date": "2026-01-30",
            "priority": "high",
            "assigned_consultor_id": consultor_id,
            "assigned_mediador_id": mediador_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/deadlines",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=deadline_data
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert data["title"] == deadline_data["title"]
        assert data["assigned_consultor_id"] == consultor_id
        assert data["assigned_mediador_id"] == mediador_id
        
        print(f"✓ Deadline created with assignments:")
        print(f"  - Consultor ID: {consultor_id}")
        print(f"  - Mediador ID: {mediador_id}")
        
        # Cleanup - delete the test deadline
        deadline_id = data["id"]
        delete_response = requests.delete(
            f"{BASE_URL}/api/deadlines/{deadline_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert delete_response.status_code == 200
        print(f"✓ Test deadline cleaned up")
    
    def test_calendar_filter_by_consultor(self, admin_token, consultor_id):
        """Test filtering calendar by consultor"""
        response = requests.get(
            f"{BASE_URL}/api/deadlines/calendar?consultor_id={consultor_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        deadlines = response.json()
        print(f"✓ Calendar filtered by consultor: {len(deadlines)} events")
    
    def test_calendar_filter_by_mediador(self, admin_token, mediador_id):
        """Test filtering calendar by mediador"""
        response = requests.get(
            f"{BASE_URL}/api/deadlines/calendar?mediador_id={mediador_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        deadlines = response.json()
        print(f"✓ Calendar filtered by mediador: {len(deadlines)} events")


class TestPublicRegistration:
    """Public client registration tests"""
    
    def test_public_registration(self):
        """Test public client registration endpoint"""
        import uuid
        unique_email = f"test.pytest.{uuid.uuid4().hex[:8]}@email.pt"
        
        registration_data = {
            "name": "TEST_Pytest User",
            "email": unique_email,
            "phone": "+351 999 000 111",
            "process_type": "credito"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/public/client-registration",
            json=registration_data
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "process_id" in data
        
        print(f"✓ Public registration successful:")
        print(f"  - Process ID: {data['process_id']}")
        print(f"  - Email: {unique_email}")


class TestProcesses:
    """Process management tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_processes(self, admin_token):
        """Test getting all processes"""
        response = requests.get(
            f"{BASE_URL}/api/processes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        processes = response.json()
        assert isinstance(processes, list)
        print(f"✓ Processes retrieved: {len(processes)} total")
    
    def test_get_stats(self, admin_token):
        """Test getting statistics"""
        response = requests.get(
            f"{BASE_URL}/api/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        stats = response.json()
        
        # Verify stats structure
        assert "total_processes" in stats or "total_users" in stats
        print(f"✓ Stats retrieved: {stats}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
