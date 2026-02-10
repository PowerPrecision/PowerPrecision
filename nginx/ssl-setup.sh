#!/bin/bash
# ====================================================================
# CERTBOT SSL SETUP - LET'S ENCRYPT
# ====================================================================
# Script para obter e renovar certificados SSL do Let's Encrypt
#
# Uso:
#   ./ssl-setup.sh [dominio]
#
# Exemplo:
#   ./ssl-setup.sh creditoimo.pt
#
# Pré-requisitos:
#   - DNS apontando para o servidor
#   - Portas 80 e 443 abertas
#   - Docker compose a correr
# ====================================================================

set -e

DOMAIN=${1:-creditoimo.pt}
EMAIL=${2:-admin@$DOMAIN}

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  Let's Encrypt SSL Setup${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo "Domínio: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Verificar se o docker está a correr
if ! docker compose ps | grep -q "nginx.*running"; then
    echo -e "${RED}❌ O container nginx não está a correr${NC}"
    echo "Execute primeiro: docker compose up -d"
    exit 1
fi

# 1. Obter certificado staging (teste)
echo -e "${YELLOW}🔍 Testando com staging...${NC}"
docker compose exec nginx certbot certonly \
    --nginx \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --staging \
    -d $DOMAIN \
    -d www.$DOMAIN

# Se sucesso, obter certificado real
echo ""
read -p "Staging OK? Obter certificado real? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}🔒 Obtendo certificado real...${NC}"
    docker compose exec nginx certbot certonly \
        --nginx \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        --force-renewal \
        -d $DOMAIN \
        -d www.$DOMAIN

    echo ""
    echo -e "${GREEN}✅ Certificado obtido com sucesso!${NC}"
    echo ""
    echo "Agora actualize o ficheiro nginx/conf.d/default.conf:"
    echo ""
    echo "1. Comente as linhas:"
    echo "   # ssl_certificate /etc/nginx/ssl/selfsigned.crt;"
    echo "   # ssl_certificate_key /etc/nginx/ssl/selfsigned.key;"
    echo ""
    echo "2. Descomente as linhas:"
    echo "   ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;"
    echo "   ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;"
    echo "   ssl_trusted_certificate /etc/letsencrypt/live/$DOMAIN/chain.pem;"
    echo ""
    echo "3. Reinicie o nginx:"
    echo "   docker compose restart nginx"
fi

# Setup auto-renovação
echo ""
echo -e "${YELLOW}📅 Configurar renovação automática...${NC}"
echo ""
echo "Adicione ao crontab do host:"
echo "0 0 1 * * docker compose exec nginx certbot renew --quiet && docker compose restart nginx"
