# student.spec

description:
A student who can enroll in courses.

Has a unique email, name, and status (active, inactive, or suspended).
Tracks when created and last updated.

api:
Create a new student with name and email. Email must be unique.
Get a student by their ID.
Find a student by their email.
Update a student's information.
Delete a student (soft delete - sets inactive). Cannot delete if they have active @entities/registration records.
List students with filtering and pagination.

tests:
Create with valid data succeeds
Duplicate email rejected
Invalid email format rejected
Get returns student by ID
Get returns nothing for unknown ID
Update changes fields
Delete sets status inactive
Delete fails with active registrations
