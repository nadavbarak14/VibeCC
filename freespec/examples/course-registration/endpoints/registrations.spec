# registrations.spec

description:
REST endpoints for enrollment operations.
Base path: /registrations

Uses @services/enrollment for business logic.
Students can only manage their own registrations.

api:
GET /registrations - List registrations with optional filtering by student, course, status, pagination.
GET /registrations/:id - Get a registration with student and course details.
POST /registrations - Enroll a student in a course. Returns 201, or 409 for business rule violations.
POST /registrations/check-eligibility - Check if enrollment is allowed without making changes.
PUT /registrations/:id/complete - Mark as completed with a grade. Requires admin.
DELETE /registrations/:id - Drop enrollment with optional reason. Returns 409 if already completed.

tests:
List returns filtered registrations
Get returns registration details
Enroll creates registration
Enroll fails if prerequisites not met returns 409
Enroll fails if course full returns 409
Check eligibility returns reasons
Complete sets grade
Drop updates status
Drop fails for completed
Student cannot enroll others
