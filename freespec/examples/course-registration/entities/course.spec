# course.spec

description:
A course that students can register for. Has an id, code, title, description, capacity, and status. Code must be unique and follows a pattern like CS101 or MATH200.

Status is draft, open, closed, or archived. Only open courses accept new registrations. Draft courses are being prepared and not yet visible to students. Closed courses have finished registration but may still be in progress. Archived courses are historical records.

Capacity is the maximum number of students who can register. A course tracks current enrollment count. When enrollment equals capacity, the course is full and rejects new registrations.

A course can have prerequisites, which are other courses a student must have completed before registering. Prerequisites form a directed graph and must not create cycles.

exports:
Create a course with code, title, description, and capacity
Get a course by id
Find a course by code
Update a course's title, description, or capacity
Change course status with validation
Delete a course (only if draft with no registrations)
List courses with optional status filter and pagination
Add a prerequisite course
Remove a prerequisite course
Get all prerequisites for a course
Check if a course is full

tests:
Create with valid data succeeds
Create with duplicate code fails
Create with invalid code format fails
Create with zero or negative capacity fails
Get returns course by id
Get returns nothing for unknown id
Find by code succeeds
Update title succeeds
Update capacity below current enrollment fails
Change status from draft to open succeeds
Change status from open to closed succeeds
Change status from closed to archived succeeds
Change status backwards fails
Delete draft course with no registrations succeeds
Delete non-draft course fails
Delete course with registrations fails
List returns open courses by default
List filters by status
Add prerequisite succeeds
Add prerequisite that creates cycle fails
Add self as prerequisite fails
Remove prerequisite succeeds
Check full returns true when at capacity
Check full returns false when under capacity
