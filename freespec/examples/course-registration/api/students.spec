# students.spec

description:
The students API provides REST endpoints for managing student records. All endpoints require authentication and most require admin privileges.

GET /students lists all students. Supports optional query parameters for filtering by active status and pagination. Requires admin privileges. Returns 200 with an array of student data.

GET /students/:id retrieves a specific student. Students can access their own record; accessing others requires admin privileges. Returns 200 with student data, 403 if not authorized, or 404 if not found.

PATCH /students/:id updates a student's information. Students can update their own name and password; admins can update any field including active status. Returns 200 with updated data, 400 for validation errors, 403 if not authorized, or 404 if not found.

DELETE /students/:id deactivates a student. Requires admin privileges. This does not delete the student but marks them as inactive. Returns 204 on success, 403 if not admin, or 404 if not found.

Pagination uses page and limit query parameters with sensible defaults. The response includes pagination metadata.

exports:
- GET /students to list all students
- GET /students/:id to get a specific student
- PATCH /students/:id to update a student
- DELETE /students/:id to deactivate a student

tests:
- GET /students without authentication returns 401
- GET /students without admin privileges returns 403
- GET /students as admin returns 200 with student list
- GET /students respects pagination parameters
- GET /students/:id as the same student returns 200
- GET /students/:id as a different non-admin student returns 403
- GET /students/:id as admin returns 200
- GET /students/:id for non-existent student returns 404
- PATCH /students/:id can update own name
- PATCH /students/:id can update own password
- PATCH /students/:id cannot update own admin status
- PATCH /students/:id as admin can update any field
- PATCH /students/:id with invalid password returns 400
- DELETE /students/:id without admin returns 403
- DELETE /students/:id as admin returns 204
- DELETE /students/:id for non-existent student returns 404
