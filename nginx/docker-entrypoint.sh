#!/bin/sh
# ====================================================================
# NGINX DOCKER ENTRYPOINT
# ====================================================================
# Script de inicialização do container Nginx
#
# Funcionalidades:
# - Verifica existência de certificados SSL
# - Configura variáveis de ambiente
# - Inicia Nginx
# ====================================================================

set -e

echo "========================================"
echo "  CreditoIMO Nginx Reverse Proxy"
echo "========================================"

# Verificar se os certificados existem
if [ ! -f /etc/nginx/ssl/selfsigned.crt ]; then
    echo "⚠️  Gerando certificados self-signed..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/selfsigned.key \
        -out /etc/nginx/ssl/selfsigned.crt \
        -subj "/C=PT/ST=Lisboa/L=Lisboa/O=CreditoIMO/CN=localhost"
fi

# Verificar se DH params existem
if [ ! -f /etc/nginx/ssl/dhparam.pem ]; then
    echo "⚠️  Gerando DH parameters (pode demorar)..."
    openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048
fi

# Criar directório para Let's Encrypt
mkdir -p /var/www/certbot

# Verificar configuração do Nginx
echo "🔍 Verificando configuração..."
nginx -t

echo "✅ Configuração válida"
echo "🚀 Iniciando Nginx..."

# Executar comando passado (nginx -g "daemon off;")
exec "$@"
