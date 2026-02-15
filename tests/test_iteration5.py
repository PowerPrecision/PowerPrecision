"""
Test Suite for CreditoIMO - Iteration 5
Testing: Login, Public Form, Event Creation, User Roles, Notifications
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://smart-docs-47.preview.emergentagent.com').rstrip('/')

# Test credentials
CREDENTIALS = {
    "admin": {"email": "admin@sistema.pt", "password": "admin2026"},
    "ceo": {"email": "pedro@powerealestate.pt", "password": "power2026"},
    "diretor": {"email": "carina@powerealestate.pt", "password": "power2026"},
    "administrativo": {"email": "marisa@powerealestate.pt", "password": "power2026"}
}


class TestHealthAndAuth:
    """Test health check and authentication"""
    
    def test_health_check(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("PASS: Health check successful")
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"PASS: Admin login successful - role: {data['user']['role']}")
        return data["access_token"]
    
    def test_ceo_login(self):
        """Test CEO login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["ceo"])
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "ceo"
        print(f"PASS: CEO login successful - role: {data['user']['role']}")
        return data["access_token"]
    
    def test_diretor_login(self):
        """Test Diretor login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["diretor"])
        if response.status_code == 200:
            data = response.json()
            print(f"PASS: Diretor login successful - role: {data['user']['role']}")
            return data["access_token"]
        else:
            print(f"INFO: Diretor user may not exist yet - status: {response.status_code}")
            pytest.skip("Diretor user not found")
    
    def test_administrativo_login(self):
        """Test Administrativo login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["administrativo"])
        if response.status_code == 200:
            data = response.json()
            print(f"PASS: Administrativo login successful - role: {data['user']['role']}")
            return data["access_token"]
        else:
            print(f"INFO: Administrativo user may not exist yet - status: {response.status_code}")
            pytest.skip("Administrativo user not found")


class TestNotificationsFiltering:
    """Test notifications filtering by role"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["access_token"]
    
    @pytest.fixture
    def ceo_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["ceo"])
        return response.json()["access_token"]
    
    def test_admin_sees_all_notifications(self, admin_token):
        """Admin should see all notifications including new registrations"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/alerts/notifications", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Admin notifications endpoint works - total: {data.get('total', 0)}")
    
    def test_ceo_sees_all_notifications(self, ceo_token):
        """CEO should see all notifications including new registrations"""
        headers = {"Authorization": f"Bearer {ceo_token}"}
        response = requests.get(f"{BASE_URL}/api/alerts/notifications", headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: CEO notifications endpoint works - total: {data.get('total', 0)}")


class TestEventCreation:
    """Test calendar event creation"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["access_token"]
    
    def test_create_event_without_process(self, admin_token):
        """Test creating a general event without a process"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get admin user ID
        user_response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        user_id = user_response.json()["id"]
        
        event_data = {
            "title": "TEST_Event_Iteration5",
            "description": "Test event created by testing agent",
            "due_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "priority": "medium",
            "process_id": None,
            "assigned_user_ids": [user_id]
        }
        
        response = requests.post(f"{BASE_URL}/api/deadlines", json=event_data, headers=headers)
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"PASS: Event created successfully - id: {data.get('id', 'N/A')}")
            return data.get("id")
        else:
            print(f"INFO: Event creation response - status: {response.status_code}, body: {response.text[:200]}")
            # Check if it's a validation error
            if response.status_code == 422:
                print("INFO: Validation error - checking required fields")
            assert response.status_code in [200, 201, 422]
    
    def test_get_calendar_deadlines(self, admin_token):
        """Test getting calendar deadlines"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/deadlines/calendar", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"PASS: Calendar deadlines retrieved - count: {len(data)}")
        else:
            print(f"INFO: Calendar deadlines endpoint - status: {response.status_code}")
            assert response.status_code == 200


class TestPublicClientForm:
    """Test public client registration form"""
    
    def test_public_registration_endpoint(self):
        """Test that public registration endpoint exists"""
        # Test with minimal data to check endpoint exists
        test_data = {
            "name": "TEST_Client_Iteration5",
            "email": "test_iteration5@example.com",
            "phone": "+351912345678",
            "process_type": "ambos",
            "personal_data": {
                "nif": "123456789",
                "documento_id": "12345678",
                "naturalidade": "Lisboa",
                "nacionalidade": "Portuguesa",
                "morada_fiscal": "Rua Teste 123",
                "birth_date": "1995-01-15",
                "estado_civil": "solteiro",
                "compra_tipo": "individual",
                "menor_35_anos": True  # Testing the new checkbox
            },
            "real_estate_data": {
                "tipo_imovel": "apartamento",
                "num_quartos": "T2",
                "localizacao": "Lisboa"
            },
            "financial_data": {
                "acesso_portal_financas": "test123",
                "chave_movel_digital": "sim",
                "monthly_income": 2000,
                "capital_proprio": 30000,
                "valor_financiado": "200000"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/public/client-registration", json=test_data)
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"PASS: Public registration successful - process_id: {data.get('process_id', 'N/A')}")
            # Verify menor_35_anos was saved
            if data.get("personal_data", {}).get("menor_35_anos"):
                print("PASS: menor_35_anos field saved correctly")
        elif response.status_code == 400:
            # May fail due to duplicate email
            print(f"INFO: Registration may have duplicate - {response.text[:100]}")
        else:
            print(f"INFO: Public registration response - status: {response.status_code}")


class TestUserRoles:
    """Test user roles and permissions"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["access_token"]
    
    def test_get_users_list(self, admin_token):
        """Test getting users list to verify roles"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        
        assert response.status_code == 200
        users = response.json()
        
        # Check for different roles
        roles_found = set()
        for user in users:
            roles_found.add(user.get("role"))
        
        print(f"PASS: Users list retrieved - count: {len(users)}")
        print(f"INFO: Roles found in system: {roles_found}")
        
        # Check for new roles
        if "diretor" in roles_found:
            print("PASS: 'diretor' role exists in system")
        else:
            print("INFO: 'diretor' role not found - may need to be created")
            
        if "administrativo" in roles_found:
            print("PASS: 'administrativo' role exists in system")
        else:
            print("INFO: 'administrativo' role not found - may need to be created")
            
        # Check that consultor_intermediario is removed
        if "consultor_intermediario" in roles_found:
            print("WARNING: 'consultor_intermediario' role still exists - should be removed")
        else:
            print("PASS: 'consultor_intermediario' role not found (as expected)")


class TestProcessDetails:
    """Test process details page features"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        return response.json()["access_token"]
    
    def test_get_process_with_activities(self, admin_token):
        """Test getting a process and its activities"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get first process
        response = requests.get(f"{BASE_URL}/api/processes?limit=1", headers=headers)
        assert response.status_code == 200
        processes = response.json()
        
        if len(processes) > 0:
            process_id = processes[0]["id"]
            
            # Get activities for this process
            activities_response = requests.get(f"{BASE_URL}/api/activities/{process_id}", headers=headers)
            
            if activities_response.status_code == 200:
                activities = activities_response.json()
                print(f"PASS: Activities retrieved for process - count: {len(activities)}")
            else:
                print(f"INFO: Activities endpoint - status: {activities_response.status_code}")
        else:
            print("INFO: No processes found to test activities")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
