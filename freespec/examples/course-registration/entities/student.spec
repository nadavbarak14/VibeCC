# student.spec

description:
A student who can enroll in courses in the registration system.

Properties:
- id: unique identifier, generated on creation, immutable
- email: student's email address, must be unique across all students
- name: student's full name, cannot be empty
- status: one of active, inactive, suspended
- createdAt: timestamp when student was created
- updatedAt: timestamp when student was last modified

Constraints:
- Email must be valid email format (contains @, valid domain structure)
- Email uniqueness is case-insensitive (Bob@Example.com = bob@example.com)
- Name must be non-empty after trimming whitespace
- Status defaults to "active" when created
- Cannot change id after creation
- updatedAt automatically updates on any modification

A student with status "inactive" or "suspended" cannot enroll in new courses
but retains their existing @entities/registration records.

Deleting a student is a soft delete - sets status to inactive. Cannot delete
if student has any registrations with status "confirmed" or "pending".

api:
Create a new student given name and email. Validates email format and
uniqueness. Sets status to active, generates id, sets timestamps.
Returns the created student. Fails if email invalid or duplicate.

Get a student by their id. Returns the student if found, nothing if not found.

Find a student by email address. Case-insensitive match. Returns the student
if found, nothing if not found.

Update a student given their id and fields to change. Can update name, email,
or status. Validates email if changed. Updates the updatedAt timestamp.
Returns updated student. Fails if student not found or validation fails.

Delete a student given their id. Soft delete - sets status to inactive.
Fails if student has active registrations (confirmed or pending status).
Returns success/failure.

List students with optional filters and pagination. Can filter by status,
search by name or email (partial match, case-insensitive). Pagination via
page number and page size. Returns list of students and total count.

tests:
Create with valid name and email succeeds
Create generates unique id
Create sets status to active
Create sets createdAt and updatedAt
Create with empty name fails
Create with whitespace-only name fails
Create with invalid email format fails
Create with duplicate email fails
Create with duplicate email different case fails
Get with valid id returns student
Get with unknown id returns nothing
Find by email returns student
Find by email is case-insensitive
Find by unknown email returns nothing
Update name succeeds
Update email succeeds
Update email to duplicate fails
Update status succeeds
Update unknown student fails
Update changes updatedAt timestamp
Delete sets status to inactive
Delete with confirmed registration fails
Delete with pending registration fails
Delete with only completed registrations succeeds
Delete with only dropped registrations succeeds
Delete unknown student fails
List returns all students
List filters by status
List searches by partial name
List searches by partial email
List search is case-insensitive
List pagination returns correct page
List returns total count
