# courses.spec

## Description
REST endpoints for @entities/course management.
Base path: /courses

GET endpoints are public.
Modifications require admin role.

## API
- GET /courses -> list[Course]
  List courses. Query: status, search, page, limit.

- GET /courses/:id -> Course
  Get course with current enrollment count.

- GET /courses/:id/prerequisites -> list[Course]
  Get prerequisite courses.

- GET /courses/:id/roster -> list[Registration]
  Get enrolled students. Requires admin.

- POST /courses -> Course
  Create course. Body: code, title, capacity, prerequisites. Requires admin.

- PUT /courses/:id -> Course
  Update course. Cannot reduce capacity below enrollment. Requires admin.

- DELETE /courses/:id -> void
  Archive course. Returns 409 if has active enrollments. Requires admin.

## Tests
- List returns paginated courses
- List filters by status
- Get returns course with enrollment count
- Get returns 404 for unknown
- Prerequisites returns correct courses
- Roster returns enrollments
- Create with valid data returns 201
- Create with duplicate code returns 409
- Update changes fields
- Cannot reduce capacity below enrollment
- Delete archives course
- Non-admin cannot modify
