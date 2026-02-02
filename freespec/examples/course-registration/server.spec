# server.spec

description:
HTTP server for the course registration system. Runs on configurable port,
default 8080. All responses are JSON. Authentication via Bearer tokens.

Routes requests to @endpoints/students, @endpoints/courses, @endpoints/registrations.

Includes middleware for request logging, error handling, and rate limiting.

api:
Start the server with configuration options.
Stop the server gracefully, completing any pending requests.
Health check endpoint that returns server status and uptime.

tests:
Server starts on configured port
Health endpoint returns 200
Invalid routes return 404
Missing auth returns 401
Rate limiting triggers after threshold
Graceful shutdown completes pending requests
