"""
Iteration 42: Backend API Bug Fixes Test Suite

Tests for the following bug fixes:
1. PUT /api/auth/profile - User can update their own profile (name, phone)
2. POST /api/auth/change-password - User can change their password
3. POST /api/clients/{client_id}/create-process - Create process for existing client (using process_id)

Test credentials:
- Admin: admin@admin.com / adminadmin (note: password was changed during testing)
- Consultor: flaviosilva@powerealestate.pt / flavio123
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin password (was changed during testing from 'admin' to 'adminadmin' since validation requires 6+ chars)
ADMIN_PASSWORD = "adminadmin"

class TestAuthProfileUpdate:
    """Test PUT /api/auth/profile - Update user's own profile"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@admin.com",
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.user = data.get("user", {})
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        print(f"Logged in as admin: {self.user.get('name')}")
    
    def test_update_profile_name_success(self):
        """Test updating profile name"""
        # Get current user info
        me_response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        original_name = me_response.json().get("name")
        print(f"Original name: {original_name}")
        
        # Update name
        new_name = f"Admin Updated {os.urandom(4).hex()}"
        update_response = self.session.put(f"{BASE_URL}/api/auth/profile", json={
            "name": new_name
        })
        
        assert update_response.status_code == 200, f"Profile update failed: {update_response.text}"
        data = update_response.json()
        assert data.get("success") == True
        assert "user" in data
        assert data["user"]["name"] == new_name
        print(f"Name updated to: {new_name}")
        
        # Verify with GET /me
        verify_response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert verify_response.status_code == 200
        assert verify_response.json().get("name") == new_name
        print("Name change verified with GET /me")
        
        # Restore original name
        restore_response = self.session.put(f"{BASE_URL}/api/auth/profile", json={
            "name": "Admin"
        })
        assert restore_response.status_code == 200
        print("Name restored to original")
    
    def test_update_profile_phone_success(self):
        """Test updating profile phone"""
        # Update phone
        new_phone = "+351912000001"
        update_response = self.session.put(f"{BASE_URL}/api/auth/profile", json={
            "phone": new_phone
        })
        
        assert update_response.status_code == 200, f"Phone update failed: {update_response.text}"
        data = update_response.json()
        assert data.get("success") == True
        assert data["user"]["phone"] == new_phone
        print(f"Phone updated to: {new_phone}")
    
    def test_update_profile_name_and_phone(self):
        """Test updating both name and phone"""
        update_response = self.session.put(f"{BASE_URL}/api/auth/profile", json={
            "name": "Admin Test",
            "phone": "+351912000002"
        })
        
        assert update_response.status_code == 200
        data = update_response.json()
        assert data.get("success") == True
        assert data["user"]["name"] == "Admin Test"
        assert data["user"]["phone"] == "+351912000002"
        print("Both name and phone updated successfully")
        
        # Restore
        self.session.put(f"{BASE_URL}/api/auth/profile", json={"name": "Admin"})
    
    def test_update_profile_empty_body_fails(self):
        """Test that empty update body returns error"""
        update_response = self.session.put(f"{BASE_URL}/api/auth/profile", json={})
        
        assert update_response.status_code == 400, f"Expected 400, got {update_response.status_code}"
        print("Empty body correctly rejected with 400")
    
    def test_update_profile_unauthorized(self):
        """Test that unauthorized requests fail"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.put(f"{BASE_URL}/api/auth/profile", json={
            "name": "Hacker"
        })
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Unauthorized request correctly rejected")


class TestChangePassword:
    """Test POST /api/auth/change-password - Change user password"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as consultor for password change tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # We'll use admin for tests since changing consultor password could break other tests
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@admin.com",
            "password": "admin"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        print("Logged in as admin for password tests")
    
    def test_change_password_wrong_current_password(self):
        """Test that wrong current password fails"""
        response = self.session.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": "wrongpassword123",
            "new_password": "newpassword123"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "incorreta" in data.get("detail", "").lower() or "invalid" in data.get("detail", "").lower() or "errada" in data.get("detail", "").lower()
        print("Wrong current password correctly rejected")
    
    def test_change_password_short_new_password(self):
        """Test that short new password fails"""
        response = self.session.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": ADMIN_PASSWORD,
            "new_password": "123"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "6 caracteres" in data.get("detail", "") or "too short" in data.get("detail", "").lower()
        print("Short password correctly rejected")
    
    def test_change_password_missing_fields(self):
        """Test that missing fields fail"""
        # Missing new password
        response = self.session.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": ADMIN_PASSWORD
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("Missing new_password correctly rejected")
        
        # Missing current password
        response = self.session.post(f"{BASE_URL}/api/auth/change-password", json={
            "new_password": "newpassword123"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("Missing current_password correctly rejected")
    
    def test_change_password_success_and_restore(self):
        """Test successful password change and restore (cycle test)"""
        global ADMIN_PASSWORD
        
        # Change to new password
        new_password = "testchange123"
        response = self.session.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": ADMIN_PASSWORD,
            "new_password": new_password
        })
        
        assert response.status_code == 200, f"Password change failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("Password changed successfully")
        
        # Login with new password
        time.sleep(1)  # Small delay to avoid rate limits
        new_session = requests.Session()
        new_session.headers.update({"Content-Type": "application/json"})
        login_response = new_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@admin.com",
            "password": new_password
        })
        
        assert login_response.status_code == 200, f"Login with new password failed: {login_response.text}"
        new_token = login_response.json().get("access_token")
        new_session.headers.update({"Authorization": f"Bearer {new_token}"})
        print("Login with new password successful")
        
        # Restore original password
        restore_response = new_session.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": new_password,
            "new_password": ADMIN_PASSWORD
        })
        
        assert restore_response.status_code == 200, f"Password restore failed: {restore_response.text}"
        print("Password restored to original")
        
        # Verify login with original password
        time.sleep(1)  # Small delay to avoid rate limits
        verify_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@admin.com",
            "password": ADMIN_PASSWORD
        }, headers={"Content-Type": "application/json"})
        
        assert verify_response.status_code == 200, "Login with restored password failed"
        print("Password restore verified")
    
    def test_change_password_unauthorized(self):
        """Test that unauthorized requests fail"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": "admin",
            "new_password": "hacked123"
        })
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Unauthorized request correctly rejected")


class TestCreateProcessForClient:
    """Test POST /api/clients/{client_id}/create-process - Create process from client management"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@admin.com",
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        print("Logged in as admin")
    
    def test_create_process_for_virtual_client_using_process_id(self):
        """Test creating a new process using an existing process_id as client_id (virtual client)"""
        # First, get a list of existing processes to get a process_id
        processes_response = self.session.get(f"{BASE_URL}/api/processes?limit=5")
        assert processes_response.status_code == 200, f"Failed to get processes: {processes_response.text}"
        
        processes = processes_response.json()
        assert len(processes) > 0, "No processes found for testing"
        
        # Get first process
        existing_process = processes[0]
        process_id = existing_process.get("id")
        client_name = existing_process.get("client_name")
        print(f"Using process_id: {process_id} (client: {client_name})")
        
        # Now create a new process using this process_id as client_id
        create_response = self.session.post(
            f"{BASE_URL}/api/clients/{process_id}/create-process?process_type=credito_habitacao"
        )
        
        assert create_response.status_code == 200, f"Create process failed: {create_response.text}"
        data = create_response.json()
        assert data.get("success") == True
        assert "process_id" in data
        assert "process_number" in data
        new_process_id = data.get("process_id")
        new_process_number = data.get("process_number")
        print(f"New process created: #{new_process_number} (id: {new_process_id})")
        
        # Verify the new process exists and has correct client data
        verify_response = self.session.get(f"{BASE_URL}/api/processes/{new_process_id}")
        assert verify_response.status_code == 200, f"Failed to get new process: {verify_response.text}"
        
        new_process = verify_response.json()
        assert new_process.get("client_name") == client_name
        assert new_process.get("process_type") == "credito_habitacao"
        print(f"New process verified with client_name: {new_process.get('client_name')}")
        
        # Cleanup: Archive the new test process
        archive_response = self.session.patch(
            f"{BASE_URL}/api/processes/{new_process_id}/status?status=arquivado"
        )
        if archive_response.status_code == 200:
            print("Test process archived")
    
    def test_create_process_different_types(self):
        """Test creating processes with different types"""
        # Get a process to use as client
        processes_response = self.session.get(f"{BASE_URL}/api/processes?limit=1")
        processes = processes_response.json()
        if not processes:
            pytest.skip("No processes available for testing")
        
        process_id = processes[0].get("id")
        created_ids = []
        
        process_types = ["compra_direta", "arrendamento", "consultoria"]
        
        for ptype in process_types:
            create_response = self.session.post(
                f"{BASE_URL}/api/clients/{process_id}/create-process?process_type={ptype}"
            )
            
            assert create_response.status_code == 200, f"Create {ptype} process failed: {create_response.text}"
            data = create_response.json()
            created_ids.append(data.get("process_id"))
            print(f"Created {ptype} process: #{data.get('process_number')}")
        
        # Cleanup
        for pid in created_ids:
            self.session.patch(f"{BASE_URL}/api/processes/{pid}/status?status=arquivado")
        print("Test processes archived")
    
    def test_create_process_invalid_client_id(self):
        """Test that invalid client_id returns 404"""
        create_response = self.session.post(
            f"{BASE_URL}/api/clients/invalid-uuid-12345/create-process?process_type=credito_habitacao"
        )
        
        assert create_response.status_code == 404, f"Expected 404, got {create_response.status_code}"
        print("Invalid client_id correctly returns 404")


class TestConsultorLogin:
    """Test consultor login for role-specific tests"""
    
    def test_consultor_login_success(self):
        """Test that consultor can login"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "flaviosilva@powerealestate.pt",
            "password": "flavio123"
        })
        
        assert response.status_code == 200, f"Consultor login failed: {response.text}"
        data = response.json()
        assert data.get("user", {}).get("role") == "consultor"
        print(f"Consultor logged in: {data.get('user', {}).get('name')}")
    
    def test_consultor_can_update_own_profile(self):
        """Test that consultor can update their own profile"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login as consultor
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "flaviosilva@powerealestate.pt",
            "password": "flavio123"
        })
        assert login_response.status_code == 200
        token = login_response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Update profile
        update_response = session.put(f"{BASE_URL}/api/auth/profile", json={
            "phone": "+351913000001"
        })
        
        assert update_response.status_code == 200, f"Profile update failed: {update_response.text}"
        data = update_response.json()
        assert data.get("success") == True
        print("Consultor profile update successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
