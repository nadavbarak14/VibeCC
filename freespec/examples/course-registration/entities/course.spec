# course.spec

description:
A course available for enrollment.

Has a unique code, title, capacity limit, and list of prerequisite courses.
Status can be draft, open, closed, or archived.

Prerequisites are other courses that a @entities/student must complete before enrolling.
Cannot have circular prerequisite chains.

api:
Create a course with code, title, capacity, and optional prerequisites.
Get a course by ID.
Update a course. Cannot reduce capacity below current enrollment.
Delete a course (archives it). Cannot delete if has active @entities/registration records.
List courses with filtering and pagination.
Get all prerequisite courses for a given course.
Check current enrollment count and remaining capacity.
Open a course for registration.
Close a course to new registrations.

tests:
Create with valid data succeeds
Duplicate code rejected
Invalid prerequisite rejected
Circular prerequisites rejected
Get returns course by ID
Update changes fields
Cannot reduce capacity below enrollment
Delete archives course
Delete fails with active registrations
Check capacity returns accurate count
