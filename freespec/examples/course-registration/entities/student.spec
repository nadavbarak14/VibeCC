# student.spec

description:
A student is a user who can authenticate and register for courses. Each student has an email address which serves as their unique identifier and login credential. Email addresses are case-insensitive, so "John@Example.com" and "john@example.com" refer to the same student.

Students have a name for display purposes and a password for authentication. Passwords are never stored in plain text; only a secure hash is kept. The password must be at least 8 characters long.

Students can be active or inactive. Only active students can log in and register for courses. A student starts as active when created.

exports:
- Create a new student with email, name, and password
- Find a student by their email address
- Find a student by their unique ID
- Update a student's name or password
- Deactivate a student
- Reactivate a student
- List all students with optional filters for active status
- Verify a password matches for a given student

tests:
- Creating a student with valid email, name, and password succeeds
- Creating a student with an already-used email fails
- Creating a student with email differing only in case from existing email fails
- Creating a student with password shorter than 8 characters fails
- Creating a student with invalid email format fails
- Finding a student by email is case-insensitive
- Verifying correct password returns success
- Verifying incorrect password returns failure
- Inactive students cannot have their password verified
- Updating password to one shorter than 8 characters fails
- Deactivating an already inactive student succeeds without error
