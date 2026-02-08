import requests
import sys
from datetime import datetime

class SpecificFeaturesTester:
    def __init__(self, base_url="https://crm-core-3.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.client_token = None
        self.consultor_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_process_id = None
        self.created_status_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.text else {}
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login_admin(self):
        """Test admin login with specific credentials"""
        success, response = self.run_test(
            "Admin Login (admin@sistema.pt / admin123)",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@sistema.pt", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✅ Admin logged in successfully")
            return True
        return False

    def test_login_client(self):
        """Test client login with specific credentials"""
        success, response = self.run_test(
            "Client Login (joao.silva@email.pt / cliente123)",
            "POST",
            "auth/login",
            200,
            data={"email": "joao.silva@email.pt", "password": "cliente123"}
        )
        if success and 'access_token' in response:
            self.client_token = response['access_token']
            print(f"   ✅ Client logged in successfully")
            return True
        return False

    def test_login_consultor(self):
        """Test consultor login"""
        success, response = self.run_test(
            "Consultor Login (consultor@sistema.pt / consultor123)",
            "POST",
            "auth/login",
            200,
            data={"email": "consultor@sistema.pt", "password": "consultor123"}
        )
        if success and 'access_token' in response:
            self.consultor_token = response['access_token']
            print(f"   ✅ Consultor logged in successfully")
            return True
        return False

    def test_get_workflow_statuses(self):
        """Test getting existing workflow statuses"""
        success, response = self.run_test(
            "Get Workflow Statuses (Admin Panel)",
            "GET",
            "workflow-statuses",
            200,
            token=self.admin_token
        )
        if success and isinstance(response, list):
            print(f"   ✅ Found {len(response)} workflow statuses:")
            for status in response:
                print(f"      - {status.get('name')}: {status.get('label')} (order: {status.get('order')})")
            return True
        return False

    def test_create_workflow_status(self):
        """Test admin creating new workflow status"""
        new_status = {
            "name": "teste_novo_estado",
            "label": "Teste Novo Estado",
            "order": 99,
            "color": "purple",
            "description": "Estado criado durante teste automatizado"
        }
        success, response = self.run_test(
            "Admin Create New Workflow Status",
            "POST",
            "workflow-statuses",
            200,
            data=new_status,
            token=self.admin_token
        )
        if success and 'id' in response:
            self.created_status_id = response['id']
            print(f"   ✅ Created status: {response.get('name')} - {response.get('label')}")
            return True
        return False

    def test_edit_workflow_status(self):
        """Test admin editing workflow status"""
        if not self.created_status_id:
            print("   ⚠️ No status to edit, skipping")
            return True
        
        update_data = {
            "label": "Teste Estado Editado",
            "description": "Estado editado durante teste automatizado",
            "color": "orange"
        }
        success, response = self.run_test(
            "Admin Edit Workflow Status",
            "PUT",
            f"workflow-statuses/{self.created_status_id}",
            200,
            data=update_data,
            token=self.admin_token
        )
        if success:
            print(f"   ✅ Updated status label to: {response.get('label')}")
            return True
        return False

    def test_client_create_process(self):
        """Test client creating new process"""
        process_data = {
            "process_type": "ambos",
            "personal_data": {
                "nif": "123456789",
                "address": "Rua de Teste, 123, Lisboa",
                "birth_date": "1990-01-01",
                "marital_status": "solteiro",
                "nationality": "Portuguesa"
            },
            "financial_data": {
                "monthly_income": 2500.0,
                "monthly_expenses": 1200.0,
                "employment_type": "efetivo",
                "employer_name": "Empresa Teste"
            }
        }
        success, response = self.run_test(
            "Client Create New Process",
            "POST",
            "processes",
            200,
            data=process_data,
            token=self.client_token
        )
        if success and 'id' in response:
            self.test_process_id = response['id']
            print(f"   ✅ Process created with ID: {self.test_process_id[:8]}...")
            return True
        return False

    def test_verify_process_history(self):
        """Test that process creation is recorded in history"""
        if not self.test_process_id:
            return False
        
        success, response = self.run_test(
            "Verify Process Creation in History",
            "GET",
            f"history?process_id={self.test_process_id}",
            200,
            token=self.client_token
        )
        if success and isinstance(response, list):
            creation_entries = [h for h in response if "Criou processo" in h.get('action', '')]
            if creation_entries:
                print(f"   ✅ Process creation recorded in history")
                print(f"      Action: {creation_entries[0].get('action')}")
                print(f"      User: {creation_entries[0].get('user_name')}")
                return True
            else:
                print(f"   ❌ Process creation not found in history")
                return False
        return False

    def test_add_comment_activity(self):
        """Test adding comment/activity to process"""
        if not self.test_process_id:
            return False
        
        comment_data = {
            "process_id": self.test_process_id,
            "comment": "Este é um comentário de teste adicionado pelo cliente João Silva."
        }
        success, response = self.run_test(
            "Add Comment/Activity to Process",
            "POST",
            "activities",
            200,
            data=comment_data,
            token=self.client_token
        )
        if success:
            print(f"   ✅ Comment added: {response.get('comment')[:50]}...")
            return True
        return False

    def test_verify_comment_in_activities(self):
        """Test that comment appears in activities list"""
        if not self.test_process_id:
            return False
        
        success, response = self.run_test(
            "Verify Comment in Activities List",
            "GET",
            f"activities?process_id={self.test_process_id}",
            200,
            token=self.client_token
        )
        if success and isinstance(response, list):
            if len(response) > 0:
                print(f"   ✅ Found {len(response)} activities:")
                for activity in response:
                    print(f"      - {activity.get('user_name')} ({activity.get('user_role')}): {activity.get('comment')[:30]}...")
                return True
            else:
                print(f"   ❌ No activities found")
                return False
        return False

    def test_consultor_change_status(self):
        """Test consultor/mediator changing process state"""
        if not self.test_process_id:
            return False
        
        update_data = {"status": "em_analise"}
        success, response = self.run_test(
            "Consultor Change Process Status",
            "PUT",
            f"processes/{self.test_process_id}",
            200,
            data=update_data,
            token=self.consultor_token
        )
        if success:
            print(f"   ✅ Status changed to: {response.get('status')}")
            return True
        return False

    def test_verify_status_change_history(self):
        """Test that status change is recorded in history"""
        if not self.test_process_id:
            return False
        
        success, response = self.run_test(
            "Verify Status Change in History",
            "GET",
            f"history?process_id={self.test_process_id}",
            200,
            token=self.client_token
        )
        if success and isinstance(response, list):
            status_changes = [h for h in response if "Alterou estado" in h.get('action', '')]
            if status_changes:
                print(f"   ✅ Status change recorded in history")
                for change in status_changes:
                    print(f"      {change.get('action')} by {change.get('user_name')}: {change.get('old_value')} → {change.get('new_value')}")
                return True
            else:
                print(f"   ❌ Status change not found in history")
                return False
        return False

    def test_onedrive_not_configured(self):
        """Test OneDrive shows not configured message"""
        success, response = self.run_test(
            "OneDrive Status (Should be Not Configured)",
            "GET",
            "onedrive/status",
            200,
            token=self.admin_token
        )
        if success:
            configured = response.get('configured', False)
            if not configured:
                print(f"   ✅ OneDrive correctly shows as not configured")
                return True
            else:
                print(f"   ❌ OneDrive shows as configured when it shouldn't be")
                return False
        return False

    def cleanup(self):
        """Clean up created test data"""
        print(f"\n🧹 Cleaning up test data...")
        
        # Delete created workflow status
        if self.created_status_id and self.admin_token:
            self.run_test(
                "Delete Created Workflow Status",
                "DELETE",
                f"workflow-statuses/{self.created_status_id}",
                200,
                token=self.admin_token
            )

def main():
    print("🚀 Testing Specific Portuguese Real Estate System Features")
    print("=" * 60)
    
    tester = SpecificFeaturesTester()
    
    # Test sequence matching requirements
    tests = [
        ("Login as Admin", tester.test_login_admin),
        ("Verify Workflow States Exist", tester.test_get_workflow_statuses),
        ("Admin Create New Workflow State", tester.test_create_workflow_status),
        ("Admin Edit Workflow State", tester.test_edit_workflow_status),
        ("Login as Client", tester.test_login_client),
        ("Login as Consultor", tester.test_login_consultor),
        ("Client Create New Process", tester.test_client_create_process),
        ("Verify History Records Process Creation", tester.test_verify_process_history),
        ("Add Comment/Activity to Process", tester.test_add_comment_activity),
        ("Verify Comment in Activities List", tester.test_verify_comment_in_activities),
        ("Consultor Change Process Status", tester.test_consultor_change_status),
        ("Verify History Records Status Change", tester.test_verify_status_change_history),
        ("OneDrive Shows Not Configured", tester.test_onedrive_not_configured),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} - Exception: {str(e)}")
            failed_tests.append(test_name)
    
    # Cleanup
    tester.cleanup()
    
    # Print results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if failed_tests:
        print(f"\n❌ Failed tests ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"   - {test}")
    else:
        print("\n🎉 All specific features working correctly!")
    
    return 0 if len(failed_tests) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())