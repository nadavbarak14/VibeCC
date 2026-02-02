# students.spec

description:
REST endpoints for @entities/student management.
Base path: /students

All endpoints require authentication.
Students can only access their own record. Admins can access all.

api:
GET /students - List students with optional filtering by status, search, pagination.
GET /students/:id - Get a single student. Returns 404 if not found.
POST /students - Create a new student with email and name. Returns 201.
PUT /students/:id - Update a student's email, name, or status.
DELETE /students/:id - Soft delete. Returns 204, or 409 if has active enrollments.

tests:
List returns paginated students
List filters by status
Get returns student
Get returns 404 for unknown
Create with valid data returns 201
Create with duplicate email returns 409
Update changes fields
Delete sets inactive
Delete with enrollments returns 409
Unauthenticated returns 401
Student cannot view others
