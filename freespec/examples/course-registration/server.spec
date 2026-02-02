# server.spec

## Description
HTTP server for the course registration system. Handles routing,
middleware, authentication, and error handling.

Runs on configurable port (default 8080).
All endpoints return JSON responses.
Authentication via Bearer tokens for protected routes.

## API
- start(config) -> Server
  Initializes and starts the HTTP server.

- stop() -> void
  Gracefully shuts down the server.

- healthCheck() -> HealthStatus
  Returns server status, uptime, and dependency health.

## Middleware
- Authentication: Validates Bearer tokens, attaches user context
- Logging: Logs all requests with method, path, duration, status
- ErrorHandler: Catches exceptions, returns consistent error format
- RateLimiter: Limits requests per IP (configurable)

## Routes
- /health -> health check (public)
- /students -> @endpoints/students
- /courses -> @endpoints/courses
- /registrations -> @endpoints/registrations

## Error Format
All errors return consistent structure:
- status: HTTP status code
- error: Error type identifier
- message: Human-readable description
- details: Optional additional context

## Tests
- Server starts on configured port
- Health endpoint returns 200 when healthy
- Invalid routes return 404
- Unauthenticated requests to protected routes return 401
- Rate limiting triggers after threshold
- Graceful shutdown completes pending requests

## Mentions
@endpoints/students
@endpoints/courses
@endpoints/registrations
