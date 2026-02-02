# students.spec

description:
REST API endpoints for student management. Uses @entities/student for data access. Most endpoints require authentication via @services/auth.

Students can view and update their own profile. Listing all students and viewing other students' profiles requires admin privileges. Password is never included in responses.

Pagination uses cursor-based pagination with a default page size of 20 and maximum of 100. The response includes a next cursor if more results exist.

exports:
GET /students - list students (admin only)
GET /students/:id - get a student by id
PUT /students/:id - update a student
DELETE /students/:id - soft delete a student
PUT /students/:id/password - change password

tests:
GET /students without auth returns 401
GET /students as non-admin returns 403
GET /students as admin returns paginated list
GET /students with status filter works
GET /students/:id returns student without password
GET /students/:id for own profile succeeds
GET /students/:id for other profile as non-admin returns 403
GET /students/:id for unknown id returns 404
PUT /students/:id updates name
PUT /students/:id updates email
PUT /students/:id for other user as non-admin returns 403
PUT /students/:id with duplicate email returns 409
DELETE /students/:id soft deletes
DELETE /students/:id for other user as non-admin returns 403
DELETE /students/:id with active registrations returns 409
PUT /students/:id/password with correct current password succeeds
PUT /students/:id/password with wrong current password returns 401
PUT /students/:id/password for other user returns 403
