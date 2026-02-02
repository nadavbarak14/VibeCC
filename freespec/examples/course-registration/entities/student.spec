# student.spec

description:
A student who can log in and register for courses. Has an id, email, password hash, name, and status. Email must be unique and is case-insensitive. Passwords are never stored in plain text.

Status is active, inactive, or suspended, defaulting to active. Only active students can log in and register for courses. Inactive or suspended students keep their existing @entities/registration records but cannot create new ones.

Deleting a student sets status to inactive rather than removing the record. A student cannot be deleted if they have any in-progress registrations.

exports:
Create a student with name, email, and password
Get a student by id
Find a student by email
Update a student's name or email
Change a student's password, requiring the current password
Delete a student (soft delete to inactive)
List students with optional status filter and pagination
Verify a password against the stored hash

tests:
Create with valid data succeeds
Create with duplicate email fails
Create with duplicate email different case fails
Create with invalid email format fails
Create with weak password fails
Get returns student by id
Get returns nothing for unknown id
Find by email is case-insensitive
Update name succeeds
Update email to new unique value succeeds
Update email to duplicate fails
Change password with correct current password succeeds
Change password with wrong current password fails
Delete sets status to inactive
Delete with in-progress registration fails
List returns all active students by default
List filters by status
Verify password returns true for correct password
Verify password returns false for wrong password
