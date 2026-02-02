# registration.spec

description:
A student's enrollment in a course.

Links a @entities/student to a @entities/course.
Status can be pending, confirmed, dropped, or completed.
Has optional grade (only when completed).
Tracks when enrolled, completed, or dropped.

A student can only have one registration per course.

api:
Create a registration linking student and course.
Get a registration by ID.
Find a registration by student and course.
List all registrations for a student.
List all registrations for a course (the roster).
Update registration status.
Set grade and mark as completed.

tests:
Create links student and course
Duplicate student-course rejected
Invalid student rejected
Invalid course rejected
Get returns registration
List by student returns all enrollments
List by course returns roster
Set grade marks as completed
