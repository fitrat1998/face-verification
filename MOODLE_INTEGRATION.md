# Moodle Integration Guide

This system integrates with Moodle LMS using two complementary approaches:

1. **User Key Authentication** (`auth_userkey`) — generate a one-time login URL for seamless SSO.
2. **Web Service REST API** — create/look up Moodle user accounts automatically.

---

## Prerequisites

- Moodle 3.9+ (4.x recommended)
- Administrator access to Moodle
- Moodle site must be accessible from the backend server

---

## Step 1 — Enable the User Key Authentication plugin

1. Go to **Site administration → Plugins → Authentication → Manage authentication**.
2. Enable **User key** authentication.
3. Configure: allow IPs, set key lifetime (e.g. 60 seconds).

---

## Step 2 — Create a Web Service

1. Go to **Site administration → Server → Web services → External services**.
2. Click **Add** and create a new service (e.g. `FaceAuth Service`).
3. Enable it and add the following functions:
   - `core_user_get_users_by_field`
   - `core_user_create_users`
   - `auth_userkey_request_login_url`

---

## Step 3 — Generate a Web Service Token

1. Go to **Site administration → Server → Web services → Manage tokens**.
2. Create a token for an administrator account and the service created above.
3. Copy the token to `MOODLE_WSTOKEN` in `.env`.

---

## Step 4 — Configure Environment Variables

```ini
MOODLE_BASE_URL=https://moodle.youruni.edu
MOODLE_WSTOKEN=your-ws-token-here
# OAuth2 fields are optional if only using user-key SSO
MOODLE_CLIENT_ID=
MOODLE_CLIENT_SECRET=
MOODLE_REDIRECT_URI=
```

---

## How It Works

### Registration Flow

```
Student registers → backend creates Moodle account (core_user_create_users)
                 → moodle_user_id stored in moodle_sessions table
```

### Login / Dashboard Flow

```
Student opens Dashboard → clicks "Open Moodle"
                       → backend calls auth_userkey_request_login_url
                       → returns one-time login URL
                       → browser opens Moodle, student is logged in automatically
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 503 from `/api/moodle/login-url` | `MOODLE_WSTOKEN` or `MOODLE_BASE_URL` not set | Set env vars and restart |
| `auth_userkey_request_login_url` returns error | Plugin not enabled | Enable User Key auth plugin |
| User not created | Missing `core_user_create_users` capability | Add function to Web Service |
