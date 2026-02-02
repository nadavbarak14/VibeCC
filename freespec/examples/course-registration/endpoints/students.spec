# students.spec

description:
REST API endpoints for managing @entities/student records.

Base path: /students

Authentication: All endpoints require a valid Bearer token.

Authorization:
- Students can only view and update their own record
- Students cannot delete their own record
- Admins can view, update, and delete any student
- Only admins can list all students
- Anyone authenticated can create a student (self-registration)

Request/response format: JSON

Error responses follow standard format with appropriate HTTP status codes:
- 400: Invalid request data (validation errors)
- 401: Missing or invalid authentication
- 403: Authenticated but not authorized for this action
- 404: Student not found
- 409: Conflict (duplicate email, has active registrations)

api:
GET /students
List all students. Admin only. Supports query parameters:
- status: filter by status (active, inactive, suspended)
- search: partial match on name or email, case-insensitive
- page: page number starting from 1, defaults to 1
- limit: items per page, defaults to 20, max 100
Returns paginated list with items and total count.

GET /students/:id
Get a single student by id. Students can only access their own record,
admins can access any. Returns student object.
Returns 404 if not found, 403 if not authorized.

POST /students
Create a new student. Request body contains name and email.
Returns created student with 201 status.
Returns 400 if validation fails, 409 if email already exists.

PUT /students/:id
Update a student. Students can only update their own record (name and email
only), admins can update any record including status. Request body contains
fields to update. Returns updated student.
Returns 400 if validation fails, 403 if not authorized, 404 if not found,
409 if email already exists.

DELETE /students/:id
Delete (deactivate) a student. Admin only. Sets status to inactive.
Returns 204 on success.
Returns 403 if not admin, 404 if not found, 409 if student has active
registrations (confirmed or pending).

tests:
GET /students returns paginated list for admin
GET /students filters by status
GET /students searches by name
GET /students searches by email
GET /students search is case-insensitive
GET /students pagination works correctly
GET /students returns 401 without auth
GET /students returns 403 for non-admin
GET /students/:id returns student for owner
GET /students/:id returns student for admin
GET /students/:id returns 401 without auth
GET /students/:id returns 403 for other student
GET /students/:id returns 404 for unknown id
POST /students creates student with valid data
POST /students returns 201 with created student
POST /students returns 400 for missing name
POST /students returns 400 for missing email
POST /students returns 400 for invalid email
POST /students returns 401 without auth
POST /students returns 409 for duplicate email
PUT /students/:id updates name for owner
PUT /students/:id updates email for owner
PUT /students/:id owner cannot update status
PUT /students/:id admin can update status
PUT /students/:id returns 400 for invalid email
PUT /students/:id returns 401 without auth
PUT /students/:id returns 403 for other student
PUT /students/:id returns 404 for unknown id
PUT /students/:id returns 409 for duplicate email
DELETE /students/:id deactivates student for admin
DELETE /students/:id returns 204 on success
DELETE /students/:id returns 401 without auth
DELETE /students/:id returns 403 for non-admin
DELETE /students/:id returns 403 for self-delete
DELETE /students/:id returns 404 for unknown id
DELETE /students/:id returns 409 with active registrations
