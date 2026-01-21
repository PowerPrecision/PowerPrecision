"""
Script para adicionar dados fictícios completos aos clientes/processos
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

# Dados fictícios portugueses
FIRST_NAMES_M = ["João", "Pedro", "Tiago", "Miguel", "Rui", "Carlos", "André", "Bruno", "Diogo", "Ricardo", "Paulo", "Nuno", "Fernando", "António", "José", "Manuel", "Francisco", "Luís", "Hugo", "Daniel", "Sérgio", "Rafael", "Vasco", "Rodrigo", "Gonçalo"]
FIRST_NAMES_F = ["Maria", "Ana", "Sofia", "Inês", "Catarina", "Mariana", "Rita", "Joana", "Patrícia", "Cristina", "Sandra", "Teresa", "Isabel", "Helena", "Luísa", "Carla", "Marta", "Paula", "Vera", "Diana", "Sílvia", "Andreia", "Sara", "Beatriz", "Carolina"]
LAST_NAMES = ["Silva", "Santos", "Ferreira", "Pereira", "Oliveira", "Costa", "Rodrigues", "Martins", "Jesus", "Sousa", "Fernandes", "Gonçalves", "Gomes", "Lopes", "Marques", "Alves", "Almeida", "Ribeiro", "Pinto", "Carvalho", "Teixeira", "Moreira", "Correia", "Mendes", "Nunes"]

STREET_TYPES = ["Rua", "Avenida", "Travessa", "Largo", "Praça"]
STREET_NAMES = ["da Liberdade", "Central", "do Comércio", "das Flores", "dos Combatentes", "de Santo António", "D. Pedro IV", "25 de Abril", "da República", "dos Heróis", "Nova", "Direita", "Principal"]

PROFESSIONS = [
    "Engenheiro/a Civil", "Médico/a", "Professor/a", "Advogado/a", "Arquiteto/a",
    "Contabilista", "Gestor/a", "Técnico/a de IT", "Enfermeiro/a", "Designer",
    "Comercial", "Empresário/a", "Funcionário/a Público", "Consultor/a", "Analista"
]

MARITAL_STATUS = ["Casado/a", "Solteiro/a", "Divorciado/a", "União de Facto"]

NOTES_TEMPLATES = [
    "Cliente interessado em financiamento. Primeira habitação.",
    "Reunião agendada para análise de documentação.",
    "Aguardar resposta do banco sobre pré-aprovação.",
    "Documentos entregues. Em análise.",
    "Cliente referenciado por {name}. Alta prioridade.",
    "Aguardar avaliação do imóvel pelo banco.",
    "Necessário atualizar recibos de vencimento.",
    "Cliente com excelente perfil financeiro.",
    "Processo em fase final de aprovação.",
    "Aguardar resposta sobre seguro de vida."
]


async def add_client_data():
    """Adiciona dados fictícios completos aos processos"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("📝 Adicionando dados fictícios aos clientes...")
    
    processes = await db.processes.find({}).to_list(length=500)
    updated_count = 0
    
    for process in processes:
        # Gerar dados pessoais se não existirem
        update_data = {}
        
        # Nome completo se necessário
        if not process.get('client_name') or ' ' not in process.get('client_name', ''):
            gender = random.choice(['M', 'F'])
            first_name = random.choice(FIRST_NAMES_M if gender == 'M' else FIRST_NAMES_F)
            last_name = random.choice(LAST_NAMES)
            last_name2 = random.choice(LAST_NAMES)
            update_data['client_name'] = f"{first_name} {last_name} {last_name2}"
        
        # Email se não existir ou for do formato trello.import
        if not process.get('client_email') or 'trello.import' in process.get('client_email', ''):
            name_parts = process.get('client_name', update_data.get('client_name', 'cliente')).lower().split()
            email_name = '.'.join(name_parts[:2]) if len(name_parts) >= 2 else name_parts[0]
            email_name = email_name.replace(' ', '.')
            domains = ['gmail.com', 'hotmail.com', 'sapo.pt', 'outlook.com', 'icloud.com']
            update_data['client_email'] = f"{email_name}@{random.choice(domains)}"
        
        # Telefone se não existir
        if not process.get('client_phone'):
            prefix = random.choice(['91', '92', '93', '96'])
            number = f"{random.randint(100, 999)} {random.randint(100, 999)}"
            update_data['client_phone'] = f"+351 {prefix}{number}"
        
        # Endereço se não existir
        if not process.get('client_address'):
            street_type = random.choice(STREET_TYPES)
            street_name = random.choice(STREET_NAMES)
            number = random.randint(1, 300)
            floor = random.randint(1, 8)
            side = random.choice(['Esq', 'Dto', 'Centro'])
            update_data['client_address'] = f"{street_type} {street_name}, nº {number}, {floor}º {side}"
        
        # Código Postal se não existir
        if not process.get('client_postal_code'):
            code1 = random.randint(1000, 9999)
            code2 = random.randint(100, 999)
            update_data['client_postal_code'] = f"{code1}-{code2}"
        
        # Data de nascimento se não existir
        if not process.get('client_birth_date'):
            # Idade entre 25 e 65 anos
            years_ago = random.randint(25, 65)
            birth_date = datetime.now() - timedelta(days=years_ago*365)
            update_data['client_birth_date'] = birth_date.strftime('%Y-%m-%d')
        
        # Estado civil se não existir
        if not process.get('client_marital_status'):
            update_data['client_marital_status'] = random.choice(MARITAL_STATUS)
        
        # Profissão se não existir
        if not process.get('client_profession'):
            update_data['client_profession'] = random.choice(PROFESSIONS)
        
        # Rendimento mensal se não existir
        if not process.get('client_monthly_income'):
            # Baseado no valor do empréstimo, calcular rendimento adequado
            loan = process.get('loan_amount', 150000)
            # Rendimento deve ser pelo menos 3x a prestação mensal estimada
            monthly_payment = (loan / 360) * 1.03  # 30 anos, taxa aproximada
            min_income = monthly_payment * 3
            update_data['client_monthly_income'] = int(random.randint(int(min_income), int(min_income * 1.8)))
        
        # Notas melhoradas se necessário
        if not process.get('notes') or 'Importado do Trello' in process.get('notes', ''):
            note_template = random.choice(NOTES_TEMPLATES)
            if '{name}' in note_template:
                ref_name = random.choice(FIRST_NAMES_M + FIRST_NAMES_F)
                note_template = note_template.replace('{name}', ref_name)
            update_data['notes'] = note_template
        
        # Observações adicionais
        observations = []
        if random.random() > 0.7:
            observations.append("✓ Cliente com histórico bancário limpo")
        if random.random() > 0.6:
            observations.append("✓ Sem dívidas pendentes")
        if random.random() > 0.8:
            observations.append("⚠ Aguardar documentos adicionais")
        if random.random() > 0.85:
            observations.append("★ Cliente VIP")
        
        if observations:
            current_notes = update_data.get('notes', process.get('notes', ''))
            update_data['notes'] = current_notes + '\n\n' + '\n'.join(observations)
        
        if update_data:
            await db.processes.update_one(
                {"id": process["id"]},
                {"$set": update_data}
            )
            updated_count += 1
            
            if updated_count % 10 == 0:
                print(f"  ✓ {updated_count} clientes atualizados...")
    
    print(f"\n✅ {updated_count} clientes atualizados com dados completos!")
    
    # Mostrar exemplo
    sample = await db.processes.find_one({})
    if sample:
        print("\n📋 Exemplo de cliente:")
        print(f"  Nome: {sample.get('client_name')}")
        print(f"  Email: {sample.get('client_email')}")
        print(f"  Telefone: {sample.get('client_phone')}")
        print(f"  Endereço: {sample.get('client_address', 'N/A')}")
        print(f"  Profissão: {sample.get('client_profession', 'N/A')}")
        print(f"  Rendimento: €{sample.get('client_monthly_income', 0):,}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(add_client_data())
