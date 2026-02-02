# registrations.spec

description:
REST API endpoints for course registration. Uses @services/enrollment for business logic. All endpoints require authentication.

Students can enroll themselves in courses and view their own registrations. Viewing all registrations or other students' registrations requires admin privileges. Completing a registration with a grade is admin only.

The eligibility endpoint allows checking if enrollment would succeed before attempting it, returning a list of reasons if not eligible.

exports:
POST /registrations - enroll current user in a course
GET /registrations - list current user's registrations
GET /registrations/:id - get a registration by id
DELETE /registrations/:id - drop a registration
GET /courses/:id/eligibility - check if current user can enroll
POST /registrations/:id/complete - complete with grade (admin only)

tests:
POST /registrations without auth returns 401
POST /registrations enrolls current user
POST /registrations for closed course returns 409
POST /registrations for full course returns 409
POST /registrations when already enrolled returns 409
POST /registrations with missing prerequisites returns 409 with reasons
GET /registrations returns current user's registrations
GET /registrations with status filter works
GET /registrations/:id for own registration succeeds
GET /registrations/:id for other user as non-admin returns 403
GET /registrations/:id for unknown id returns 404
DELETE /registrations/:id drops registration
DELETE /registrations/:id for completed returns 409
DELETE /registrations/:id for other user returns 403
GET /courses/:id/eligibility returns empty reasons when eligible
GET /courses/:id/eligibility returns all failure reasons
GET /courses/:id/eligibility for unknown course returns 404
POST /registrations/:id/complete as admin sets grade
POST /registrations/:id/complete as non-admin returns 403
POST /registrations/:id/complete with invalid grade returns 422
POST /registrations/:id/complete for non-confirmed returns 409
