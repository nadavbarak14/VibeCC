# registrations.spec

## Description
REST endpoints for enrollment operations.
Base path: /registrations

Uses @services/enrollment for business logic.
Students can only manage their own registrations.

## API
- GET /registrations -> list[Registration]
  List registrations. Query: studentId, courseId, status, page, limit.

- GET /registrations/:id -> Registration
  Get registration with student and course details.

- POST /registrations -> Registration
  Enroll student. Body: studentId, courseId.
  Returns 201, or 409 for business rule violations.

- POST /registrations/check-eligibility -> EligibilityResult
  Check if enrollment allowed. Body: studentId, courseId.

- PUT /registrations/:id/complete -> Registration
  Mark completed with grade. Body: grade. Requires admin.

- DELETE /registrations/:id -> void
  Drop enrollment. Body: reason (optional).
  Returns 409 if already completed.

## Tests
- List returns filtered registrations
- Get returns registration details
- Enroll creates registration
- Enroll fails if prerequisites not met (409)
- Enroll fails if course full (409)
- Check eligibility returns reasons
- Complete sets grade
- Drop updates status
- Drop fails for completed
- Student cannot enroll others
