# enrollment.spec

description:
Business logic for student course registration. Enforces all rules for enrolling students in courses. Coordinates between @entities/student, @entities/course, and @entities/registration.

A student can only enroll if they are active, the course is open, they have completed all prerequisites, the course has capacity, and they are not already enrolled. Prerequisites are courses the student has completed with a passing grade (not F), not just enrolled in.

Dropping a course frees up a capacity slot and allows the student to re-enroll later. Completed courses cannot be dropped. Only confirmed registrations can be dropped.

The service provides eligibility checking separate from enrollment, so the UI can show why a student cannot enroll before they attempt it.

exports:
Enroll a student in a course, returning the registration or failure reason
Drop a student from a course with an optional reason
Check if a student is eligible to enroll, returning all failure reasons if not
Get all registrations for a student with optional status filter
Get all students enrolled in a course with optional status filter
Get completed courses for a student

tests:
Enroll succeeds when all rules pass
Enroll creates registration with confirmed status
Enroll fails when student not found
Enroll fails when student is inactive
Enroll fails when student is suspended
Enroll fails when course not found
Enroll fails when course not open
Enroll fails when already enrolled
Enroll fails when prerequisites not met
Enroll fails when prerequisite completed with F grade
Enroll fails when course is full
Enroll after dropping same course succeeds
Drop succeeds for confirmed registration
Drop fails for pending registration
Drop fails for completed registration
Drop fails for already dropped registration
Drop decrements course enrollment count
Eligibility check returns empty list when eligible
Eligibility check returns all failure reasons
Eligibility check includes missing prerequisites by name
Get registrations for student returns all matching
Get registrations filters by status
Get students in course returns enrolled students
Get completed courses returns only completed with passing grade
