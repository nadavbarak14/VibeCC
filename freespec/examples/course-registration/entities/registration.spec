# registration.spec

description:
A registration linking a @entities/student to a @entities/course. Has an id, student id, course id, status, registered at timestamp, and optional completed at timestamp with grade.

Status is pending, confirmed, dropped, or completed. Pending registrations are awaiting confirmation. Confirmed registrations are active enrollments. Dropped registrations were cancelled by the student. Completed registrations have a final grade.

A student can only have one non-dropped registration per course. The combination of student id and course id must be unique among active registrations. Dropped registrations are kept for history.

Grades are letter grades A, B, C, D, or F. Only confirmed registrations can be completed with a grade. Completed registrations cannot be modified or dropped.

exports:
Create a registration for a student and course
Get a registration by id
Get a registration by student and course
Update registration status
Complete a registration with a grade
List registrations for a student
List registrations for a course
Count active registrations for a course

tests:
Create registration succeeds
Create duplicate active registration fails
Create registration after dropping same course succeeds
Get returns registration by id
Get returns nothing for unknown id
Get by student and course returns active registration
Get by student and course ignores dropped registrations
Update from pending to confirmed succeeds
Update from confirmed to dropped succeeds
Update completed registration fails
Complete confirmed registration with valid grade succeeds
Complete pending registration fails
Complete with invalid grade fails
List for student returns all their registrations
List for course returns all registrations
Count returns number of non-dropped registrations
