# students.spec

## Description
REST endpoints for student management.
Base path: /students

## Endpoints

### GET /students
List all students with optional filtering and pagination.

Query parameters:
- status: filter by status (active, inactive, suspended)
- search: search by name or email
- page: page number (default 1)
- limit: items per page (default 20, max 100)

Response: paginated list of students

### GET /students/:id
Get a single student by ID.

Response: student object or 404

### POST /students
Create a new student.

Request body:
- email: required
- name: required

Response: created student with 201

### PUT /students/:id
Update an existing student.

Request body (all optional):
- email
- name
- status

Response: updated student or 404

### DELETE /students/:id
Soft delete a student (sets status to inactive).

Response: 204 on success, 404 if not found,
409 if student has active enrollments

## Authentication
All endpoints require authentication.
Only admins can list all students.
Students can only view/update their own record.

## Tests
- List returns paginated students
- List filters by status
- List searches by name
- Get returns student by ID
- Get returns 404 for unknown ID
- Create with valid data returns 201
- Create with duplicate email returns 409
- Create with invalid email returns 400
- Update changes fields
- Update with duplicate email returns 409
- Delete sets status to inactive
- Delete with active enrollments returns 409
- Unauthenticated request returns 401
- Student cannot view other students

## Mentions
@entities/student
