# enrollment.spec

description:
An enrollment represents a @entities/student being registered in a @entities/course. Each enrollment has a unique identifier, references both the student and course, and tracks when the enrollment was created. Enrollments have a status that can be active, withdrawn, or completed. A student cannot have multiple active enrollments in the same course. When a student withdraws, the enrollment status changes but the record is preserved for historical purposes.

api:
Create an enrollment linking a student to a course with an active status. Look up an enrollment by its identifier. Find all enrollments for a specific student. Find all enrollments for a specific course. Update an enrollment's status to withdrawn or completed. Check whether a student is currently enrolled in a specific course.

tests:
Creating an enrollment assigns a unique identifier and records the timestamp
Creating a duplicate active enrollment for same student and course fails
Looking up a nonexistent enrollment returns nothing
Finding enrollments by student returns all their enrollments
Finding enrollments by course returns all students in that course
Withdrawing an enrollment changes its status to withdrawn
A withdrawn student is not considered currently enrolled
Completing an enrollment changes its status to completed
A student can re-enroll in a course after withdrawing
Finding enrollments can filter by status
