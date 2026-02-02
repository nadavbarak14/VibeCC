# registration.spec

description:
A registration links a @entities/student to a @entities/course, representing enrollment. Each registration tracks when the student enrolled and their current status.

A registration can be enrolled, completed, or dropped. Students start as enrolled when they register. A completed registration means the student finished the course successfully. A dropped registration means the student withdrew.

A student can only have one active registration per course. If they drop a course, they can register again. Completed registrations count toward prerequisite requirements for other courses.

exports:
- Create a registration for a student in a course
- Find a registration by student and course
- Find all registrations for a student
- Find all registrations for a course
- Mark a registration as completed
- Mark a registration as dropped
- Check if a student has completed a specific course

tests:
- Creating a registration for a valid student and course succeeds
- Creating a registration for a non-existent student fails
- Creating a registration for a non-existent course fails
- Creating a duplicate active registration for same student and course fails
- A student who dropped a course can register for it again
- A student who completed a course cannot register for it again
- Marking an enrolled registration as completed succeeds
- Marking a dropped registration as completed fails
- Marking a completed registration as dropped fails
- Finding registrations for a student returns all statuses
- Checking completion returns true only for completed status
