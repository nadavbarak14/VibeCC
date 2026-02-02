# registrations.spec

description:
The registrations API provides REST endpoints for course registration, using @services/enrollment for the business logic.

POST /registrations enrolls the authenticated student in a course. The request body contains the course ID. Returns 201 with the registration data, 400 if prerequisites not met or already enrolled, 404 if course not found, or 409 if course is full or closed.

GET /registrations lists the authenticated student's registrations. Supports filtering by status with a query parameter. Returns 200 with an array of registration data including course information.

GET /registrations/:id retrieves a specific registration. Students can only access their own registrations; admins can access any. Returns 200 with registration data, 403 if not authorized, or 404 if not found.

DELETE /registrations/:id drops the student from the course. Students can only drop their own active enrollments; admins can drop any. Returns 204 on success, 400 if already completed or dropped, 403 if not authorized, or 404 if not found.

PATCH /registrations/:id updates registration status. Only admins can use this endpoint, typically to mark a registration as completed. Returns 200 with updated data, 400 for invalid status transition, 403 if not admin, or 404 if not found.

GET /students/:id/registrations lists registrations for a specific student. Requires admin privileges unless accessing own registrations. Returns 200 with registration data.

exports:
- POST /registrations to enroll in a course
- GET /registrations to list own registrations
- GET /registrations/:id to get a specific registration
- DELETE /registrations/:id to drop a course
- PATCH /registrations/:id to update registration status
- GET /students/:id/registrations to list a student's registrations

tests:
- POST /registrations without authentication returns 401
- POST /registrations for open course with seats returns 201
- POST /registrations for closed course returns 409
- POST /registrations for full course returns 409
- POST /registrations without prerequisites met returns 400
- POST /registrations for already enrolled course returns 400
- GET /registrations returns own registrations
- GET /registrations can filter by status
- GET /registrations/:id for own registration returns 200
- GET /registrations/:id for other's registration returns 403
- GET /registrations/:id as admin for any registration returns 200
- DELETE /registrations/:id for own enrolled course returns 204
- DELETE /registrations/:id for completed course returns 400
- DELETE /registrations/:id for other's registration returns 403
- DELETE /registrations/:id frees a seat in the course
- PATCH /registrations/:id without admin returns 403
- PATCH /registrations/:id as admin marking completed returns 200
- GET /students/:id/registrations for own returns 200
- GET /students/:id/registrations for other without admin returns 403
