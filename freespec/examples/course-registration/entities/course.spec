# course.spec

description:
A course represents a class that students can register for. Each course has a unique code like "CS101" that identifies it, a title for display, and an optional description.

Courses have a maximum capacity indicating how many students can enroll. A course can be open for registration or closed. Only open courses accept new registrations. Courses start as closed when created.

Courses may have prerequisites, which are other courses a student must have completed before registering. Prerequisites form a directed acyclic graph; circular prerequisites are not allowed.

exports:
- Create a new course with code, title, capacity, and optional description
- Find a course by its code
- Find a course by its unique ID
- Update a course's title, description, or capacity
- Open a course for registration
- Close a course to registration
- Add a prerequisite to a course
- Remove a prerequisite from a course
- List all courses with optional filters for open status
- Get the current enrollment count for a course
- Check if a course has available seats

tests:
- Creating a course with valid code, title, and capacity succeeds
- Creating a course with an already-used code fails
- Course codes are case-sensitive
- Creating a course with capacity less than 1 fails
- Opening a closed course succeeds
- Opening an already open course succeeds without error
- Adding a prerequisite that would create a cycle fails
- Adding the same prerequisite twice succeeds without creating duplicates
- Removing a prerequisite that doesn't exist succeeds without error
- Reducing capacity below current enrollment count fails
