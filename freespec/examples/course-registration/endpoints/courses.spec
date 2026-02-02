# courses.spec

## Description
REST endpoints for course management.
Base path: /courses

## Endpoints

### GET /courses
List all courses with optional filtering and pagination.

Query parameters:
- status: filter by status (draft, open, closed, archived)
- search: search by code or title
- page: page number (default 1)
- limit: items per page (default 20, max 100)

Response: paginated list of courses

### GET /courses/:id
Get a single course by ID.

Response: course object with current enrollment count, or 404

### GET /courses/:id/prerequisites
Get prerequisite courses for a course.

Response: list of prerequisite courses

### GET /courses/:id/roster
Get enrolled students for a course.

Response: list of registrations with student details
Requires admin or instructor role.

### POST /courses
Create a new course. Requires admin role.

Request body:
- code: required
- title: required
- capacity: required
- prerequisites: optional list of course IDs

Response: created course with 201

### PUT /courses/:id
Update an existing course. Requires admin role.

Request body (all optional):
- code
- title
- capacity (cannot reduce below current enrollment)
- prerequisites
- status

Response: updated course or 404

### DELETE /courses/:id
Archive a course (sets status to archived). Requires admin role.

Response: 204 on success, 404 if not found,
409 if course has active enrollments

## Authentication
GET endpoints are public.
Modifying endpoints require admin role.
Roster requires admin or instructor role.

## Tests
- List returns paginated courses
- List filters by status
- List searches by code
- Get returns course with enrollment count
- Get returns 404 for unknown ID
- Prerequisites returns correct courses
- Roster returns enrolled students
- Roster requires authorization
- Create with valid data returns 201
- Create with duplicate code returns 409
- Create with invalid prerequisites returns 400
- Update changes fields
- Update cannot reduce capacity below enrollment
- Delete archives course
- Delete with active enrollments returns 409
- Non-admin cannot create courses

## Mentions
@entities/course
@entities/registration
