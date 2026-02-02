# course.spec

description:
A course available for student enrollment in the registration system.

Properties:
- id: unique identifier, generated on creation, immutable
- code: course code like "CS101", must be unique across all courses
- title: course title, cannot be empty
- capacity: maximum number of students that can enroll, must be positive
- prerequisites: list of course ids that must be completed before enrolling
- status: one of draft, open, closed, archived
- createdAt: timestamp when course was created
- updatedAt: timestamp when course was last modified

Constraints:
- Code must be non-empty, unique, case-insensitive (CS101 = cs101)
- Title must be non-empty after trimming whitespace
- Capacity must be a positive integer (at least 1)
- Prerequisites must reference existing courses
- Prerequisites cannot create circular chains (A requires B requires A)
- Status defaults to "draft" when created
- Cannot change id after creation
- updatedAt automatically updates on any modification

Status meanings:
- draft: course is being set up, not visible to students
- open: course accepts new enrollments
- closed: course is full or registration period ended, no new enrollments
- archived: course is historical, not visible to students

A @entities/student can only enroll in courses with status "open".
Prerequisites are checked against @entities/registration with status "completed".

Deleting a course sets status to "archived". Cannot delete if any registrations
exist with status "confirmed" or "pending".

api:
Create a course given code, title, capacity, and optional prerequisites.
Validates all fields and prerequisite references. Checks for circular
prerequisites. Sets status to draft, generates id, sets timestamps.
Returns the created course. Fails if validation fails.

Get a course by id. Returns course if found, nothing if not found.

Update a course given id and fields to change. Can update code, title,
capacity, prerequisites, or status. Cannot reduce capacity below current
enrollment count. Validates prerequisites if changed.
Returns updated course. Fails if not found or validation fails.

Delete a course (archive it) given id. Sets status to archived.
Fails if course has active registrations (confirmed or pending).
Returns success/failure.

List courses with optional filters and pagination. Can filter by status,
search by code or title (partial match, case-insensitive). Pagination via
page number and page size. Returns list of courses and total count.

Get prerequisites for a course given id. Returns list of prerequisite courses
with their full details. Returns empty list if no prerequisites.
Fails if course not found.

Check capacity for a course given id. Returns current enrollment count
(registrations with confirmed status) and remaining slots.
Fails if course not found.

Open a course for registration given id. Sets status to "open".
Can only open courses with status "draft" or "closed".
Fails if course not found or in wrong status.

Close a course to registration given id. Sets status to "closed".
Can only close courses with status "open".
Fails if course not found or in wrong status.

tests:
Create with valid data succeeds
Create generates unique id
Create sets status to draft
Create sets timestamps
Create with empty code fails
Create with duplicate code fails
Create with duplicate code different case fails
Create with empty title fails
Create with zero capacity fails
Create with negative capacity fails
Create with valid prerequisites succeeds
Create with nonexistent prerequisite fails
Create with circular prerequisite fails
Create with self as prerequisite fails
Get with valid id returns course
Get with unknown id returns nothing
Update code succeeds
Update code to duplicate fails
Update title succeeds
Update capacity increase succeeds
Update capacity decrease succeeds when above enrollment
Update capacity decrease fails when below enrollment
Update prerequisites succeeds
Update prerequisites to circular fails
Update status succeeds
Update unknown course fails
Delete sets status to archived
Delete with confirmed registrations fails
Delete with pending registrations fails
Delete with only completed registrations succeeds
Delete unknown course fails
List returns all courses
List filters by status
List excludes archived by default
List searches by partial code
List searches by partial title
List pagination works correctly
Get prerequisites returns prerequisite courses
Get prerequisites returns empty for none
Get prerequisites fails for unknown course
Check capacity returns correct counts
Check capacity fails for unknown course
Open course sets status to open
Open draft course succeeds
Open closed course succeeds
Open already open course fails
Open archived course fails
Close course sets status to closed
Close open course succeeds
Close draft course fails
Close archived course fails
