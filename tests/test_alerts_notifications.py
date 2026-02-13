"""
Backend API Tests for CreditoIMO Alerts & Notifications System
Iteration 4 - Testing:
1. GET /api/processes/{id}/alerts - Process alerts endpoint
2. GET /api/alerts/notifications - User notifications endpoint
3. PUT /api/alerts/notifications/{id}/read - Mark notification as read
4. Alerts for age < 35 years (Apoio ao Estado)
5. Alerts for 90-day countdown after pre-approval
6. Alerts for documents expiring in 15 days
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://consultant-hub-40.preview.emergentagent.com')

# Test credentials from review request
ADMIN_CREDENTIALS = {"email": "admin@sistema.pt", "password": "admin2026"}
CONSULTOR_CREDENTIALS = {"email": "flavio@powerealestate.pt", "password": "power2026"}
INTERMEDIARIO_CREDENTIALS = {"email": "estacio@precisioncredito.pt", "password": "power2026"}


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
        """Test admin login with new credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {data['user']['name']}")
    
    def test_consultor_login(self):
        """Test consultor login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CONSULTOR_CREDENTIALS)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "consultor"
        print(f"✓ Consultor login successful: {data['user']['name']}")
    
    def test_intermediario_login(self):
        """Test intermediario login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=INTERMEDIARIO_CREDENTIALS)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "intermediario"
        print(f"✓ Intermediario login successful: {data['user']['name']}")


class TestNotificationsAPI:
    """Notifications API tests - GET /api/alerts/notifications"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def consultor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CONSULTOR_CREDENTIALS)
        return response.json()["access_token"]
    
    def test_get_notifications_admin(self, admin_token):
        """Test getting notifications as admin"""
        response = requests.get(
            f"{BASE_URL}/api/alerts/notifications",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "notifications" in data
        assert "total" in data
        assert "unread" in data
        assert isinstance(data["notifications"], list)
        
        print(f"✓ Admin notifications: {data['total']} total, {data['unread']} unread")
        
        # Verify notification structure if any exist
        if data["notifications"]:
            notification = data["notifications"][0]
            assert "id" in notification
            assert "type" in notification
            assert "message" in notification
            assert "read" in notification
            assert "created_at" in notification
            print(f"  - First notification: {notification['message'][:50]}...")
    
    def test_get_notifications_consultor(self, consultor_token):
        """Test getting notifications as consultor (filtered by assigned processes)"""
        response = requests.get(
            f"{BASE_URL}/api/alerts/notifications",
            headers={"Authorization": f"Bearer {consultor_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "notifications" in data
        assert "total" in data
        assert "unread" in data
        
        print(f"✓ Consultor notifications: {data['total']} total, {data['unread']} unread")
    
    def test_get_unread_only_notifications(self, admin_token):
        """Test getting only unread notifications"""
        response = requests.get(
            f"{BASE_URL}/api/alerts/notifications?unread_only=true",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned notifications should be unread
        for notification in data["notifications"]:
            assert notification["read"] == False
        
        print(f"✓ Unread notifications filter working: {len(data['notifications'])} unread")


class TestProcessAlertsAPI:
    """Process Alerts API tests - GET /api/processes/{id}/alerts"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def process_with_alerts(self, admin_token):
        """Get a process that has alerts (Fernanda Nunes - age < 35 and document expiry)"""
        response = requests.get(
            f"{BASE_URL}/api/processes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        processes = response.json()
        # Find Fernanda Nunes process
        for p in processes:
            if p.get("client_name") == "Fernanda Nunes":
                return p["id"]
        # Return first process if not found
        return processes[0]["id"] if processes else None
    
    @pytest.fixture
    def process_with_countdown(self, admin_token):
        """Get a process with ch_aprovado status (has countdown alert)"""
        response = requests.get(
            f"{BASE_URL}/api/processes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        processes = response.json()
        for p in processes:
            if p.get("status") == "ch_aprovado":
                return p["id"]
        return None
    
    def test_get_process_alerts(self, admin_token, process_with_alerts):
        """Test getting alerts for a specific process"""
        if not process_with_alerts:
            pytest.skip("No process found for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/processes/{process_with_alerts}/alerts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "process_id" in data
        assert "client_name" in data
        assert "alerts" in data
        assert "total" in data
        assert "has_critical" in data
        assert "has_high" in data
        
        print(f"✓ Process alerts for {data['client_name']}: {data['total']} alerts")
        
        # Verify alert structure if any exist
        if data["alerts"]:
            alert = data["alerts"][0]
            assert "type" in alert
            assert "active" in alert
            assert "message" in alert
            assert "priority" in alert
            print(f"  - Alert types: {[a['type'] for a in data['alerts']]}")
    
    def test_age_under_35_alert(self, admin_token, process_with_alerts):
        """Test that age < 35 alert is returned correctly"""
        if not process_with_alerts:
            pytest.skip("No process found for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/processes/{process_with_alerts}/alerts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check for age alert
        age_alerts = [a for a in data["alerts"] if a["type"] == "age_under_35"]
        
        if age_alerts:
            alert = age_alerts[0]
            assert alert["active"] == True
            assert "Apoio ao Estado" in alert["message"] or "menos de 35" in alert["message"]
            assert alert["priority"] == "info"
            print(f"✓ Age alert found: {alert['message']}")
        else:
            print("✓ No age alert (client may be >= 35 years)")
    
    def test_pre_approval_countdown_alert(self, admin_token, process_with_countdown):
        """Test that 90-day countdown alert is returned for approved processes"""
        if not process_with_countdown:
            pytest.skip("No approved process found for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/processes/{process_with_countdown}/alerts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check for countdown alert
        countdown_alerts = [a for a in data["alerts"] if a["type"] == "pre_approval_countdown"]
        
        if countdown_alerts:
            alert = countdown_alerts[0]
            assert alert["active"] == True
            assert "days_remaining" in alert or "dias" in alert["message"]
            assert alert["priority"] in ["low", "medium", "high", "critical"]
            print(f"✓ Countdown alert found: {alert['message']}")
            if "days_remaining" in alert:
                print(f"  - Days remaining: {alert['days_remaining']}")
        else:
            print("✓ No countdown alert (may not have approval date)")
    
    def test_document_expiry_alert(self, admin_token, process_with_alerts):
        """Test that document expiry alerts are returned"""
        if not process_with_alerts:
            pytest.skip("No process found for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/processes/{process_with_alerts}/alerts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check for document expiry alerts
        doc_alerts = [a for a in data["alerts"] if a["type"] == "document_expiry"]
        
        if doc_alerts:
            alert = doc_alerts[0]
            assert alert["active"] == True
            assert "document_name" in alert or "expira" in alert["message"]
            assert alert["priority"] in ["high", "critical"]
            print(f"✓ Document expiry alert found: {alert['message']}")
        else:
            print("✓ No document expiry alerts (no documents expiring soon)")
    
    def test_process_not_found(self, admin_token):
        """Test 404 for non-existent process"""
        response = requests.get(
            f"{BASE_URL}/api/processes/non-existent-id/alerts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        print("✓ 404 returned for non-existent process")


class TestMarkNotificationRead:
    """Test marking notifications as read - PUT /api/alerts/notifications/{id}/read"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        return response.json()["access_token"]
    
    def test_mark_notification_read(self, admin_token):
        """Test marking a notification as read"""
        # First get notifications
        response = requests.get(
            f"{BASE_URL}/api/alerts/notifications",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        if not data["notifications"]:
            pytest.skip("No notifications to test")
        
        # Get first unread notification
        unread = [n for n in data["notifications"] if not n["read"]]
        if not unread:
            print("✓ All notifications already read")
            return
        
        notification_id = unread[0]["id"]
        
        # Mark as read
        response = requests.put(
            f"{BASE_URL}/api/alerts/notifications/{notification_id}/read",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        
        print(f"✓ Notification {notification_id[:8]}... marked as read")
    
    def test_mark_nonexistent_notification(self, admin_token):
        """Test 404 for non-existent notification"""
        response = requests.put(
            f"{BASE_URL}/api/alerts/notifications/non-existent-id/read",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        print("✓ 404 returned for non-existent notification")


class TestAlertsRoutes:
    """Test additional alerts routes"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def process_id(self, admin_token):
        response = requests.get(
            f"{BASE_URL}/api/processes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        processes = response.json()
        return processes[0]["id"] if processes else None
    
    def test_alerts_process_endpoint(self, admin_token, process_id):
        """Test GET /api/alerts/process/{process_id}"""
        if not process_id:
            pytest.skip("No process found")
        
        response = requests.get(
            f"{BASE_URL}/api/alerts/process/{process_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "process_id" in data
        assert "alerts" in data
        print(f"✓ Alerts endpoint working: {data.get('total_alerts', len(data.get('alerts', [])))} alerts")
    
    def test_age_check_endpoint(self, admin_token, process_id):
        """Test GET /api/alerts/age-check/{process_id}"""
        if not process_id:
            pytest.skip("No process found")
        
        response = requests.get(
            f"{BASE_URL}/api/alerts/age-check/{process_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "type" in data
        assert data["type"] == "age_under_35"
        assert "active" in data
        print(f"✓ Age check endpoint working: active={data['active']}")
    
    def test_pre_approval_endpoint(self, admin_token, process_id):
        """Test GET /api/alerts/pre-approval/{process_id}"""
        if not process_id:
            pytest.skip("No process found")
        
        response = requests.get(
            f"{BASE_URL}/api/alerts/pre-approval/{process_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "type" in data
        assert data["type"] == "pre_approval_countdown"
        assert "active" in data
        print(f"✓ Pre-approval endpoint working: active={data['active']}")
    
    def test_documents_endpoint(self, admin_token, process_id):
        """Test GET /api/alerts/documents/{process_id}"""
        if not process_id:
            pytest.skip("No process found")
        
        response = requests.get(
            f"{BASE_URL}/api/alerts/documents/{process_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "process_id" in data
        assert "alerts" in data
        assert "total" in data
        print(f"✓ Documents alerts endpoint working: {data['total']} document alerts")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
