#!/bin/bash
# ====================================================================
# LOAD TEST RUNNER - CREDITOIMO
# ====================================================================
# Script para executar testes de carga com Locust
#
# Uso:
#   ./run_tests.sh [comando]
#
# Comandos:
#   quick       - Teste rápido (30s, 20 users)
#   ratelimit   - Teste de rate limiting (30s, agressivo)
#   stress      - Teste de stress (2min, 100 users)
#   web         - Iniciar interface web
#   help        - Mostrar ajuda
# ====================================================================

set -e

# Configuração
HOST="${API_HOST:-http://localhost:8001}"
LOCUST_FILE="locustfile.py"

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}  CreditoIMO Load Test Runner${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo ""
    echo "Uso: ./run_tests.sh [comando]"
    echo ""
    echo "Comandos:"
    echo -e "  ${GREEN}quick${NC}       Teste rápido (30s, 20 utilizadores)"
    echo -e "  ${GREEN}ratelimit${NC}   Teste de rate limiting (30s, agressivo)"
    echo -e "  ${GREEN}stress${NC}      Teste de stress (2min, 100 utilizadores)"
    echo -e "  ${GREEN}baseline${NC}    Teste de baseline (apenas health checks)"
    echo -e "  ${GREEN}web${NC}         Iniciar interface web em localhost:8089"
    echo -e "  ${GREEN}report${NC}      Gerar relatório HTML"
    echo ""
    echo "Variáveis de ambiente:"
    echo "  API_HOST    URL da API (default: http://localhost:8001)"
    echo ""
}

case "${1:-help}" in
    quick)
        echo -e "${GREEN}🚀 Executando teste rápido...${NC}"
        echo "   Host: $HOST"
        echo "   Duração: 30 segundos"
        echo "   Utilizadores: 20"
        echo ""
        locust -f $LOCUST_FILE --host=$HOST \
            --users=20 --spawn-rate=5 --run-time=30s --headless
        ;;
    
    ratelimit)
        echo -e "${GREEN}🛑 Testando Rate Limiting...${NC}"
        echo "   Host: $HOST"
        echo "   Duração: 30 segundos"
        echo "   Utilizadores: 30 (agressivos)"
        echo ""
        echo -e "${YELLOW}⚠️  Este teste vai triggerar muitos 429 (esperado!)${NC}"
        echo ""
        locust -f $LOCUST_FILE --host=$HOST \
            --users=30 --spawn-rate=30 --run-time=30s --headless
        ;;
    
    stress)
        echo -e "${GREEN}💪 Executando teste de stress...${NC}"
        echo "   Host: $HOST"
        echo "   Duração: 2 minutos"
        echo "   Utilizadores: 100"
        echo ""
        locust -f $LOCUST_FILE --host=$HOST \
            --users=100 --spawn-rate=10 --run-time=120s --headless
        ;;
    
    baseline)
        echo -e "${GREEN}📊 Executando baseline (health checks only)...${NC}"
        echo "   Host: $HOST"
        echo ""
        locust -f $LOCUST_FILE --host=$HOST \
            --users=50 --spawn-rate=10 --run-time=30s --headless \
            HealthCheckUser
        ;;
    
    web)
        echo -e "${GREEN}🌐 Iniciando interface web...${NC}"
        echo "   Abrir: http://localhost:8089"
        echo "   Host alvo: $HOST"
        echo ""
        locust -f $LOCUST_FILE --host=$HOST
        ;;
    
    report)
        REPORT_FILE="report_$(date +%Y%m%d_%H%M%S).html"
        echo -e "${GREEN}📄 Gerando relatório HTML...${NC}"
        echo "   Output: $REPORT_FILE"
        echo ""
        locust -f $LOCUST_FILE --host=$HOST \
            --users=50 --spawn-rate=5 --run-time=60s --headless \
            --html=$REPORT_FILE
        echo ""
        echo -e "${GREEN}✅ Relatório gerado: $REPORT_FILE${NC}"
        ;;
    
    help|--help|-h)
        show_help
        ;;
    
    *)
        echo -e "${YELLOW}Comando desconhecido: $1${NC}"
        show_help
        exit 1
        ;;
esac
