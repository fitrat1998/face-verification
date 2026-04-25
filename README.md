# Face Verification Authentication System

Production-ready face verification authentication system for 1000+ students with Moodle integration.

## Features

- 📝 **Face Registration** - Capture and store facial data
- 🔓 **Face Recognition Login** - Real-time face detection and login
- 🔗 **Moodle Integration** - Automatic OAuth2 integration
- 🛡️ **Security** - JWT, encryption, rate limiting
- 📊 **Audit Logging** - Complete login history
- 🚀 **Scalable** - Optimized for 1000+ users

## Technology Stack

- **Frontend**: HTML5, Vanilla JavaScript, face-api.js
- **Backend**: Python Flask
- **Database**: PostgreSQL
- **Face Recognition**: Python face_recognition library
- **Deployment**: Docker, docker-compose

## Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Node.js (for frontend development)

### Installation

1. Clone repository
```bash
git clone https://github.com/fitrat1998/face-verification.git
cd face-verification
```

2. Install Python dependencies
```bash
pip install -r requirements.txt
```

3. Setup environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Setup PostgreSQL database
```bash
psql -U postgres -d face_verification < schema.sql
```

5. Run Flask application
```bash
python app.py
```

6. Open browser
```
http://localhost:5000
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new student with face
- `POST /api/auth/login` - Face recognition login
- `POST /api/auth/logout` - Logout

### Student Profile
- `GET /api/student/profile` - Get student profile
- `POST /api/student/update-face` - Update face data
- `GET /api/student/login-history` - Get login history

### Moodle Integration
- `GET /api/moodle/oauth/authorize` - OAuth authorization
- `POST /api/moodle/oauth/callback` - OAuth callback

## Configuration

Edit `.env` file:

```env
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/face_verification

# JWT
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=3600

# Moodle
MOODLE_URL=https://your-moodle.com
MOODLE_CLIENT_ID=your-client-id
MOODLE_CLIENT_SECRET=your-client-secret

# Face Recognition
FACE_MATCH_THRESHOLD=0.6
```

## Docker Deployment

```bash
docker-compose up -d
```

This will start:
- Flask API on port 5000
- PostgreSQL on port 5432

## Database Schema

### students
- id, student_id, name, email, password_hash, created_at, updated_at

### face_data
- id, student_id, face_encoding, captured_at

### login_logs
- id, student_id, login_time, logout_time, ip_address, face_match_score

### moodle_sessions
- id, student_id, moodle_user_id, session_token, expires_at

## Security Features

- ✅ Password hashing with bcrypt
- ✅ JWT token authentication
- ✅ Face data encryption
- ✅ CORS protection
- ✅ Rate limiting (5 attempts/15 min)
- ✅ SQL injection prevention
- ✅ Input validation and sanitization

## Documentation

- [API Documentation](docs/API_DOCUMENTATION.md)
- [Moodle Integration Guide](docs/MOODLE_INTEGRATION.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Security Best Practices](docs/SECURITY.md)

## Project Structure

```
face-verification/
├── app.py                 # Flask main application
├── models.py              # Database models
├── face_recognition.py    # Face processing logic
├── auth.py                # Authentication logic
├── moodle_integration.py  # Moodle OAuth integration
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker configuration
├── Dockerfile             # Docker image
├── .env.example            # Environment template
├── schema.sql             # Database schema
├── index.html             # Frontend landing page
├── register.html          # Registration page
├── login.html             # Login page
├── dashboard.html         # Student dashboard
├── styles.css             # Frontend styles
└── docs/                  # Documentation
    ├── API_DOCUMENTATION.md
    ├── MOODLE_INTEGRATION.md
    ├── DEPLOYMENT.md
    └── SECURITY.md
```

## Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## License

MIT License

## Support

For issues and questions, please create an issue on GitHub.

## Author

fitrat1998

## Acknowledgments

- face-api.js for face detection
- face_recognition for face encoding
- Flask for web framework
