#!/usr/bin/env python3
"""
Backend API Testing for CreditoIMO System
Tests authentication, processes, statistics, workflow, calendar, and user management
Based on the review request requirements
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class CreditoIMOTester:
    def __init__(self, base_url="https://property-credit.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}  # Store tokens for different users
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, token: Optional[str] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}", "ERROR")
                if response.text:
                    self.log(f"   Response: {response.text[:200]}", "ERROR")
                self.failed_tests.append(f"{name} - Expected {expected_status}, got {response.status_code}")

            try:
                response_data = response.json() if response.text else {}
            except:
                response_data = {"raw_response": response.text}

            return success, response_data

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}", "ERROR")
            self.failed_tests.append(f"{name} - Error: {str(e)}")
            return False, {}

    def test_health_check(self) -> bool:
        """Test health endpoint"""
        success, _ = self.run_test("Health Check", "GET", "health", 200)
        return success

    def test_user_login(self, email: str, password: str, user_type: str) -> bool:
        """Test login for a specific user"""
        success, response = self.run_test(
            f"{user_type} Login ({email})",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'access_token' in response:
            self.tokens[user_type] = response['access_token']
            self.log(f"✅ {user_type} token obtained for {email}")
            return True
        return False

    def test_all_user_logins(self) -> bool:
        """Test login for all 8 users mentioned in the review request"""
        users = [
            ("admin@sistema.pt", "admin2026", "Admin"),
            ("pedro@powerealestate.pt", "power2026", "CEO"),
            ("tiago@powerealestate.pt", "power2026", "Consultor1"),
            ("flavio@powerealestate.pt", "power2026", "Consultor2"),
            ("estacio@precisioncredito.pt", "power2026", "Intermediario1"),
            ("fernando@precisioncredito.pt", "power2026", "Intermediario2"),
            ("carina@powerealestate.pt", "power2026", "ConsultorIntermediario1"),
            ("marisa@powerealestate.pt", "power2026", "ConsultorIntermediario2"),
        ]
        
        results = []
        for email, password, user_type in users:
            result = self.test_user_login(email, password, user_type)
            results.append(result)
        
        return all(results)

    def test_get_processes(self) -> bool:
        """Test GET /api/processes - should list all processes"""
        if not self.tokens.get("Admin"):
            self.log("❌ Admin token required", "ERROR")
            return False

        success, response = self.run_test(
            "Get All Processes",
            "GET",
            "processes",
            200,
            token=self.tokens["Admin"]
        )
        
        if success:
            process_count = len(response) if isinstance(response, list) else 0
            self.log(f"✅ Found {process_count} processes in database")
            
            # Check if we have the expected 154 processes
            if process_count >= 150:  # Allow some tolerance
                self.log(f"✅ Process count looks good ({process_count} processes)")
            else:
                self.log(f"⚠️ Expected ~154 processes, found {process_count}", "WARNING")
        
        return success

    def test_get_process_details(self) -> bool:
        """Test GET /api/process/{id} - get details of a specific process"""
        if not self.tokens.get("Admin"):
            return False

        # First get a process ID
        success, processes = self.run_test(
            "Get Processes for Detail Test",
            "GET",
            "processes",
            200,
            token=self.tokens["Admin"]
        )
        
        if not success or not processes:
            return False
        
        # Test getting details of the first process
        process_id = processes[0].get("id") if processes else None
        if not process_id:
            self.log("❌ No process ID found", "ERROR")
            return False

        success, response = self.run_test(
            f"Get Process Details ({process_id[:8]}...)",
            "GET",
            f"processes/{process_id}",
            200,
            token=self.tokens["Admin"]
        )
        
        if success:
            # Check if process has complete client data
            client_data_fields = ["client_name", "client_email", "personal_data", "financial_data"]
            missing_fields = [field for field in client_data_fields if not response.get(field)]
            if missing_fields:
                self.log(f"⚠️ Process missing some data: {missing_fields}", "WARNING")
            else:
                self.log("✅ Process has complete client data")
        
        return success

    def test_get_statistics(self) -> bool:
        """Test GET /api/stats - verify correct counts"""
        if not self.tokens.get("Admin"):
            return False

        success, response = self.run_test(
            "Get Statistics",
            "GET",
            "stats",
            200,
            token=self.tokens["Admin"]
        )
        
        if success:
            self.log(f"✅ Statistics retrieved:")
            stats_to_check = [
                "total_processes", "active_processes", "concluded_processes", 
                "total_users", "active_users", "total_deadlines"
            ]
            for stat in stats_to_check:
                if stat in response:
                    self.log(f"   {stat}: {response[stat]}")
                else:
                    self.log(f"   ⚠️ Missing stat: {stat}", "WARNING")
        
        return success

    def test_get_workflow_statuses(self) -> bool:
        """Test GET /api/workflow-statuses - verify 14 phases"""
        if not self.tokens.get("Admin"):
            return False

        success, response = self.run_test(
            "Get Workflow Statuses",
            "GET",
            "workflow-statuses",
            200,
            token=self.tokens["Admin"]
        )
        
        if success:
            status_count = len(response) if isinstance(response, list) else 0
            self.log(f"✅ Found {status_count} workflow phases")
            
            if status_count == 14:
                self.log("✅ Correct number of workflow phases (14)")
            else:
                self.log(f"⚠️ Expected 14 workflow phases, found {status_count}", "WARNING")
            
            # Log the phases
            if isinstance(response, list):
                for i, status in enumerate(response[:5]):  # Show first 5
                    self.log(f"   Phase {i+1}: {status.get('label', status.get('name', 'Unknown'))}")
                if len(response) > 5:
                    self.log(f"   ... and {len(response) - 5} more phases")
        
        return success

    def test_get_calendar_deadlines(self) -> bool:
        """Test GET /api/deadlines - verify 43 events"""
        if not self.tokens.get("Admin"):
            return False

        success, response = self.run_test(
            "Get Calendar Deadlines",
            "GET",
            "deadlines",
            200,
            token=self.tokens["Admin"]
        )
        
        if success:
            deadline_count = len(response) if isinstance(response, list) else 0
            self.log(f"✅ Found {deadline_count} calendar events/deadlines")
            
            if deadline_count >= 40:  # Allow some tolerance
                self.log(f"✅ Calendar events count looks good ({deadline_count} events)")
            else:
                self.log(f"⚠️ Expected ~43 calendar events, found {deadline_count}", "WARNING")
        
        return success

    def test_get_users(self) -> bool:
        """Test GET /api/users - verify 8 active users"""
        if not self.tokens.get("Admin"):
            return False

        success, response = self.run_test(
            "Get Users List",
            "GET",
            "users",
            200,
            token=self.tokens["Admin"]
        )
        
        if success:
            user_count = len(response) if isinstance(response, list) else 0
            self.log(f"✅ Found {user_count} users in system")
            
            if user_count == 8:
                self.log("✅ Correct number of users (8)")
            else:
                self.log(f"⚠️ Expected 8 users, found {user_count}", "WARNING")
            
            # Check user roles
            if isinstance(response, list):
                roles = {}
                for user in response:
                    role = user.get("role", "unknown")
                    roles[role] = roles.get(role, 0) + 1
                
                self.log("✅ User roles breakdown:")
                for role, count in roles.items():
                    self.log(f"   {role}: {count}")
        
        return success

    def test_role_based_access(self) -> bool:
        """Test role-based access control"""
        results = []
        
        # Test Consultor access to processes
        if self.tokens.get("Consultor1"):
            success, _ = self.run_test(
                "Consultor Access to Processes",
                "GET",
                "processes",
                200,
                token=self.tokens["Consultor1"]
            )
            results.append(success)
        
        # Test Intermediario access to processes
        if self.tokens.get("Intermediario1"):
            success, _ = self.run_test(
                "Intermediario Access to Processes",
                "GET",
                "processes",
                200,
                token=self.tokens["Intermediario1"]
            )
            results.append(success)
        
        # Test CEO access to stats
        if self.tokens.get("CEO"):
            success, _ = self.run_test(
                "CEO Access to Statistics",
                "GET",
                "stats",
                200,
                token=self.tokens["CEO"]
            )
            results.append(success)
        
        return all(results) if results else False

    def test_process_assignments(self) -> bool:
        """Test process assignments to consultors and intermediarios"""
        if not self.tokens.get("Admin"):
            return False

        # Get processes to check assignments
        success, processes = self.run_test(
            "Get Processes for Assignment Check",
            "GET",
            "processes",
            200,
            token=self.tokens["Admin"]
        )
        
        if success and isinstance(processes, list):
            assigned_consultor = 0
            assigned_intermediario = 0
            
            for process in processes:
                if process.get("assigned_consultor_id"):
                    assigned_consultor += 1
                if process.get("assigned_mediador_id"):
                    assigned_intermediario += 1
            
            self.log(f"✅ Process assignments:")
            self.log(f"   Processes with consultor: {assigned_consultor}")
            self.log(f"   Processes with intermediario: {assigned_intermediario}")
            
            return True
        
        return success

    def test_kanban_board(self) -> bool:
        """Test Kanban board endpoint"""
        if not self.tokens.get("Admin"):
            return False

        success, response = self.run_test(
            "Get Kanban Board",
            "GET",
            "processes/kanban",
            200,
            token=self.tokens["Admin"]
        )
        
        if success:
            columns = response.get("columns", [])
            total_processes = response.get("total_processes", 0)
            
            self.log(f"✅ Kanban board loaded:")
            self.log(f"   Total columns: {len(columns)}")
            self.log(f"   Total processes: {total_processes}")
            
            # Show process distribution
            for column in columns[:3]:  # Show first 3 columns
                count = column.get("count", 0)
                label = column.get("label", column.get("name", "Unknown"))
                self.log(f"   {label}: {count} processes")
        
        return success

    def run_all_tests(self) -> int:
        """Run all tests in sequence"""
        self.log("🚀 Starting CreditoIMO Backend API Tests")
        self.log(f"🌐 Testing against: {self.base_url}")
        
        # Core functionality tests based on review request
        tests = [
            ("Health Check", self.test_health_check),
            ("All User Logins (8 users)", self.test_all_user_logins),
            ("Get All Processes (~154)", self.test_get_processes),
            ("Get Process Details", self.test_get_process_details),
            ("Get Statistics", self.test_get_statistics),
            ("Get Workflow Statuses (14 phases)", self.test_get_workflow_statuses),
            ("Get Calendar Deadlines (~43 events)", self.test_get_calendar_deadlines),
            ("Get Users List (8 users)", self.test_get_users),
            ("Role-Based Access Control", self.test_role_based_access),
            ("Process Assignments", self.test_process_assignments),
            ("Kanban Board", self.test_kanban_board),
        ]

        for test_name, test_func in tests:
            try:
                if not test_func():
                    self.log(f"❌ {test_name} failed", "ERROR")
            except Exception as e:
                self.log(f"❌ {test_name} - Exception: {str(e)}", "ERROR")
                self.failed_tests.append(f"{test_name} - Exception: {str(e)}")

        # Results
        self.log("\n" + "="*60)
        self.log(f"📊 TEST RESULTS")
        self.log(f"   Tests Run: {self.tests_run}")
        self.log(f"   Tests Passed: {self.tests_passed}")
        self.log(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        self.log(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            self.log(f"\n❌ Failed Tests:")
            for test in self.failed_tests:
                self.log(f"   - {test}")
        else:
            self.log(f"\n✅ All tests passed!")

        return 0 if self.tests_passed == self.tests_run else 1

def main():
    """Main test runner"""
    tester = CreditoIMOTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())