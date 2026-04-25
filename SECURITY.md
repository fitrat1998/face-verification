# Security Guide

## Overview

This document describes the security controls implemented in the Face Verification Authentication System and provides guidance for hardening production deployments.

---

## Controls in Place

### Authentication & Sessions

| Control | Implementation |
|---------|---------------|
| Password hashing | bcrypt with cost factor 12 |
| Session tokens | JWT (HS256), 1-hour expiry |
| Face encodings | Stored as raw numpy bytes; face data never leaves the server |
| Logout | Records logout timestamp; tokens expire naturally after 1 hour |

### API Security

| Control | Implementation |
|---------|---------------|
| Rate limiting | 5 login attempts / 15 min per IP; 10 registrations / hour |
| CORS | Configurable allow-list of frontend origins |
| Input validation | All request bodies validated; missing fields rejected with 400 |
| SQL injection | SQLAlchemy ORM with parameterised queries |

### Infrastructure

| Control | Implementation |
|---------|---------------|
| Secrets | Loaded from environment variables / `.env` (never committed) |
| Container | Runs as non-root `appuser` |
| Dependencies | Pinned versions in `requirements.txt` |

---

## Hardening Checklist

- [ ] Replace `JWT_SECRET_KEY` default value with `openssl rand -hex 32`
- [ ] Enable HTTPS (TLS 1.2+) — never serve over plain HTTP in production
- [ ] Restrict `CORS_ORIGINS` to your frontend domain
- [ ] Use a managed PostgreSQL instance with SSL enabled
- [ ] Enable PostgreSQL connection pooling (PgBouncer) for high concurrency
- [ ] Rotate JWT secret periodically (causes existing tokens to expire)
- [ ] Monitor login failures and set up alerting for brute-force patterns
- [ ] Keep dependencies up to date (`pip-audit` / Dependabot)
- [ ] Enable network policies if deploying to Kubernetes

---

## Face Data Privacy

- Face encodings (128-dimensional vectors) are stored as binary blobs in PostgreSQL.
- Raw images are **not** persisted — only the derived numeric encoding.
- Consider additional Fernet encryption of the `face_encoding` column for compliance with local biometric data laws (GDPR, PDPA, etc.).

---

## Reporting Security Issues

Please report security vulnerabilities privately via GitHub Security Advisories or by emailing the repository maintainer directly. Do not open public issues for security bugs.
