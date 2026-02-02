# enrollment.spec

description:
Business logic for student enrollment. Enforces prerequisites, capacity limits,
and prevents duplicate registrations.

Coordinates between @entities/student, @entities/course, and @entities/registration.

api:
Enroll a student in a course. Validates that the student is active, the course
is open for registration, all prerequisites are completed, there's available
capacity, and the student isn't already enrolled.

Drop a student from a course. Records the reason. Cannot drop a completed course.

Mark a registration as completed with a grade. This is required for the course
to count toward prerequisites.

Check if a student is eligible to enroll in a course without making any changes.
Returns whether eligible and a list of reasons if not (student not found,
student not active, course not found, course not open, already enrolled,
prerequisites not met, course full).

Get all courses a student is enrolled in.
Get all students enrolled in a course.

tests:
Enroll succeeds when all rules pass
Enroll fails if student not found
Enroll fails if student not active
Enroll fails if course not found
Enroll fails if course not open
Enroll fails if already enrolled
Enroll fails if prerequisites not met
Enroll fails if course full
Drop succeeds for confirmed enrollment
Drop fails for completed enrollment
Complete sets grade and status
Eligibility check returns all failure reasons
Dropping frees capacity slot
Completed courses satisfy prerequisites
