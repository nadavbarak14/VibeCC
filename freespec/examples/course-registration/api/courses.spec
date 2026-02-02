# courses.spec

description:
REST API endpoints for course management. Uses @entities/course for data access and @services/enrollment for registration operations.

Course listing is public and shows only open courses by default. Course details include prerequisites. Creating, updating, and deleting courses requires admin privileges.

The enrollment count and capacity are included in responses so students can see available spots. Prerequisites are returned as a list of course summaries.

exports:
GET /courses - list courses with optional filters
GET /courses/:id - get course details
POST /courses - create a course (admin only)
PUT /courses/:id - update a course (admin only)
DELETE /courses/:id - delete a course (admin only)
POST /courses/:id/prerequisites - add prerequisite (admin only)
DELETE /courses/:id/prerequisites/:prereqId - remove prerequisite (admin only)
GET /courses/:id/students - list enrolled students (admin only)

tests:
GET /courses returns open courses by default
GET /courses with status filter returns matching courses
GET /courses includes enrollment count and capacity
GET /courses supports pagination
GET /courses/:id returns course with prerequisites
GET /courses/:id for unknown id returns 404
POST /courses without auth returns 401
POST /courses as non-admin returns 403
POST /courses as admin creates course
POST /courses with duplicate code returns 409
POST /courses with invalid data returns 422
PUT /courses/:id updates course
PUT /courses/:id reducing capacity below enrollment returns 409
DELETE /courses/:id deletes draft course
DELETE /courses/:id for non-draft returns 409
DELETE /courses/:id with registrations returns 409
POST /courses/:id/prerequisites adds prerequisite
POST /courses/:id/prerequisites creating cycle returns 409
DELETE /courses/:id/prerequisites/:prereqId removes prerequisite
GET /courses/:id/students returns enrolled students
GET /courses/:id/students as non-admin returns 403
