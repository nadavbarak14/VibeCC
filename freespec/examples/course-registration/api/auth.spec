# auth.spec

description:
The auth API provides REST endpoints for student authentication, using @services/auth for the business logic.

POST /auth/register creates a new student account. The request body contains email, name, and password. Returns 201 with the student data on success, 400 for validation errors, or 409 if the email is already taken.

POST /auth/login authenticates a student. The request body contains email and password. Returns 200 with a session token on success, 401 for invalid credentials, or 429 if rate-limited. The session token should be included in subsequent requests as a Bearer token in the Authorization header.

POST /auth/logout invalidates the current session. Requires authentication. Returns 204 on success or 401 if not authenticated.

GET /auth/me returns information about the currently authenticated student. Requires authentication. Returns 200 with student data or 401 if not authenticated.

All endpoints accept and return JSON. Error responses include a message field explaining what went wrong.

exports:
- POST /auth/register to create a new student account
- POST /auth/login to authenticate and get a session token
- POST /auth/logout to invalidate the current session
- GET /auth/me to get current student information

tests:
- POST /auth/register with valid data returns 201 and student data
- POST /auth/register with missing fields returns 400
- POST /auth/register with invalid email format returns 400
- POST /auth/register with short password returns 400
- POST /auth/register with existing email returns 409
- POST /auth/login with valid credentials returns 200 and token
- POST /auth/login with invalid credentials returns 401
- POST /auth/login when rate-limited returns 429
- POST /auth/logout with valid token returns 204
- POST /auth/logout without authentication returns 401
- GET /auth/me with valid token returns 200 and student data
- GET /auth/me without authentication returns 401
- GET /auth/me with expired token returns 401
