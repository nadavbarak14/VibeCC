# enrollment-api.spec

description:
A REST API that exposes the course enrollment system over HTTP. It provides endpoints for managing @entities/student records, @entities/course records, and processing enrollments through @services/enrollment-service. All endpoints return JSON responses with appropriate HTTP status codes. Successful operations return the relevant data, while failures return error objects with a code and human-readable message. The API follows REST conventions with resources identified by URLs and operations mapped to HTTP methods.

api:
Create a student by posting to the students collection. Get a student by their identifier. Update a student's information. List all students with optional status filter. Create a course by posting to the courses collection. Get a course by its code. Update a course's information. List all courses with optional status filter. Enroll a student in a course by posting to the enrollments collection. Withdraw a student from a course by updating the enrollment. Get all enrollments for a student. Get all enrollments for a course. Check enrollment eligibility for a student and course combination.

tests:
POST to students with valid data returns 201 and the created student
POST to students with duplicate email returns 409 conflict
GET student by id returns 200 and the student data
GET nonexistent student returns 404
PATCH student with valid data returns 200 and updated student
GET students returns 200 and list of all students
GET students with status filter returns only matching students
POST to courses with valid data returns 201 and the created course
POST to courses with duplicate code returns 409 conflict
GET course by code returns 200 and the course data
GET nonexistent course returns 404
PATCH course with valid data returns 200 and updated course
GET courses returns 200 and list of all courses
POST to enrollments with valid student and course returns 201
POST to enrollments with ineligible student returns 400 with reason
POST to enrollments with unavailable course returns 400 with reason
POST to enrollments when already enrolled returns 409 conflict
DELETE enrollment returns 200 and marks as withdrawn
GET enrollments for student returns their enrollment list
GET enrollments for course returns enrolled students
GET enrollment eligibility returns status and reason if ineligible
Invalid JSON in request body returns 400 bad request
Missing required fields return 400 with field-specific errors
