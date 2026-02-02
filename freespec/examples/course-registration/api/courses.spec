# courses.spec

description:
The courses API provides REST endpoints for managing @entities/course records. Reading courses is available to all authenticated users via @services/auth, but modifications require admin privileges.

GET /courses lists all courses. Supports optional query parameters for filtering by open status and pagination. Returns 200 with an array of course data including current enrollment count and available seats.

GET /courses/:id retrieves a specific course with full details including prerequisites. Returns 200 with course data or 404 if not found.

POST /courses creates a new course. Requires admin privileges. The request body contains code, title, capacity, and optional description. Returns 201 with the course data, 400 for validation errors, 403 if not admin, or 409 if the code is already taken.

PATCH /courses/:id updates a course. Requires admin privileges. Can update title, description, capacity, and status. Returns 200 with updated data, 400 if reducing capacity below enrollment, 403 if not admin, or 404 if not found.

DELETE /courses/:id closes a course to new registrations. Requires admin privileges. Does not delete the course or affect existing enrollments. Returns 204 on success.

POST /courses/:id/prerequisites adds a prerequisite. Requires admin privileges. Request body contains the prerequisite course ID. Returns 204 on success, 400 if it would create a cycle, or 404 if either course not found.

DELETE /courses/:id/prerequisites/:prereqId removes a prerequisite. Requires admin privileges. Returns 204 on success.

exports:
- GET /courses to list all courses
- GET /courses/:id to get a specific course
- POST /courses to create a new course
- PATCH /courses/:id to update a course
- DELETE /courses/:id to close a course
- POST /courses/:id/prerequisites to add a prerequisite
- DELETE /courses/:id/prerequisites/:prereqId to remove a prerequisite

tests:
- GET /courses without authentication returns 401
- GET /courses returns 200 with course list and enrollment info
- GET /courses can filter by open status
- GET /courses/:id returns 200 with full course details
- GET /courses/:id for non-existent course returns 404
- POST /courses without admin returns 403
- POST /courses with valid data returns 201
- POST /courses with existing code returns 409
- POST /courses with invalid capacity returns 400
- PATCH /courses/:id without admin returns 403
- PATCH /courses/:id as admin returns 200
- PATCH /courses/:id reducing capacity below enrollment returns 400
- DELETE /courses/:id without admin returns 403
- DELETE /courses/:id as admin closes course and returns 204
- POST /courses/:id/prerequisites adding valid prerequisite returns 204
- POST /courses/:id/prerequisites creating cycle returns 400
- DELETE /courses/:id/prerequisites/:prereqId removes prerequisite
