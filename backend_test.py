#!/usr/bin/env python3
"""
Backend API Testing for Portuguese Real Estate Credit Registration System
Tests all authentication, user management, process management, and deadline APIs
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class CreditoIMOTester:
    def __init__(self, base_url="https://client-register-sys.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.client_token = None
        self.consultor_token = None
        self.mediador_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_users = []
        self.created_processes = []
        self.created_deadlines = []

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

            try:
                response_data = response.json() if response.text else {}
            except:
                response_data = {"raw_response": response.text}

            return success, response_data

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}", "ERROR")
            return False, {}

    def test_health_check(self) -> bool:
        """Test health endpoint"""
        success, _ = self.run_test("Health Check", "GET", "health", 200)
        return success

    def test_admin_login(self) -> bool:
        """Test admin login"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@sistema.pt", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            self.log(f"✅ Admin token obtained")
            return True
        return False

    def test_client_registration(self) -> bool:
        """Test client registration"""
        client_data = {
            "email": f"cliente_test_{datetime.now().strftime('%H%M%S')}@test.pt",
            "password": "TestPass123!",
            "name": "Cliente Teste",
            "phone": "912345678"
        }
        
        success, response = self.run_test(
            "Client Registration",
            "POST",
            "auth/register",
            200,
            data=client_data
        )
        
        if success and 'access_token' in response:
            self.client_token = response['access_token']
            self.created_users.append({
                "id": response['user']['id'],
                "email": client_data['email'],
                "role": "cliente"
            })
            self.log(f"✅ Client registered and token obtained")
            return True
        return False

    def test_create_users_by_admin(self) -> bool:
        """Test creating consultor and mediador by admin"""
        if not self.admin_token:
            self.log("❌ Admin token required", "ERROR")
            return False

        # Create Consultor
        consultor_data = {
            "email": f"consultor_test_{datetime.now().strftime('%H%M%S')}@test.pt",
            "password": "TestPass123!",
            "name": "Consultor Teste",
            "phone": "913456789",
            "role": "consultor"
        }
        
        success, response = self.run_test(
            "Create Consultor",
            "POST",
            "users",
            200,
            data=consultor_data,
            token=self.admin_token
        )
        
        if success:
            self.created_users.append({
                "id": response['id'],
                "email": consultor_data['email'],
                "role": "consultor"
            })
            
            # Login as consultor to get token
            login_success, login_response = self.run_test(
                "Consultor Login",
                "POST",
                "auth/login",
                200,
                data={"email": consultor_data['email'], "password": consultor_data['password']}
            )
            if login_success:
                self.consultor_token = login_response['access_token']

        # Create Mediador
        mediador_data = {
            "email": f"mediador_test_{datetime.now().strftime('%H%M%S')}@test.pt",
            "password": "TestPass123!",
            "name": "Mediador Teste",
            "phone": "914567890",
            "role": "mediador"
        }
        
        success2, response2 = self.run_test(
            "Create Mediador",
            "POST",
            "users",
            200,
            data=mediador_data,
            token=self.admin_token
        )
        
        if success2:
            self.created_users.append({
                "id": response2['id'],
                "email": mediador_data['email'],
                "role": "mediador"
            })
            
            # Login as mediador to get token
            login_success2, login_response2 = self.run_test(
                "Mediador Login",
                "POST",
                "auth/login",
                200,
                data={"email": mediador_data['email'], "password": mediador_data['password']}
            )
            if login_success2:
                self.mediador_token = login_response2['access_token']

        return success and success2

    def test_create_process(self) -> bool:
        """Test creating a process as client"""
        if not self.client_token:
            self.log("❌ Client token required", "ERROR")
            return False

        process_data = {
            "process_type": "ambos",
            "personal_data": {
                "nif": "123456789",
                "address": "Rua Teste, 123, 1000-001 Lisboa",
                "birth_date": "1990-01-01",
                "marital_status": "solteiro",
                "nationality": "Portuguesa"
            },
            "financial_data": {
                "monthly_income": 2500.0,
                "other_income": 500.0,
                "monthly_expenses": 1200.0,
                "employment_type": "efetivo",
                "employer_name": "Empresa Teste",
                "employment_duration": "3 anos",
                "has_debts": False,
                "debt_amount": None
            }
        }
        
        success, response = self.run_test(
            "Create Process",
            "POST",
            "processes",
            200,
            data=process_data,
            token=self.client_token
        )
        
        if success and 'id' in response:
            self.created_processes.append({
                "id": response['id'],
                "client_id": response['client_id'],
                "status": response['status']
            })
            self.log(f"✅ Process created with ID: {response['id'][:8]}...")
            return True
        return False

    def test_get_processes(self) -> bool:
        """Test getting processes for different user types"""
        results = []
        
        # Test as client
        if self.client_token:
            success, _ = self.run_test(
                "Get Processes (Client)",
                "GET",
                "processes",
                200,
                token=self.client_token
            )
            results.append(success)

        # Test as admin
        if self.admin_token:
            success, _ = self.run_test(
                "Get Processes (Admin)",
                "GET",
                "processes",
                200,
                token=self.admin_token
            )
            results.append(success)

        return all(results)

    def test_update_process_by_consultor(self) -> bool:
        """Test updating process by consultor"""
        if not self.consultor_token or not self.created_processes:
            self.log("❌ Consultor token and process required", "ERROR")
            return False

        process_id = self.created_processes[0]['id']
        update_data = {
            "real_estate_data": {
                "property_type": "apartamento",
                "property_zone": "Lisboa Centro",
                "desired_area": 80.0,
                "max_budget": 300000.0,
                "property_purpose": "habitacao_propria",
                "notes": "Preferência por zona histórica"
            },
            "status": "em_analise"
        }
        
        success, response = self.run_test(
            "Update Process (Consultor)",
            "PUT",
            f"processes/{process_id}",
            200,
            data=update_data,
            token=self.consultor_token
        )
        
        if success:
            # Update our tracking
            for process in self.created_processes:
                if process['id'] == process_id:
                    process['status'] = 'em_analise'
                    break
        
        return success

    def test_update_process_by_mediador(self) -> bool:
        """Test updating process status by mediador"""
        if not self.mediador_token or not self.created_processes:
            self.log("❌ Mediador token and process required", "ERROR")
            return False

        process_id = self.created_processes[0]['id']
        
        # First, change status to authorization
        update_data = {
            "status": "autorizacao_bancaria"
        }
        
        success, response = self.run_test(
            "Update Process Status (Mediador)",
            "PUT",
            f"processes/{process_id}",
            200,
            data=update_data,
            token=self.mediador_token
        )
        
        if success:
            # Update our tracking
            for process in self.created_processes:
                if process['id'] == process_id:
                    process['status'] = 'autorizacao_bancaria'
                    break
            
            # Now test adding credit data
            credit_update = {
                "credit_data": {
                    "requested_amount": 250000.0,
                    "loan_term_years": 30,
                    "interest_rate": 3.5,
                    "monthly_payment": 1123.0,
                    "bank_name": "Banco Teste",
                    "bank_approval_date": "2024-01-15",
                    "bank_approval_notes": "Aprovado com condições standard"
                }
            }
            
            success2, _ = self.run_test(
                "Add Credit Data (Mediador)",
                "PUT",
                f"processes/{process_id}",
                200,
                data=credit_update,
                token=self.mediador_token
            )
            
            return success2
        
        return success

    def test_create_deadline(self) -> bool:
        """Test creating deadline"""
        if not self.consultor_token or not self.created_processes:
            self.log("❌ Consultor token and process required", "ERROR")
            return False

        process_id = self.created_processes[0]['id']
        deadline_data = {
            "process_id": process_id,
            "title": "Entregar documentos bancários",
            "description": "Cliente deve entregar comprovativos de rendimento",
            "due_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "priority": "high"
        }
        
        success, response = self.run_test(
            "Create Deadline",
            "POST",
            "deadlines",
            200,
            data=deadline_data,
            token=self.consultor_token
        )
        
        if success and 'id' in response:
            self.created_deadlines.append({
                "id": response['id'],
                "process_id": process_id
            })
            return True
        return False

    def test_get_deadlines(self) -> bool:
        """Test getting deadlines"""
        if not self.client_token:
            return False

        success, _ = self.run_test(
            "Get Deadlines",
            "GET",
            "deadlines",
            200,
            token=self.client_token
        )
        return success

    def test_update_deadline(self) -> bool:
        """Test updating deadline (mark as completed)"""
        if not self.consultor_token or not self.created_deadlines:
            self.log("❌ Consultor token and deadline required", "ERROR")
            return False

        deadline_id = self.created_deadlines[0]['id']
        update_data = {
            "completed": True
        }
        
        success, _ = self.run_test(
            "Update Deadline",
            "PUT",
            f"deadlines/{deadline_id}",
            200,
            data=update_data,
            token=self.consultor_token
        )
        return success

    def test_get_stats(self) -> bool:
        """Test getting statistics"""
        if not self.admin_token:
            return False

        success, response = self.run_test(
            "Get Stats",
            "GET",
            "stats",
            200,
            token=self.admin_token
        )
        
        if success:
            self.log(f"✅ Stats retrieved: {json.dumps(response, indent=2)}")
        return success

    def test_get_users(self) -> bool:
        """Test getting users list (admin only)"""
        if not self.admin_token:
            return False

        success, response = self.run_test(
            "Get Users",
            "GET",
            "users",
            200,
            token=self.admin_token
        )
        
        if success:
            self.log(f"✅ Found {len(response)} users")
        return success

    def test_search_filters(self) -> bool:
        """Test search and filter functionality"""
        if not self.admin_token:
            return False

        # Test role filter
        success, response = self.run_test(
            "Filter Users by Role",
            "GET",
            "users?role=cliente",
            200,
            token=self.admin_token
        )
        return success

    def cleanup(self):
        """Clean up created test data"""
        self.log("🧹 Cleaning up test data...")
        
        # Delete created deadlines
        for deadline in self.created_deadlines:
            if self.consultor_token:
                self.run_test(
                    f"Delete Deadline {deadline['id'][:8]}...",
                    "DELETE",
                    f"deadlines/{deadline['id']}",
                    200,
                    token=self.consultor_token
                )

        # Delete created users (except the client who created processes)
        for user in self.created_users:
            if user['role'] != 'cliente' and self.admin_token:
                self.run_test(
                    f"Delete User {user['email']}",
                    "DELETE",
                    f"users/{user['id']}",
                    200,
                    token=self.admin_token
                )

    def run_all_tests(self) -> int:
        """Run all tests in sequence"""
        self.log("🚀 Starting CreditoIMO Backend API Tests")
        self.log(f"🌐 Testing against: {self.base_url}")
        
        # Core functionality tests
        tests = [
            ("Health Check", self.test_health_check),
            ("Admin Login", self.test_admin_login),
            ("Client Registration", self.test_client_registration),
            ("Create Users by Admin", self.test_create_users_by_admin),
            ("Create Process", self.test_create_process),
            ("Get Processes", self.test_get_processes),
            ("Update Process by Consultor", self.test_update_process_by_consultor),
            ("Update Process by Mediador", self.test_update_process_by_mediador),
            ("Create Deadline", self.test_create_deadline),
            ("Get Deadlines", self.test_get_deadlines),
            ("Update Deadline", self.test_update_deadline),
            ("Get Statistics", self.test_get_stats),
            ("Get Users", self.test_get_users),
            ("Search Filters", self.test_search_filters),
        ]

        failed_tests = []
        
        for test_name, test_func in tests:
            try:
                if not test_func():
                    failed_tests.append(test_name)
            except Exception as e:
                self.log(f"❌ {test_name} - Exception: {str(e)}", "ERROR")
                failed_tests.append(test_name)

        # Cleanup
        self.cleanup()

        # Results
        self.log("\n" + "="*60)
        self.log(f"📊 TEST RESULTS")
        self.log(f"   Tests Run: {self.tests_run}")
        self.log(f"   Tests Passed: {self.tests_passed}")
        self.log(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        self.log(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if failed_tests:
            self.log(f"\n❌ Failed Tests:")
            for test in failed_tests:
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