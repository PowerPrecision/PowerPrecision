#!/usr/bin/env python3
"""
Additional specific tests for JWT tokens and role-based access
"""

import requests
import json
from datetime import datetime

class AdditionalTester:
    def __init__(self, base_url="https://real-estate-crm-8.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def test_jwt_token_validation(self):
        """Test JWT token validation"""
        self.log("🔐 Testing JWT Token Validation")
        
        # First login as admin
        response = requests.post(f"{self.base_url}/api/auth/login", 
                               json={"email": "admin@sistema.pt", "password": "admin2026"})
        if response.status_code == 200:
            self.admin_token = response.json()['access_token']
            self.log("✅ Admin login successful")
            
            # Test /me endpoint with valid token
            me_response = requests.get(f"{self.base_url}/api/auth/me", 
                                     headers={'Authorization': f'Bearer {self.admin_token}'})
            if me_response.status_code == 200:
                user_data = me_response.json()
                self.log(f"✅ JWT token valid - User: {user_data.get('name')} ({user_data.get('role')})")
            else:
                self.log("❌ JWT token validation failed", "ERROR")
            
            # Test with invalid token
            invalid_response = requests.get(f"{self.base_url}/api/auth/me", 
                                          headers={'Authorization': 'Bearer invalid_token'})
            if invalid_response.status_code == 401:
                self.log("✅ Invalid token correctly rejected")
            else:
                self.log("❌ Invalid token not rejected", "ERROR")
        else:
            self.log("❌ Admin login failed", "ERROR")

    def test_role_permissions(self):
        """Test detailed role-based permissions"""
        self.log("👥 Testing Role-Based Access Control")
        
        # Test different user roles
        test_users = [
            ("pedro@powerealestate.pt", "power2026", "CEO"),
            ("tiago@powerealestate.pt", "power2026", "CONSULTOR"),
            ("estacio@precisioncredito.pt", "power2026", "INTERMEDIARIO")
        ]
        
        for email, password, expected_role in test_users:
            # Login
            login_response = requests.post(f"{self.base_url}/api/auth/login", 
                                         json={"email": email, "password": password})
            if login_response.status_code == 200:
                token = login_response.json()['access_token']
                user_data = login_response.json()['user']
                
                self.log(f"✅ {expected_role} login: {user_data.get('name')}")
                
                # Test access to processes
                processes_response = requests.get(f"{self.base_url}/api/processes", 
                                                headers={'Authorization': f'Bearer {token}'})
                if processes_response.status_code == 200:
                    processes = processes_response.json()
                    self.log(f"   Can access {len(processes)} processes")
                
                # Test access to stats
                stats_response = requests.get(f"{self.base_url}/api/stats", 
                                            headers={'Authorization': f'Bearer {token}'})
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    self.log(f"   Can access statistics: {stats.get('total_processes', 0)} total processes")
                
                # Test access to users (should fail for non-admin)
                users_response = requests.get(f"{self.base_url}/api/users", 
                                            headers={'Authorization': f'Bearer {token}'})
                if expected_role == "CEO":
                    if users_response.status_code == 403:
                        self.log(f"   ✅ {expected_role} correctly denied access to users list")
                    else:
                        self.log(f"   ⚠️ {expected_role} has unexpected access to users list")
                else:
                    if users_response.status_code == 403:
                        self.log(f"   ✅ {expected_role} correctly denied access to users list")
                    else:
                        self.log(f"   ⚠️ {expected_role} has unexpected access to users list")

    def test_process_data_completeness(self):
        """Test process data completeness"""
        self.log("📋 Testing Process Data Completeness")
        
        if not self.admin_token:
            return
        
        # Get a sample of processes
        response = requests.get(f"{self.base_url}/api/processes", 
                              headers={'Authorization': f'Bearer {self.admin_token}'})
        if response.status_code == 200:
            processes = response.json()
            
            # Check data completeness
            complete_processes = 0
            incomplete_processes = 0
            
            for process in processes[:10]:  # Check first 10
                required_fields = ['client_name', 'client_email', 'status', 'created_at']
                missing_fields = [field for field in required_fields if not process.get(field)]
                
                if not missing_fields:
                    complete_processes += 1
                else:
                    incomplete_processes += 1
            
            self.log(f"✅ Process data check (sample of 10):")
            self.log(f"   Complete processes: {complete_processes}")
            self.log(f"   Incomplete processes: {incomplete_processes}")

    def test_calendar_events_details(self):
        """Test calendar events with user assignments"""
        self.log("📅 Testing Calendar Events Details")
        
        if not self.admin_token:
            return
        
        # Get calendar deadlines
        response = requests.get(f"{self.base_url}/api/deadlines/calendar", 
                              headers={'Authorization': f'Bearer {self.admin_token}'})
        if response.status_code == 200:
            events = response.json()
            
            assigned_events = 0
            unassigned_events = 0
            
            for event in events:
                if event.get('assigned_user_id') or event.get('assigned_consultor_id') or event.get('assigned_mediador_id'):
                    assigned_events += 1
                else:
                    unassigned_events += 1
            
            self.log(f"✅ Calendar events analysis:")
            self.log(f"   Total events: {len(events)}")
            self.log(f"   Assigned to users: {assigned_events}")
            self.log(f"   Unassigned: {unassigned_events}")

    def run_all_tests(self):
        """Run all additional tests"""
        self.log("🚀 Starting Additional CreditoIMO Tests")
        
        self.test_jwt_token_validation()
        self.test_role_permissions()
        self.test_process_data_completeness()
        self.test_calendar_events_details()
        
        self.log("✅ Additional tests completed")

if __name__ == "__main__":
    tester = AdditionalTester()
    tester.run_all_tests()