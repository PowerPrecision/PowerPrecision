"""
====================================================================
LOAD TESTS - CREDITOIMO API
====================================================================
Testes de carga usando Locust para validar:
- Performance da API sob stress
- Funcionamento do Rate Limiting
- Tempos de resposta

ENDPOINTS TESTADOS:
- POST /api/auth/login          (Rate Limit: 10/minute)
- POST /api/public/client-registration (Rate Limit: 5/hour)
- GET  /health                  (Sem rate limit)

COMO EXECUTAR:

1. Interface Web (recomendado):
   cd /app/load_tests && locust -f locustfile.py --host=http://localhost:8001
   Abrir: http://localhost:8089

2. Linha de comando (headless):
   cd /app/load_tests && locust -f locustfile.py \\
       --host=http://localhost:8001 \\
       --users=50 \\
       --spawn-rate=5 \\
       --run-time=60s \\
       --headless

3. Teste rápido de Rate Limiting:
   cd /app/load_tests && locust -f locustfile.py \\
       --host=http://localhost:8001 \\
       --users=20 \\
       --spawn-rate=20 \\
       --run-time=30s \\
       --headless

MÉTRICAS A OBSERVAR:
- Requests/s
- Response times (p50, p95, p99)
- Taxa de erros 429 (Too Many Requests)
- Taxa de erros 5xx

====================================================================
"""
import random
import string
import time
from datetime import datetime
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner


# ====================================================================
# CONFIGURAÇÃO
# ====================================================================
class TestConfig:
    """Configuração dos testes."""
    
    # Credenciais válidas para teste
    VALID_EMAIL = "admin@sistema.pt"
    VALID_PASSWORD = "admin2026"
    
    # Tipos de processo válidos
    PROCESS_TYPES = [
        "compra_de_habitacao",
        "construcao",
        "transferencia_de_credito",
        "credito_pessoal"
    ]


# ====================================================================
# CONTADORES GLOBAIS
# ====================================================================
class RateLimitTracker:
    """Rastreia respostas 429 para validar Rate Limiting."""
    
    def __init__(self):
        self.rate_limit_hits = {
            "login": 0,
            "registration": 0,
            "other": 0
        }
        self.total_requests = {
            "login": 0,
            "registration": 0,
            "other": 0
        }
    
    def record_request(self, endpoint: str, status_code: int):
        """Regista um request."""
        key = self._get_key(endpoint)
        self.total_requests[key] += 1
        
        if status_code == 429:
            self.rate_limit_hits[key] += 1
    
    def _get_key(self, endpoint: str) -> str:
        if "login" in endpoint:
            return "login"
        elif "registration" in endpoint:
            return "registration"
        return "other"
    
    def get_stats(self) -> dict:
        """Retorna estatísticas."""
        return {
            "rate_limit_hits": self.rate_limit_hits,
            "total_requests": self.total_requests,
            "rate_limit_working": self.rate_limit_hits["login"] > 0 or self.rate_limit_hits["registration"] > 0
        }


# Instância global do tracker
rate_limit_tracker = RateLimitTracker()


# ====================================================================
# EVENT HANDLERS
# ====================================================================
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, 
               response, context, exception, start_time, url, **kwargs):
    """Listener para todos os requests - rastreia rate limits."""
    if response is not None:
        try:
            status_code = response.status_code
            rate_limit_tracker.record_request(name, status_code)
        except Exception:
            pass  # Ignorar erros no tracking


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Executado quando o teste termina - mostra resumo."""
    stats = rate_limit_tracker.get_stats()
    
    print("\n" + "=" * 60)
    print("RATE LIMITING VALIDATION REPORT")
    print("=" * 60)
    print(f"\n📊 Requests totais:")
    for endpoint, count in stats["total_requests"].items():
        print(f"   - {endpoint}: {count}")
    
    print(f"\n🛑 Rate Limit Hits (429):")
    for endpoint, count in stats["rate_limit_hits"].items():
        print(f"   - {endpoint}: {count}")
    
    if stats["rate_limit_working"]:
        print(f"\n✅ RATE LIMITING ESTÁ A FUNCIONAR CORRECTAMENTE!")
    else:
        print(f"\n⚠️  Nenhum 429 detectado - Rate Limit pode não estar activo ou teste muito curto")
    
    print("=" * 60 + "\n")


# ====================================================================
# UTILIZADOR BASE
# ====================================================================
class CreditoIMOUser(HttpUser):
    """
    Utilizador simulado que executa tarefas típicas na API.
    
    Comportamento:
    - Espera 1-3 segundos entre tarefas
    - Mistura de operações autenticadas e públicas
    """
    
    # Tempo de espera entre tarefas (simula comportamento real)
    wait_time = between(1, 3)
    
    # Armazenar token de autenticação
    token = None
    
    def on_start(self):
        """Executado quando o utilizador inicia."""
        # Tentar autenticar no início
        self._authenticate()
    
    def _authenticate(self):
        """Obtém token de autenticação."""
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": TestConfig.VALID_EMAIL,
                "password": TestConfig.VALID_PASSWORD
            },
            headers={"Content-Type": "application/json"},
            name="/api/auth/login (auth)"
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
    
    def _get_auth_headers(self):
        """Retorna headers com autenticação."""
        if self.token:
            return {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
        return {"Content-Type": "application/json"}
    
    # ================================================================
    # TAREFAS
    # ================================================================
    
    @task(3)
    def health_check(self):
        """
        Tarefa: Verificar health da API.
        Peso: 3 (mais frequente)
        """
        with self.client.get(
            "/health",
            name="/health",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(5)
    def login_attempt(self):
        """
        Tarefa: Tentar fazer login.
        Peso: 5 (muito frequente - para testar rate limiting)
        
        Rate Limit esperado: 10/minute
        """
        # Alternar entre credenciais válidas e inválidas
        use_valid = random.random() > 0.3
        
        credentials = {
            "email": TestConfig.VALID_EMAIL if use_valid else f"user{random.randint(1,1000)}@test.com",
            "password": TestConfig.VALID_PASSWORD if use_valid else "wrongpassword"
        }
        
        with self.client.post(
            "/api/auth/login",
            json=credentials,
            headers={"Content-Type": "application/json"},
            name="/api/auth/login",
            catch_response=True
        ) as response:
            # Aceitar 200 (sucesso), 401 (credenciais inválidas) e 429 (rate limit)
            if response.status_code in [200, 401, 429]:
                if response.status_code == 429:
                    # Rate limit atingido - marcar como sucesso do teste
                    response.success()
                else:
                    response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def public_registration(self):
        """
        Tarefa: Submeter registo público.
        Peso: 2
        
        Rate Limit esperado: 5/hour
        """
        # Gerar dados únicos para cada request
        unique_id = ''.join(random.choices(string.ascii_lowercase, k=8))
        
        registration_data = {
            "name": f"Teste LoadTest {unique_id}",
            "email": f"loadtest_{unique_id}@example.com",
            "phone": f"9{random.randint(10000000, 99999999)}",
            "process_type": random.choice(TestConfig.PROCESS_TYPES),
            "message": "Teste de carga automatizado"
        }
        
        with self.client.post(
            "/api/public/client-registration",
            json=registration_data,
            headers={"Content-Type": "application/json"},
            name="/api/public/client-registration",
            catch_response=True
        ) as response:
            # Aceitar 200/201 (sucesso), 400 (validação), 422 (duplicado) e 429 (rate limit)
            if response.status_code in [200, 201, 400, 422, 429]:
                if response.status_code == 429:
                    # Rate limit atingido - marcar como sucesso do teste
                    response.success()
                else:
                    response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(1)
    def get_processes_list(self):
        """
        Tarefa: Listar processos (autenticado).
        Peso: 1
        """
        if not self.token:
            self._authenticate()
            if not self.token:
                return
        
        with self.client.get(
            "/api/processes",
            headers=self._get_auth_headers(),
            name="/api/processes",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 403]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# ====================================================================
# UTILIZADOR AGRESSIVO (para testar rate limiting)
# ====================================================================
class AggressiveUser(HttpUser):
    """
    Utilizador agressivo que faz muitos requests rapidamente.
    Usado especificamente para testar Rate Limiting.
    """
    
    # Sem espera entre requests (máxima agressividade)
    wait_time = between(0.1, 0.5)
    
    @task(1)
    def spam_login(self):
        """
        Tarefa: Spam de tentativas de login.
        Deve triggerar rate limit rapidamente.
        """
        with self.client.post(
            "/api/auth/login",
            json={
                "email": f"spam{random.randint(1,100)}@test.com",
                "password": "testpassword"
            },
            headers={"Content-Type": "application/json"},
            name="/api/auth/login (spam)",
            catch_response=True
        ) as response:
            # Qualquer resposta é válida para este teste
            if response.status_code == 429:
                # Rate limit a funcionar!
                response.success()
            elif response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"Unexpected: {response.status_code}")


# ====================================================================
# UTILIZADOR PARA HEALTH CHECK ONLY
# ====================================================================
class HealthCheckUser(HttpUser):
    """
    Utilizador que apenas faz health checks.
    Útil para testar performance base sem rate limiting.
    """
    
    wait_time = between(0.5, 1)
    
    @task
    def health_check(self):
        """Health check simples."""
        self.client.get("/health")
    
    @task
    def health_detailed(self):
        """Health check detalhado."""
        self.client.get("/health/detailed")


# ====================================================================
# COMANDOS DE EXECUÇÃO (para referência)
# ====================================================================
"""
# Teste básico com interface web:
locust -f locustfile.py --host=http://localhost:8001

# Teste headless (60 segundos, 50 utilizadores):
locust -f locustfile.py --host=http://localhost:8001 \
    --users=50 --spawn-rate=10 --run-time=60s --headless

# Teste de Rate Limiting (agressivo):
locust -f locustfile.py --host=http://localhost:8001 \
    --users=30 --spawn-rate=30 --run-time=30s --headless \
    -u AggressiveUser

# Apenas health checks (baseline):
locust -f locustfile.py --host=http://localhost:8001 \
    --users=100 --spawn-rate=20 --run-time=30s --headless \
    -u HealthCheckUser

# Gerar relatório HTML:
locust -f locustfile.py --host=http://localhost:8001 \
    --users=50 --spawn-rate=5 --run-time=120s --headless \
    --html=report.html
"""
