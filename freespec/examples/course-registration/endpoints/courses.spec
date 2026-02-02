# courses.spec

description:
REST API endpoints for managing @entities/course records.

Base path: /courses

Authentication: Read operations (GET) are public. Write operations require
authentication with admin role.

Authorization:
- Anyone can list and view courses (public catalog)
- Only admins can create, update, or delete courses
- Only admins can view course roster
- Archived courses are hidden from public listing but accessible by direct id

Request/response format: JSON

Error responses follow standard format with appropriate HTTP status codes:
- 400: Invalid request data (validation errors)
- 401: Missing or invalid authentication (for protected endpoints)
- 403: Authenticated but not admin
- 404: Course not found
- 409: Conflict (duplicate code, has active registrations, invalid status transition)

api:
GET /courses
List all courses. Public endpoint. Supports query parameters:
- status: filter by status (draft, open, closed) - archived excluded by default
- search: partial match on code or title, case-insensitive
- page: page number starting from 1, defaults to 1
- limit: items per page, defaults to 20, max 100
Returns paginated list with items and total count. Each course includes
current enrollment count.

GET /courses/:id
Get a single course by id. Public endpoint. Returns course object with
current enrollment count and remaining capacity.
Returns 404 if not found.

GET /courses/:id/prerequisites
Get prerequisite courses for a course. Public endpoint. Returns list of
course objects that are prerequisites for this course.
Returns 404 if course not found.

GET /courses/:id/roster
Get enrolled students for a course. Admin only. Returns list of registrations
with student details. Supports query parameter:
- status: filter by registration status, defaults to confirmed only
Returns 401 without auth, 403 for non-admin, 404 if course not found.

POST /courses
Create a new course. Admin only. Request body contains code, title, capacity,
and optional prerequisites (list of course ids).
Returns created course with 201 status.
Returns 400 if validation fails, 401 without auth, 403 for non-admin,
409 if code already exists.

PUT /courses/:id
Update a course. Admin only. Request body contains fields to update.
Cannot reduce capacity below current enrollment count.
Returns updated course.
Returns 400 if validation fails, 401 without auth, 403 for non-admin,
404 if not found, 409 if code exists or capacity too low.

PUT /courses/:id/open
Open a course for registration. Admin only. Sets status to open.
Only works for courses with status draft or closed.
Returns updated course.
Returns 401 without auth, 403 for non-admin, 404 if not found,
409 if invalid status transition.

PUT /courses/:id/close
Close a course to registration. Admin only. Sets status to closed.
Only works for courses with status open.
Returns updated course.
Returns 401 without auth, 403 for non-admin, 404 if not found,
409 if invalid status transition.

DELETE /courses/:id
Archive a course. Admin only. Sets status to archived.
Returns 204 on success.
Returns 401 without auth, 403 for non-admin, 404 if not found,
409 if course has active registrations.

tests:
GET /courses returns paginated list
GET /courses excludes archived courses
GET /courses filters by status
GET /courses searches by code
GET /courses searches by title
GET /courses includes enrollment count
GET /courses works without auth
GET /courses/:id returns course with capacity info
GET /courses/:id returns 404 for unknown
GET /courses/:id works without auth
GET /courses/:id/prerequisites returns prerequisite courses
GET /courses/:id/prerequisites returns empty list for none
GET /courses/:id/prerequisites returns 404 for unknown course
GET /courses/:id/roster returns enrolled students for admin
GET /courses/:id/roster filters by status
GET /courses/:id/roster returns 401 without auth
GET /courses/:id/roster returns 403 for non-admin
GET /courses/:id/roster returns 404 for unknown course
POST /courses creates course with valid data
POST /courses returns 201 with created course
POST /courses returns 400 for missing code
POST /courses returns 400 for invalid capacity
POST /courses returns 400 for invalid prerequisite
POST /courses returns 401 without auth
POST /courses returns 403 for non-admin
POST /courses returns 409 for duplicate code
PUT /courses/:id updates course fields
PUT /courses/:id returns 400 for capacity below enrollment
PUT /courses/:id returns 401 without auth
PUT /courses/:id returns 403 for non-admin
PUT /courses/:id returns 404 for unknown
PUT /courses/:id/open sets status to open
PUT /courses/:id/open works for draft course
PUT /courses/:id/open works for closed course
PUT /courses/:id/open returns 409 for open course
PUT /courses/:id/open returns 409 for archived course
PUT /courses/:id/close sets status to closed
PUT /courses/:id/close returns 409 for draft course
PUT /courses/:id/close returns 409 for archived course
DELETE /courses/:id archives course
DELETE /courses/:id returns 204 on success
DELETE /courses/:id returns 401 without auth
DELETE /courses/:id returns 403 for non-admin
DELETE /courses/:id returns 404 for unknown
DELETE /courses/:id returns 409 with active registrations
