# server.spec

## Description
HTTP server for the course registration system.
Runs on configurable port (default 8080).
All responses are JSON. Authentication via Bearer tokens.

Routes to @endpoints/students, @endpoints/courses, @endpoints/registrations.

Middleware: request logging, error handling, rate limiting.

## API
- start(config) -> Server
  Initializes and starts the HTTP server.

- stop() -> void
  Gracefully shuts down, completing pending requests.

- healthCheck() -> HealthStatus
  Returns server status and uptime.

## Tests
- Server starts on configured port
- Health endpoint returns 200
- Invalid routes return 404
- Missing auth returns 401
- Rate limiting triggers after threshold
- Graceful shutdown completes pending requests
