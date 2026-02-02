# registrations.spec

## Description
REST endpoints for course registration operations.
Base path: /registrations

## Endpoints

### GET /registrations
List registrations with filtering.

Query parameters:
- studentId: filter by student
- courseId: filter by course
- status: filter by status
- page: page number (default 1)
- limit: items per page (default 20, max 100)

Response: paginated list of registrations

### GET /registrations/:id
Get a single registration by ID.

Response: registration with student and course details, or 404

### POST /registrations
Enroll a student in a course.

Request body:
- studentId: required (or inferred from auth for students)
- courseId: required

Response: created registration with 201
Errors: 400 for validation, 409 for business rule violations

### POST /registrations/check-eligibility
Check if enrollment is allowed without making changes.

Request body:
- studentId: required
- courseId: required

Response: eligibility result with reasons

### PUT /registrations/:id/complete
Mark registration as completed. Requires admin or instructor role.

Request body:
- grade: required

Response: updated registration

### DELETE /registrations/:id
Drop enrollment (student-initiated withdrawal).

Request body:
- reason: optional

Response: 204 on success
Errors: 404 if not found, 409 if already completed

## Authentication
Students can only manage their own registrations.
Admins can manage any registration.
Instructors can complete registrations for their courses.

## Tests
- List returns filtered registrations
- List filters by student
- List filters by course
- Get returns registration details
- Get returns 404 for unknown ID
- Enroll creates registration
- Enroll fails if student not found (400)
- Enroll fails if course not found (400)
- Enroll fails if already enrolled (409)
- Enroll fails if prerequisites not met (409)
- Enroll fails if course full (409)
- Enroll fails if course not open (409)
- Check eligibility returns detailed result
- Complete sets grade and status
- Complete fails for non-confirmed registration
- Drop updates status to dropped
- Drop fails for completed registration
- Student cannot enroll others
- Student can drop own registration
- Student cannot complete registrations

## Mentions
@entities/registration
@services/enrollment
