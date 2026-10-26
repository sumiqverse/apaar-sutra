# ==============================================================================
# Multi-Stage Production Dockerfile for APAAR-Sutra Frontend
# ==============================================================================

# --- Stage 1: Build Static Assets ---
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install --frozen-lockfile || npm install

COPY . .
RUN npm run build

# --- Stage 2: Serve with Non-Root Nginx ---
FROM nginxinc/nginx-unprivileged:alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html

# Replace default unprivileged nginx config for SPA routing
COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 8080;
    server_name localhost;

    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}
EOF

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
