#!/usr/bin/env python3
"""
Create test data for CreditoIMO system
This script creates sample processes and documents to test the functionality
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "https://property-credit.preview.emergentagent.com"

def login_user(email, password):
    """Login and get token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def create_sample_processes():
    """Create sample processes with assignments"""
    # Login as admin
    admin_token = login_user("admin@sistema.pt", "admin2026")
    if not admin_token:
        print("❌ Failed to login as admin")
        return
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get user IDs
    users_response = requests.get(f"{BASE_URL}/api/users", headers=headers)
    if users_response.status_code != 200:
        print("❌ Failed to get users")
        return
    
    users = users_response.json()
    user_map = {user["email"]: user["id"] for user in users}
    
    flavio_id = user_map.get("flavio@powerealestate.pt")
    estacio_id = user_map.get("estacio@precisioncredito.pt")
    
    if not flavio_id or not estacio_id:
        print("❌ Could not find Flávio or Estácio user IDs")
        return
    
    # Create sample processes via public endpoint (simulating client registration)
    sample_processes = [
        {
            "name": "João Silva Santos",
            "email": "joao.santos@email.com",
            "phone": "+351 912 345 678",
            "process_type": "credito_habitacao",
            "personal_data": {
                "full_name": "João Silva Santos",
                "email": "joao.santos@email.com",
                "phone": "+351 912 345 678",
                "nif": "123456789",
                "birth_date": "1985-03-15",
                "nationality": "Portuguesa",
                "marital_status": "casado",
                "address": "Rua das Flores, 123, 1200-001 Lisboa"
            },
            "financial_data": {
                "monthly_income": 3500.0,
                "employment_type": "conta_outrem",
                "employer_name": "Tech Solutions Lda",
                "employment_duration": "60 meses",
                "other_income": 0.0,
                "monthly_expenses": 1200.0,
                "debt_amount": 0.0,
                "capital_proprio": 50000.0
            }
        },
        {
            "name": "Maria Fernanda Costa",
            "email": "maria.costa@email.com",
            "phone": "+351 913 456 789",
            "process_type": "credito_habitacao",
            "personal_data": {
                "full_name": "Maria Fernanda Costa",
                "email": "maria.costa@email.com",
                "phone": "+351 913 456 789",
                "nif": "987654321",
                "birth_date": "1990-07-22",
                "nationality": "Portuguesa",
                "marital_status": "solteira",
                "address": "Avenida da República, 456, 4000-001 Porto"
            },
            "financial_data": {
                "monthly_income": 2800.0,
                "employment_type": "conta_outrem",
                "employer_name": "Marketing Plus",
                "employment_duration": "36 meses",
                "other_income": 500.0,
                "monthly_expenses": 900.0,
                "debt_amount": 150.0,
                "capital_proprio": 30000.0
            }
        },
        {
            "name": "Carlos Manuel Pereira",
            "email": "carlos.pereira@email.com",
            "phone": "+351 914 567 890",
            "process_type": "transacao_imobiliaria",
            "personal_data": {
                "full_name": "Carlos Manuel Pereira",
                "email": "carlos.pereira@email.com",
                "phone": "+351 914 567 890",
                "nif": "456789123",
                "birth_date": "1978-11-10",
                "nationality": "Portuguesa",
                "marital_status": "divorciado",
                "address": "Rua do Comércio, 789, 3000-001 Coimbra"
            },
            "financial_data": {
                "monthly_income": 4200.0,
                "employment_type": "trabalhador_independente",
                "employer_name": "Consultoria CP Unipessoal",
                "employment_duration": "120 meses",
                "other_income": 800.0,
                "monthly_expenses": 1500.0,
                "debt_amount": 300.0,
                "capital_proprio": 80000.0
            }
        }
    ]
    
    created_processes = []
    
    # Create processes via public endpoint
    for i, process_data in enumerate(sample_processes):
        response = requests.post(f"{BASE_URL}/api/public/client-registration", json=process_data)
        if response.status_code == 200:
            result = response.json()
            # Get the created process
            process_id = result.get("process_id")
            if process_id:
                # Fetch the process details
                process_response = requests.get(f"{BASE_URL}/api/processes/{process_id}", headers=headers)
                if process_response.status_code == 200:
                    process = process_response.json()
                    created_processes.append(process)
                    print(f"✅ Created process {i+1}: {process['client_name']}")
                else:
                    print(f"⚠️ Process created but couldn't fetch details: {process_id}")
        else:
            print(f"❌ Failed to create process {i+1}: {response.status_code} - {response.text}")
    
    # Assign processes to Flávio and Estácio
    if created_processes:
        # Assign first process to Flávio as consultor
        if len(created_processes) >= 1:
            response = requests.post(
                f"{BASE_URL}/api/processes/{created_processes[0]['id']}/assign",
                json={"consultor_id": flavio_id},
                headers=headers
            )
            if response.status_code == 200:
                print(f"✅ Assigned process 1 to Flávio as consultor")
            else:
                print(f"❌ Failed to assign process 1 to Flávio: {response.status_code} - {response.text}")
        
        # Assign second process to Estácio as intermediário
        if len(created_processes) >= 2:
            response = requests.post(
                f"{BASE_URL}/api/processes/{created_processes[1]['id']}/assign",
                json={"mediador_id": estacio_id},
                headers=headers
            )
            if response.status_code == 200:
                print(f"✅ Assigned process 2 to Estácio as intermediário")
            else:
                print(f"❌ Failed to assign process 2 to Estácio: {response.status_code} - {response.text}")
        
        # Assign third process to both
        if len(created_processes) >= 3:
            response = requests.post(
                f"{BASE_URL}/api/processes/{created_processes[2]['id']}/assign",
                json={"consultor_id": flavio_id, "mediador_id": estacio_id},
                headers=headers
            )
            if response.status_code == 200:
                print(f"✅ Assigned process 3 to both Flávio and Estácio")
            else:
                print(f"❌ Failed to assign process 3: {response.status_code} - {response.text}")
    
    return created_processes

def create_sample_documents(processes):
    """Create sample document expiry records"""
    if not processes:
        return
    
    # Login as admin
    admin_token = login_user("admin@sistema.pt", "admin2026")
    if not admin_token:
        print("❌ Failed to login as admin")
        return
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create documents with different expiry dates
    today = datetime.now().date()
    
    sample_docs = [
        {
            "process_id": processes[0]["id"],
            "document_type": "cc",
            "document_name": "Cartão de Cidadão - João Santos",
            "expiry_date": (today + timedelta(days=30)).isoformat(),
            "notes": "Documento a expirar em breve"
        },
        {
            "process_id": processes[1]["id"] if len(processes) > 1 else processes[0]["id"],
            "document_type": "passaporte",
            "document_name": "Passaporte - Maria Costa",
            "expiry_date": (today + timedelta(days=45)).isoformat(),
            "notes": "Renovação necessária"
        },
        {
            "process_id": processes[2]["id"] if len(processes) > 2 else processes[0]["id"],
            "document_type": "certidao_predial",
            "document_name": "Certidão Predial - Imóvel Coimbra",
            "expiry_date": (today + timedelta(days=15)).isoformat(),
            "notes": "Urgente - expira em 2 semanas"
        }
    ]
    
    for i, doc_data in enumerate(sample_docs):
        response = requests.post(f"{BASE_URL}/api/documents/expiry", json=doc_data, headers=headers)
        if response.status_code == 200:
            print(f"✅ Created document {i+1}: {doc_data['document_name']}")
        else:
            print(f"❌ Failed to create document {i+1}: {response.status_code}")

def main():
    print("🚀 Creating test data for CreditoIMO system...")
    
    # Create processes
    processes = create_sample_processes()
    
    # Create documents
    if processes:
        create_sample_documents(processes)
    
    print("✅ Test data creation completed!")

if __name__ == "__main__":
    main()