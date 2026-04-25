# API Documentation

Base URL: `http://localhost:5000`

All protected endpoints require the header:
```
Authorization: Bearer <JWT_TOKEN>
```

---

## Authentication

### POST /api/auth/register

Register a new student with face data.

**Rate limit:** 10 per hour per IP

**Request body:**
```json
{
  "student_id": "STU-2024-001",
  "name": "Jane Smith",
  "email": "jane@university.edu",
  "password": "securepassword",
  "face_images": ["<base64>", "<base64>", "<base64>"]
}
```

- `face_images` — array of 1–10 JPEG images encoded as base64 strings

**Response 201:**
```json
{
  "message": "Registration successful",
  "token": "<JWT>",
  "student": { "id": 1, "student_id": "STU-2024-001", "name": "Jane Smith", "email": "...", "created_at": "..." }
}
```

**Error responses:** 400 (missing fields), 409 (duplicate), 422 (no face in image)

---

### POST /api/auth/login

Authenticate via face recognition **or** student ID + password.

**Rate limit:** 5 per 15 minutes per IP

**Face login request:**
```json
{ "face_image": "<base64 JPEG>" }
```

**Password login request:**
```json
{ "student_id": "STU-2024-001", "password": "securepassword" }
```

**Response 200:**
```json
{
  "message": "Login successful",
  "token": "<JWT>",
  "student": { ... }
}
```

**Error responses:** 400, 401, 422

---

### POST /api/auth/logout

Invalidate the current session (records logout time).

**Protected:** Yes

**Response 200:**
```json
{ "message": "Logged out successfully" }
```

---

## Student

### GET /api/student/profile

Retrieve the authenticated student's profile.

**Protected:** Yes

**Response 200:**
```json
{
  "student": {
    "id": 1,
    "student_id": "STU-2024-001",
    "name": "Jane Smith",
    "email": "jane@university.edu",
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00"
  }
}
```

---

### POST /api/student/update-face

Replace all stored face encodings with new captures.

**Protected:** Yes  
**Rate limit:** 10 per hour per IP

**Request body:**
```json
{ "face_images": ["<base64>", "<base64>", "<base64>"] }
```

**Response 200:**
```json
{ "message": "Face data updated successfully" }
```

---

### GET /api/student/login-history

Retrieve up to 50 most recent login records.

**Protected:** Yes

**Response 200:**
```json
{
  "history": [
    {
      "id": 42,
      "student_id": 1,
      "login_time": "2024-06-01T08:30:00",
      "logout_time": "2024-06-01T09:15:00",
      "ip_address": "192.168.1.10",
      "face_match_score": 0.38,
      "status": "success"
    }
  ]
}
```

Status values: `success`, `failed`, `password`

---

## Moodle

### GET /api/moodle/login-url

Generate a Moodle auto-login URL for the authenticated student.

**Protected:** Yes

**Response 200:**
```json
{ "login_url": "https://moodle.youruni.edu/auth/userkey/login.php?key=..." }
```

**Error responses:** 503 (Moodle not configured or unreachable)

---

## Error Format

All errors return JSON:
```json
{ "error": "Human-readable description" }
```
