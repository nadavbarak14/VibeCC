# registration.spec

description:
A record of a student's enrollment in a course.

Properties:
- id: unique identifier, generated on creation, immutable
- studentId: reference to @entities/student, immutable after creation
- courseId: reference to @entities/course, immutable after creation
- status: one of pending, confirmed, dropped, completed
- grade: optional grade value, only set when status is completed
- enrolledAt: timestamp when registration was created
- completedAt: timestamp when status changed to completed, null otherwise
- droppedAt: timestamp when status changed to dropped, null otherwise

Constraints:
- studentId must reference an existing student
- courseId must reference an existing course
- A student can only have one registration per course (unique studentId+courseId)
- Grade can only be set when status is completed
- Grade format is flexible (A-F, 0-100, pass/fail - determined by implementation)
- completedAt is only set when status becomes completed
- droppedAt is only set when status becomes dropped
- Cannot change studentId or courseId after creation

Status meanings:
- pending: registration created but not yet confirmed (for future use)
- confirmed: student is actively enrolled in the course
- dropped: student withdrew from the course
- completed: student finished the course with a grade

Status transitions:
- pending -> confirmed (confirm enrollment)
- pending -> dropped (cancel before confirmation)
- confirmed -> dropped (student withdraws)
- confirmed -> completed (course finished, grade assigned)
- dropped -> (terminal, no transitions)
- completed -> (terminal, no transitions)

A registration with status "completed" counts toward @entities/course prerequisites.
Dropped registrations do not count toward prerequisites.

api:
Create a registration linking a student to a course. Sets status to confirmed,
generates id, sets enrolledAt timestamp. Returns created registration.
Fails if student not found, course not found, or duplicate registration exists.

Get a registration by id. Returns registration if found, nothing if not found.

Find a registration by student id and course id. Returns registration if found,
nothing if not found. Useful for checking if already enrolled.

List registrations for a student given student id. Returns all registrations
for that student regardless of status. Returns empty list if student has none.
Fails if student not found.

List registrations for a course given course id (the roster). Returns all
registrations for that course. Can filter by status. Returns empty list if
course has none. Fails if course not found.

Update registration status given id and new status. Validates transition is
allowed. Sets droppedAt if transitioning to dropped.
Returns updated registration. Fails if not found or invalid transition.

Set grade and complete a registration given id and grade. Sets status to
completed, sets grade, sets completedAt timestamp.
Fails if not found, not in confirmed status, or grade invalid.

tests:
Create with valid student and course succeeds
Create generates unique id
Create sets status to confirmed
Create sets enrolledAt timestamp
Create with unknown student fails
Create with unknown course fails
Create duplicate student-course pair fails
Get with valid id returns registration
Get with unknown id returns nothing
Find by student and course returns registration
Find by unknown combination returns nothing
List by student returns all registrations
List by student returns empty for none
List by unknown student fails
List by course returns all registrations
List by course filters by status
List by course returns empty for none
List by unknown course fails
Update status pending to confirmed succeeds
Update status pending to dropped succeeds
Update status confirmed to dropped succeeds
Update status confirmed to completed fails without grade
Update status dropped to anything fails
Update status completed to anything fails
Update sets droppedAt when dropping
Update unknown registration fails
Set grade on confirmed registration succeeds
Set grade sets status to completed
Set grade sets completedAt timestamp
Set grade on pending registration fails
Set grade on dropped registration fails
Set grade on completed registration fails
Set grade with invalid format fails
Set grade on unknown registration fails
