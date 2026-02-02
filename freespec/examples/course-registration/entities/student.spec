# student.spec

## Description
Represents a student who can enroll in courses.

## Properties
- id: unique identifier (generated)
- email: unique email address
- name: full name
- status: active | inactive | suspended
- createdAt: timestamp
- updatedAt: timestamp

## Constraints
- Email must be unique across all students
- Email must be valid format
- Name cannot be empty
- Status defaults to "active" on creation

## Tests
- Valid student has all required fields
- Two students cannot share email
- Invalid email format rejected
- Empty name rejected
