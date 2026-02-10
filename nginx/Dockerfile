# ====================================================================
# NGINX DOCKERFILE - CREDITOIMO
# ====================================================================
# Reverse Proxy com:
# - SSL/TLS termination
# - Proxy para Backend API
# - Serve Frontend estático
# - HTTP/2 support
# - Security headers
#
# Build: docker build -t creditoimo-nginx .
# ====================================================================

FROM nginx:1.27-alpine

# Metadata
LABEL maintainer="CreditoIMO <dev@creditoimo.pt>" \
      description="Nginx Reverse Proxy for CreditoIMO"

# Instalar certbot para SSL Let's Encrypt (opcional)
RUN apk add --no-cache \
    certbot \
    certbot-nginx \
    openssl \
    curl \
    tzdata

# Definir timezone
ENV TZ=Europe/Lisbon

# Criar directórios necessários
RUN mkdir -p /var/www/html \
    /etc/nginx/ssl \
    /etc/letsencrypt \
    /var/log/nginx

# Remover configuração default
RUN rm -f /etc/nginx/conf.d/default.conf

# Copiar configurações
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# Copiar script de entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Gerar certificado self-signed para desenvolvimento
# (Será substituído pelo Let's Encrypt em produção)
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/selfsigned.key \
    -out /etc/nginx/ssl/selfsigned.crt \
    -subj "/C=PT/ST=Lisboa/L=Lisboa/O=CreditoIMO/CN=localhost"

# Gerar DH parameters para SSL (segurança extra)
RUN openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Expor portas
EXPOSE 80 443

# Entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
