# 🎓 Face Verification Authentication System

A production-ready face recognition authentication system for 1000+ students with Moodle LMS integration.

## Architecture

```
Frontend (HTML + Vanilla JS)
    └─ face-api.js  (client-side face detection)
           ↓
Backend (Python Flask)
    ├─ JWT Authentication
    ├─ face_recognition (server-side verification)
    └─ PostgreSQL via SQLAlchemy
           ↓
Moodle LMS (OAuth2 SSO)
```

## Features

- **Face Registration** — capture 3–5 photos from different angles
- **Face Login** — real-time camera stream with one-click verification
- **Password Fallback** — traditional login when camera is unavailable
- **Student Dashboard** — profile, login history, face re-registration
- **Moodle SSO** — automatic user creation and session synchronisation
- **Audit Logging** — IP address, face match score, timestamps
- **Docker Support** — single `docker compose up` deployment
- **Security** — bcrypt, JWT, Fernet encryption, rate limiting, CORS

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose  
- Git

### 2. Clone & configure

```bash
git clone https://github.com/fitrat1998/face-verification.git
cd face-verification
cp .env.example .env
# Edit .env — at minimum change JWT_SECRET_KEY
```

### 3. Run

```bash
docker compose up --build
```

| Service  | URL                   |
|----------|-----------------------|
| Frontend | http://localhost:8080 |
| Backend  | http://localhost:5000 |

### 4. Local development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt
# Set DATABASE_URL to a local PostgreSQL instance
python app.py

# Frontend – open frontend/index.html in a browser
# or serve with: python -m http.server 8080 --directory frontend
```

## Project Structure

```
face-verification/
├── backend/
│   ├── app.py                # Flask application & API routes
│   ├── models.py             # SQLAlchemy models
│   ├── face_service.py       # Face encoding & comparison
│   ├── auth.py               # JWT & bcrypt helpers
│   └── moodle_integration.py # Moodle REST API / OAuth2
├── frontend/
│   ├── index.html            # Landing page
│   ├── register.html         # Registration wizard
│   ├── login.html            # Login (face + password)
│   ├── dashboard.html        # Student dashboard
│   └── styles.css            # Responsive styles
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
├── API_DOCUMENTATION.md
├── MOODLE_INTEGRATION.md
├── DEPLOYMENT.md
└── SECURITY.md
```

## Documentation

| Document | Description |
|---|---|
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | REST API reference |
| [MOODLE_INTEGRATION.md](MOODLE_INTEGRATION.md) | Moodle setup guide |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment |
| [SECURITY.md](SECURITY.md) | Security best practices |

## License

MIT
