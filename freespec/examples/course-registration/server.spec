# server.spec

description:
HTTP server that hosts the course registration system.

Configuration:
- Port: configurable, defaults to 8080
- Host: configurable, defaults to 0.0.0.0
- Request timeout: configurable, defaults to 30 seconds

All responses are JSON with consistent structure:
- Success: { data: ... }
- Error: { error: string, message: string, details?: any }

Authentication via Bearer tokens in Authorization header. Tokens are validated
against @services/auth (external dependency). Unauthenticated requests to
protected routes receive 401.

Routes:
- /health - public health check
- /students/* - routes to @endpoints/students
- /courses/* - routes to @endpoints/courses
- /registrations/* - routes to @endpoints/registrations

Middleware stack (in order):
1. Request logging - logs method, path, duration, status code
2. Rate limiting - configurable per IP, defaults to 100 requests/minute
3. Authentication - extracts and validates Bearer token, attaches user to request
4. Error handling - catches exceptions, formats consistent error response

Graceful shutdown: on termination signal, stop accepting new connections,
wait for in-flight requests to complete (up to 30 seconds), then exit.

api:
Start the server with optional configuration. Binds to port, initializes
middleware, registers routes. Returns when server is listening.

Stop the server gracefully. Stops accepting connections, waits for pending
requests, then shuts down.

Health check returns server status including uptime, whether database is
reachable, and memory usage.

tests:
Server starts and listens on configured port
Server uses default port when not configured
Health endpoint returns 200 with status info
Health endpoint works without authentication
Request to unknown route returns 404
Request without auth to protected route returns 401
Request with invalid token returns 401
Request with valid token succeeds
Rate limit exceeded returns 429
Rate limit resets after window
All requests are logged with timing
Error responses have consistent format
Graceful shutdown waits for pending requests
Graceful shutdown times out after 30 seconds
