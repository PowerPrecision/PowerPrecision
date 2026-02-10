#!/bin/bash
# ====================================================================
# DOCKER HELPER SCRIPT - CREDITOIMO
# ====================================================================
# Comandos úteis para gestão dos containers Docker
#
# Uso:
#   ./docker.sh [comando]
#
# Comandos:
#   start       - Iniciar todos os serviços
#   stop        - Parar todos os serviços
#   restart     - Reiniciar todos os serviços
#   dev         - Iniciar em modo desenvolvimento
#   logs        - Ver logs do backend
#   shell       - Abrir shell no container backend
#   test        - Executar testes
#   build       - Rebuild das imagens
#   clean       - Limpar containers e volumes
# ====================================================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função de ajuda
show_help() {
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}  CreditoIMO - Docker Helper${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo ""
    echo "Uso: ./docker.sh [comando]"
    echo ""
    echo "Comandos disponíveis:"
    echo -e "  ${GREEN}start${NC}       Iniciar todos os serviços (produção)"
    echo -e "  ${GREEN}stop${NC}        Parar todos os serviços"
    echo -e "  ${GREEN}restart${NC}     Reiniciar todos os serviços"
    echo -e "  ${GREEN}dev${NC}         Iniciar em modo desenvolvimento (com hot reload)"
    echo -e "  ${GREEN}full${NC}        Iniciar com worker de tasks"
    echo -e "  ${GREEN}logs${NC}        Ver logs do backend"
    echo -e "  ${GREEN}logs-all${NC}    Ver logs de todos os serviços"
    echo -e "  ${GREEN}shell${NC}       Abrir shell no container backend"
    echo -e "  ${GREEN}test${NC}        Executar testes"
    echo -e "  ${GREEN}build${NC}       Rebuild das imagens"
    echo -e "  ${GREEN}clean${NC}       Limpar containers e volumes"
    echo -e "  ${GREEN}status${NC}      Ver status dos containers"
    echo -e "  ${GREEN}health${NC}      Verificar health dos serviços"
    echo ""
}

# Verificar se docker está instalado
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Erro: Docker não está instalado${NC}"
        exit 1
    fi
    if ! command -v docker compose &> /dev/null; then
        echo -e "${RED}Erro: Docker Compose não está instalado${NC}"
        exit 1
    fi
}

# Comandos
case "${1:-help}" in
    start)
        check_docker
        echo -e "${GREEN}Iniciando serviços...${NC}"
        docker compose up -d
        echo -e "${GREEN}✅ Serviços iniciados${NC}"
        docker compose ps
        ;;
    
    stop)
        check_docker
        echo -e "${YELLOW}Parando serviços...${NC}"
        docker compose down
        echo -e "${GREEN}✅ Serviços parados${NC}"
        ;;
    
    restart)
        check_docker
        echo -e "${YELLOW}Reiniciando serviços...${NC}"
        docker compose restart
        echo -e "${GREEN}✅ Serviços reiniciados${NC}"
        ;;
    
    dev)
        check_docker
        echo -e "${GREEN}Iniciando em modo desenvolvimento...${NC}"
        docker compose --profile dev up -d
        echo -e "${GREEN}✅ Ambiente de desenvolvimento pronto${NC}"
        echo ""
        echo "Serviços disponíveis:"
        echo "  - Backend:        http://localhost:8001"
        echo "  - API Docs:       http://localhost:8001/docs"
        echo "  - Mongo Express:  http://localhost:8081"
        echo "  - Redis Commander:http://localhost:8082"
        ;;
    
    full)
        check_docker
        echo -e "${GREEN}Iniciando stack completa (com worker)...${NC}"
        docker compose --profile full up -d
        echo -e "${GREEN}✅ Stack completa iniciada${NC}"
        docker compose ps
        ;;
    
    logs)
        check_docker
        docker compose logs -f backend
        ;;
    
    logs-all)
        check_docker
        docker compose logs -f
        ;;
    
    shell)
        check_docker
        echo -e "${BLUE}Abrindo shell no backend...${NC}"
        docker compose exec backend /bin/bash
        ;;
    
    test)
        check_docker
        echo -e "${BLUE}Executando testes...${NC}"
        docker compose exec backend pytest tests/ -v
        ;;
    
    build)
        check_docker
        echo -e "${YELLOW}Rebuilding imagens...${NC}"
        docker compose build --no-cache
        echo -e "${GREEN}✅ Build concluído${NC}"
        ;;
    
    clean)
        check_docker
        echo -e "${RED}⚠️  Isto vai remover todos os containers e volumes!${NC}"
        read -p "Tem certeza? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose down -v --remove-orphans
            docker system prune -f
            echo -e "${GREEN}✅ Limpeza concluída${NC}"
        else
            echo "Cancelado."
        fi
        ;;
    
    status)
        check_docker
        echo -e "${BLUE}Status dos containers:${NC}"
        docker compose ps
        ;;
    
    health)
        check_docker
        echo -e "${BLUE}Verificando health dos serviços...${NC}"
        echo ""
        
        # Backend
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            echo -e "Backend:  ${GREEN}✅ Healthy${NC}"
        else
            echo -e "Backend:  ${RED}❌ Unhealthy${NC}"
        fi
        
        # MongoDB
        if docker compose exec -T mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
            echo -e "MongoDB:  ${GREEN}✅ Healthy${NC}"
        else
            echo -e "MongoDB:  ${RED}❌ Unhealthy${NC}"
        fi
        
        # Redis
        if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
            echo -e "Redis:    ${GREEN}✅ Healthy${NC}"
        else
            echo -e "Redis:    ${RED}❌ Unhealthy${NC}"
        fi
        ;;
    
    help|--help|-h)
        show_help
        ;;
    
    *)
        echo -e "${RED}Comando desconhecido: $1${NC}"
        show_help
        exit 1
        ;;
esac
