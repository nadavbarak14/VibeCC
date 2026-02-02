# registrations.spec

description:
REST API endpoints for enrollment operations.

Base path: /registrations

Uses @services/enrollment for all business logic. This ensures consistent
rule enforcement regardless of how registrations are created.

Authentication: All endpoints require a valid Bearer token.

Authorization:
- Students can view their own registrations
- Students can create registrations for themselves only
- Students can drop their own registrations
- Admins can view all registrations
- Admins can create registrations for any student
- Admins can drop or complete any registration

Request/response format: JSON

Error responses follow standard format with appropriate HTTP status codes:
- 400: Invalid request data (validation errors)
- 401: Missing or invalid authentication
- 403: Authenticated but not authorized for this action
- 404: Registration, student, or course not found
- 409: Business rule violation (already enrolled, prerequisites not met,
       course full, invalid status transition)

api:
GET /registrations
List registrations. Students see only their own, admins see all.
Supports query parameters:
- studentId: filter by student (admin only, ignored for students)
- courseId: filter by course
- status: filter by status (pending, confirmed, dropped, completed)
- page: page number starting from 1, defaults to 1
- limit: items per page, defaults to 20, max 100
Returns paginated list with items and total count. Each registration includes
student and course summary.

GET /registrations/:id
Get a single registration by id. Students can only access their own, admins
can access any. Returns registration with full student and course details.
Returns 403 if not authorized, 404 if not found.

POST /registrations
Enroll a student in a course. Request body contains studentId and courseId.
Students can only enroll themselves (studentId must match authenticated user
unless admin). Uses @services/enrollment.enroll which enforces all business rules.
Returns created registration with 201 status.
Returns 400 for missing fields, 403 if enrolling another student, 404 if
student or course not found, 409 for any business rule violation (includes
specific reason in error response).

POST /registrations/check-eligibility
Check if enrollment is allowed without creating registration. Request body
contains studentId and courseId. Uses @services/enrollment.checkEligibility.
Students can only check for themselves, admins can check any.
Returns eligibility result with eligible boolean and reasons array.
Returns 403 if checking for another student.

PUT /registrations/:id/drop
Drop an enrollment. Optional request body can contain reason. Students can
only drop their own, admins can drop any. Uses @services/enrollment.drop.
Returns updated registration.
Returns 403 if not authorized, 404 if not found, 409 if cannot be dropped
(already completed or dropped).

PUT /registrations/:id/complete
Complete an enrollment with a grade. Admin only. Request body contains grade.
Uses @services/enrollment.complete.
Returns updated registration.
Returns 400 for missing or invalid grade, 401 without auth, 403 for non-admin,
404 if not found, 409 if cannot be completed (not confirmed).

tests:
GET /registrations returns student's own registrations
GET /registrations returns all for admin
GET /registrations filters by courseId
GET /registrations filters by status
GET /registrations pagination works
GET /registrations returns 401 without auth
GET /registrations ignores studentId filter for non-admin
GET /registrations/:id returns registration for owner
GET /registrations/:id returns registration for admin
GET /registrations/:id includes student and course details
GET /registrations/:id returns 401 without auth
GET /registrations/:id returns 403 for other student's registration
GET /registrations/:id returns 404 for unknown
POST /registrations creates registration for self
POST /registrations returns 201 with registration
POST /registrations includes student and course in response
POST /registrations admin can enroll any student
POST /registrations returns 400 for missing studentId
POST /registrations returns 400 for missing courseId
POST /registrations returns 401 without auth
POST /registrations returns 403 when enrolling another student
POST /registrations returns 404 for unknown student
POST /registrations returns 404 for unknown course
POST /registrations returns 409 when already enrolled
POST /registrations returns 409 when prerequisites not met
POST /registrations returns 409 when course full
POST /registrations returns 409 when course not open
POST /registrations 409 includes specific reason
POST /registrations/check-eligibility returns eligible true
POST /registrations/check-eligibility returns reasons when not eligible
POST /registrations/check-eligibility does not create registration
POST /registrations/check-eligibility returns 401 without auth
POST /registrations/check-eligibility returns 403 for other student
PUT /registrations/:id/drop drops own registration
PUT /registrations/:id/drop admin drops any registration
PUT /registrations/:id/drop returns updated registration
PUT /registrations/:id/drop returns 401 without auth
PUT /registrations/:id/drop returns 403 for other student
PUT /registrations/:id/drop returns 404 for unknown
PUT /registrations/:id/drop returns 409 for completed registration
PUT /registrations/:id/drop returns 409 for already dropped
PUT /registrations/:id/complete sets grade and status
PUT /registrations/:id/complete returns 400 for missing grade
PUT /registrations/:id/complete returns 400 for invalid grade
PUT /registrations/:id/complete returns 401 without auth
PUT /registrations/:id/complete returns 403 for non-admin
PUT /registrations/:id/complete returns 404 for unknown
PUT /registrations/:id/complete returns 409 for not confirmed
