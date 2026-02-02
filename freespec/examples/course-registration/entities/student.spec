# student.spec

## Description
A student who can enroll in courses.

Properties: id, email (unique), name, status (active/inactive/suspended),
createdAt, updatedAt.

## API
- create(name, email) -> Student
  Creates student. Email must be unique.

- get(id) -> Student | null
  Returns student or null if not found.

- getByEmail(email) -> Student | null
  Finds student by email.

- update(id, updates) -> Student
  Updates student fields.

- delete(id) -> bool
  Soft-deletes (sets inactive). Fails if has active @entities/registration.

- list(filters, pagination) -> list[Student]
  Returns filtered, paginated students.

## Tests
- Create with valid data succeeds
- Duplicate email rejected
- Invalid email format rejected
- Get returns student by ID
- Get returns null for unknown ID
- Update changes fields
- Delete sets status inactive
- Delete fails with active registrations
