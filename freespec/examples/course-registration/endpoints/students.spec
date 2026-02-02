# students.spec

## Description
REST endpoints for @entities/student management.
Base path: /students

All endpoints require authentication.
Students can only access their own record.
Admins can access all.

## API
- GET /students -> list[Student]
  List students. Query: status, search, page, limit.

- GET /students/:id -> Student
  Get student by ID. Returns 404 if not found.

- POST /students -> Student
  Create student. Body: email, name. Returns 201.

- PUT /students/:id -> Student
  Update student. Body: email, name, status.

- DELETE /students/:id -> void
  Soft delete. Returns 204, or 409 if has active enrollments.

## Tests
- List returns paginated students
- List filters by status
- Get returns student
- Get returns 404 for unknown
- Create with valid data returns 201
- Create with duplicate email returns 409
- Update changes fields
- Delete sets inactive
- Delete with enrollments returns 409
- Unauthenticated returns 401
- Student cannot view others
