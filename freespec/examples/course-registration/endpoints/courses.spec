# courses.spec

description:
REST endpoints for @entities/course management.
Base path: /courses

GET endpoints are public. Modifications require admin role.

api:
GET /courses - List courses with optional filtering by status, search, pagination.
GET /courses/:id - Get a course with its current enrollment count.
GET /courses/:id/prerequisites - Get prerequisite courses.
GET /courses/:id/roster - Get enrolled students. Requires admin.
POST /courses - Create a course with code, title, capacity, prerequisites. Requires admin.
PUT /courses/:id - Update a course. Cannot reduce capacity below enrollment. Requires admin.
DELETE /courses/:id - Archive a course. Returns 409 if has active enrollments. Requires admin.

tests:
List returns paginated courses
List filters by status
Get returns course with enrollment count
Get returns 404 for unknown
Prerequisites returns correct courses
Roster returns enrollments
Create with valid data returns 201
Create with duplicate code returns 409
Update changes fields
Cannot reduce capacity below enrollment
Delete archives course
Non-admin cannot modify
