"""
Iteration 44: Document Categorization and Search Feature Tests
================================================================
Tests for new document categorization with AI endpoints:
- GET /api/documents/metadata/{process_id}
- POST /api/documents/search
- GET /api/documents/categories
- POST /api/documents/categorize/{process_id}
- POST /api/documents/categorize-all/{process_id}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "flaviosilva@powerealestate.pt"
TEST_PASSWORD = "flavio123"
TEST_PROCESS_ID = "9f573b70-538f-4c4b-87e7-71bfa12e1e8a"


class TestDocumentCategorizationAuth:
    """Test authentication for document endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_document_metadata_requires_auth(self):
        """Test that document metadata endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/documents/metadata/{TEST_PROCESS_ID}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Document metadata requires authentication")
    
    def test_document_search_requires_auth(self):
        """Test that document search endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/documents/search",
            json={"query": "test", "limit": 20}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Document search requires authentication")
    
    def test_categories_requires_auth(self):
        """Test that categories endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/documents/categories")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Categories endpoint requires authentication")


class TestDocumentMetadata:
    """Test GET /api/documents/metadata/{process_id}"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_metadata_success(self):
        """Test successful retrieval of document metadata"""
        response = self.session.get(f"{BASE_URL}/api/documents/metadata/{TEST_PROCESS_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "process_id" in data, "Response should contain process_id"
        assert data["process_id"] == TEST_PROCESS_ID
        assert "client_name" in data, "Response should contain client_name"
        assert "documents" in data, "Response should contain documents list"
        assert "total" in data, "Response should contain total count"
        assert "categorized" in data, "Response should contain categorized count"
        assert "categories" in data, "Response should contain categories list"
        assert isinstance(data["documents"], list)
        assert isinstance(data["categories"], list)
        print(f"✅ Got metadata for process {TEST_PROCESS_ID}: {data['total']} documents, {data['categorized']} categorized")
    
    def test_get_metadata_invalid_process(self):
        """Test metadata retrieval with invalid process ID"""
        response = self.session.get(f"{BASE_URL}/api/documents/metadata/invalid-process-id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        print("✅ Invalid process ID returns 404")


class TestDocumentSearch:
    """Test POST /api/documents/search"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_search_success(self):
        """Test successful document search"""
        response = self.session.post(f"{BASE_URL}/api/documents/search", json={
            "query": "contrato",
            "process_id": TEST_PROCESS_ID,
            "limit": 20
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "query" in data, "Response should contain query"
        assert data["query"] == "contrato"
        assert "total_results" in data, "Response should contain total_results"
        assert "results" in data, "Response should contain results list"
        assert isinstance(data["results"], list)
        print(f"✅ Search for 'contrato' returned {data['total_results']} results")
    
    def test_search_minimum_query_length(self):
        """Test search with minimum 2 character query"""
        response = self.session.post(f"{BASE_URL}/api/documents/search", json={
            "query": "cc",
            "limit": 20
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["query"] == "cc"
        print("✅ Search accepts 2 character queries")
    
    def test_search_empty_query_validation(self):
        """Test search with empty query returns validation error"""
        response = self.session.post(f"{BASE_URL}/api/documents/search", json={
            "query": "",
            "limit": 20
        })
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        # Check for validation error about string length
        error_found = any(
            err.get("type") == "string_too_short" 
            for err in data["detail"]
        )
        assert error_found, "Should have string_too_short validation error"
        print("✅ Empty query returns 422 validation error")
    
    def test_search_single_char_query_validation(self):
        """Test search with single character query returns validation error"""
        response = self.session.post(f"{BASE_URL}/api/documents/search", json={
            "query": "a",
            "limit": 20
        })
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✅ Single character query returns 422 validation error")
    
    def test_search_with_categories_filter(self):
        """Test search with category filter"""
        response = self.session.post(f"{BASE_URL}/api/documents/search", json={
            "query": "documento",
            "categories": ["Identificação", "Rendimentos"],
            "limit": 20
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "results" in data
        print("✅ Search with category filter works")
    
    def test_search_without_process_id(self):
        """Test global search without process_id filter"""
        response = self.session.post(f"{BASE_URL}/api/documents/search", json={
            "query": "teste",
            "limit": 20
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "results" in data
        print("✅ Global search without process_id works")


class TestDocumentCategories:
    """Test GET /api/documents/categories"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_all_categories(self):
        """Test retrieval of all categories"""
        response = self.session.get(f"{BASE_URL}/api/documents/categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "categories" in data, "Response should contain categories list"
        assert "total_categories" in data, "Response should contain total_categories count"
        assert isinstance(data["categories"], list)
        
        # Each category should have name and count
        for cat in data["categories"]:
            assert "name" in cat, "Category should have name"
            assert "count" in cat, "Category should have count"
        
        print(f"✅ Got {data['total_categories']} categories")
    
    def test_get_categories_by_process(self):
        """Test retrieval of categories filtered by process"""
        response = self.session.get(
            f"{BASE_URL}/api/documents/categories",
            params={"process_id": TEST_PROCESS_ID}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "categories" in data
        assert "total_categories" in data
        print(f"✅ Got {data['total_categories']} categories for process {TEST_PROCESS_ID}")


class TestDocumentCategorization:
    """Test POST /api/documents/categorize/{process_id}"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        
        # Login
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_categorize_missing_params(self):
        """Test categorization with missing parameters"""
        response = self.session.post(
            f"{BASE_URL}/api/documents/categorize/{TEST_PROCESS_ID}"
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        # Check that s3_path and filename are required
        missing_fields = [err.get("loc", [])[-1] for err in data["detail"] if err.get("type") == "missing"]
        assert "s3_path" in missing_fields or "filename" in missing_fields
        print("✅ Categorize endpoint requires s3_path and filename")
    
    def test_categorize_invalid_process(self):
        """Test categorization with invalid process ID"""
        response = self.session.post(
            f"{BASE_URL}/api/documents/categorize/invalid-process-id",
            data={"s3_path": "test/path/doc.pdf", "filename": "doc.pdf"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        assert "não encontrado" in data["detail"].lower() or "not found" in data["detail"].lower()
        print("✅ Invalid process returns 404")
    
    def test_categorize_file_not_found(self):
        """Test categorization with non-existent S3 file"""
        response = self.session.post(
            f"{BASE_URL}/api/documents/categorize/{TEST_PROCESS_ID}",
            data={
                "s3_path": "nonexistent/path/document.pdf",
                "filename": "document.pdf"
            }
        )
        # Should return error because file doesn't exist in S3
        # Either 404 (file not found) or 500 (S3 error)
        assert response.status_code in [404, 500], f"Expected 404 or 500, got {response.status_code}"
        print(f"✅ Non-existent S3 file returns {response.status_code}")


class TestCategorizeAll:
    """Test POST /api/documents/categorize-all/{process_id}"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_categorize_all_success(self):
        """Test categorize all documents for a process"""
        response = self.session.post(
            f"{BASE_URL}/api/documents/categorize-all/{TEST_PROCESS_ID}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "total" in data, "Response should contain total"
        assert "categorized" in data, "Response should contain categorized"
        assert "skipped" in data, "Response should contain skipped"
        assert "errors" in data, "Response should contain errors"
        assert "documents" in data, "Response should contain documents list"
        assert isinstance(data["documents"], list)
        
        print(f"✅ Categorize all: {data['total']} total, {data['categorized']} categorized, {data['skipped']} skipped, {data['errors']} errors")
    
    def test_categorize_all_invalid_process(self):
        """Test categorize all with invalid process ID"""
        response = self.session.post(
            f"{BASE_URL}/api/documents/categorize-all/invalid-process-id"
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        print("✅ Invalid process ID returns 404")


class TestDocumentSearchValidation:
    """Test document search request validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_search_limit_validation(self):
        """Test search limit parameter validation"""
        # Test limit above maximum (100)
        response = self.session.post(f"{BASE_URL}/api/documents/search", json={
            "query": "test",
            "limit": 150
        })
        assert response.status_code == 422, f"Expected 422 for limit > 100, got {response.status_code}"
        print("✅ Limit > 100 returns 422")
    
    def test_search_limit_minimum(self):
        """Test search limit minimum validation"""
        # Test limit below minimum (1)
        response = self.session.post(f"{BASE_URL}/api/documents/search", json={
            "query": "test",
            "limit": 0
        })
        assert response.status_code == 422, f"Expected 422 for limit < 1, got {response.status_code}"
        print("✅ Limit < 1 returns 422")
    
    def test_search_query_max_length(self):
        """Test search query max length validation"""
        # Test query above maximum (500 chars)
        long_query = "a" * 501
        response = self.session.post(f"{BASE_URL}/api/documents/search", json={
            "query": long_query,
            "limit": 20
        })
        assert response.status_code == 422, f"Expected 422 for query > 500 chars, got {response.status_code}"
        print("✅ Query > 500 chars returns 422")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
