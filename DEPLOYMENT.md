# Deployment Guide

## Docker (Recommended)

### 1. Clone & configure

```bash
git clone https://github.com/fitrat1998/face-verification.git
cd face-verification
cp .env.example .env
```

Edit `.env` and set **at minimum**:
- `JWT_SECRET_KEY` — long random string (e.g. `openssl rand -hex 32`)
- `CORS_ORIGINS` — your frontend domain

### 2. Build & start

```bash
docker compose up --build -d
```

Services:
| Service  | Port | Description |
|----------|------|-------------|
| frontend | 8080 | Nginx static file server |
| backend  | 5000 | Flask API |
| db       | (internal) | PostgreSQL 15 |
| redis    | (internal) | Rate limiter store |

### 3. Health check

```bash
curl http://localhost:5000/api/health   # should return 200 once backend is ready
```

### 4. Logs

```bash
docker compose logs -f backend
```

---

## Production Checklist

- [ ] `JWT_SECRET_KEY` changed from default
- [ ] `FLASK_DEBUG=false`
- [ ] PostgreSQL password changed
- [ ] HTTPS/TLS termination in front of the backend (nginx, Caddy, or a load balancer)
- [ ] `CORS_ORIGINS` set to your frontend domain only
- [ ] Redis persistence enabled (`appendonly yes` in redis.conf)
- [ ] Database backups scheduled (pg_dump cron job or managed service)
- [ ] Container image pinned to specific digest in production

---

## HTTPS with Nginx Reverse Proxy (example)

```nginx
server {
    listen 443 ssl http2;
    server_name auth.youruni.edu;

    ssl_certificate     /etc/letsencrypt/live/auth.youruni.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/auth.youruni.edu/privkey.pem;

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /var/www/face-verification/frontend;
        try_files $uri $uri/ /index.html;
    }
}
```

---

## Scaling to 1000+ Students

- Deploy with **Gunicorn** (multiple workers): `gunicorn -w 4 -b 0.0.0.0:5000 app:app`
- Use **Redis** as the rate-limiter backend (`REDIS_URL`)
- Managed PostgreSQL (AWS RDS, Supabase, etc.) for production reliability
- CDN (Cloudflare, Fastly) for static frontend assets
