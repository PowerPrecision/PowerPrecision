#!/bin/bash
# =================================================================
# Script de Verificação de Segurança
# Executa Safety (vulnerabilidades) e Bandit (código)
# =================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
REPORTS_DIR="$SCRIPT_DIR/security-reports"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Verificação de Segurança CreditoIMO ===${NC}"
echo ""

# Criar directório de relatórios
mkdir -p "$REPORTS_DIR"

# 1. Safety - Verificar vulnerabilidades em dependências
echo -e "${YELLOW}[1/2] A executar Safety (vulnerabilidades de dependências)...${NC}"
cd "$BACKEND_DIR"

if safety check --output json > "$REPORTS_DIR/safety-report.json" 2>/dev/null; then
    echo -e "${GREEN}✓ Nenhuma vulnerabilidade crítica encontrada${NC}"
else
    echo -e "${RED}⚠ Vulnerabilidades encontradas - ver $REPORTS_DIR/safety-report.json${NC}"
fi

# 2. Bandit - Análise estática de segurança
echo ""
echo -e "${YELLOW}[2/2] A executar Bandit (análise estática de código)...${NC}"

# Executa bandit e guarda relatório completo (todas as severidades)
# Ignora testes e ambientes virtuais
if bandit -r . --exclude "./tests,./venv,./.venv" -f json -o "$REPORTS_DIR/bandit-report.json" 2>/dev/null; then
    echo -e "${GREEN}✓ Nenhum problema de segurança crítico encontrado${NC}"
else
    # Bandit retorna código != 0 se encontrar issues
    # Tenta ler o total de High Severity do JSON
    HIGH_ISSUES=$(python3 -c "import json; d=json.load(open('$REPORTS_DIR/bandit-report.json')); print(d['metrics']['_totals'].get('SEVERITY.HIGH', 0))" 2>/dev/null || echo "0")
    
    if [ "$HIGH_ISSUES" -gt 0 ]; then
        echo -e "${RED}⚠ $HIGH_ISSUES problemas de severidade ALTA encontrados${NC}"
    else
        echo -e "${GREEN}✓ Apenas problemas de média/baixa severidade encontrados${NC}"
    fi
fi

# Resumo
echo ""
echo -e "${YELLOW}=== Resumo ===${NC}"
echo "Relatórios gerados em: $REPORTS_DIR/"
echo "  - safety-report.json (vulnerabilidades de dependências)"
echo "  - bandit-report.json (análise de código)"

# Mostrar problemas de alta/média severidade do Bandit no terminal
echo ""
echo -e "${YELLOW}=== Issues Principais (Bandit - Medium/High) ===${NC}"

# CORREÇÃO AQUI: Usar apenas a flag nova e explicita
bandit -r . --exclude "./tests,./venv,./.venv" \
    --severity-level medium \
    --confidence-level medium \
    -q 2>/dev/null || true

echo ""
echo -e "${GREEN}Verificação concluída!${NC}"