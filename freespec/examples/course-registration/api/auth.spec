# auth.spec

description:
REST API endpoints for authentication. Provides login, logout, and session management over HTTP. Uses @services/auth for business logic.

All endpoints accept and return JSON. Login returns a token that must be included in subsequent authenticated requests as a Bearer token in the Authorization header.

Error responses use standard HTTP status codes: 400 for bad requests, 401 for authentication failures, 403 for authorization failures, 404 for not found, 422 for validation errors.

Rate limiting is applied to login attempts to prevent brute force attacks. After 5 failed attempts from the same IP, requests are blocked for 15 minutes.

exports:
POST /auth/login - authenticate with email and password
POST /auth/logout - invalidate current session
POST /auth/logout-all - invalidate all sessions for current user
GET /auth/me - get current authenticated user
POST /auth/register - create a new student account

tests:
POST /auth/login with valid credentials returns 200 with token
POST /auth/login with invalid credentials returns 401
POST /auth/login with missing email returns 400
POST /auth/login with missing password returns 400
POST /auth/login with inactive account returns 401
POST /auth/login after rate limit returns 429
POST /auth/logout with valid token returns 204
POST /auth/logout without token returns 401
POST /auth/logout-all invalidates all sessions returns 204
GET /auth/me with valid token returns user data
GET /auth/me without token returns 401
GET /auth/me with expired token returns 401
POST /auth/register with valid data returns 201 with token
POST /auth/register with duplicate email returns 409
POST /auth/register with invalid email returns 422
POST /auth/register with weak password returns 422
