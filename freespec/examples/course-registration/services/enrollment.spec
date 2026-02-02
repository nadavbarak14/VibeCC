# enrollment.spec

description:
Business logic service for student enrollment in courses. This is the main
entry point for enrollment operations, enforcing all business rules.

This service coordinates between @entities/student, @entities/course, and
@entities/registration. It should be used instead of directly manipulating
registration entities to ensure business rules are enforced.

Business rules enforced:
1. Student must exist and have status "active"
2. Course must exist and have status "open"
3. Student cannot already be enrolled (no duplicate registration)
4. All course prerequisites must be met (completed registrations)
5. Course must have available capacity (confirmed registrations < capacity)

Prerequisites check: A prerequisite is met if the student has a registration
for that course with status "completed". Dropped or pending registrations
do not count.

Capacity check: Current enrollment is count of registrations with status
"confirmed". Available capacity is course.capacity minus current enrollment.

Dropping a course:
- Only confirmed registrations can be dropped
- Completed registrations cannot be dropped (course already finished)
- Dropping frees up one capacity slot for other students

Completing a course:
- Only confirmed registrations can be completed
- Requires a grade to be assigned
- Once completed, registration counts toward prerequisites

api:
Enroll a student in a course given student id and course id. Validates all
business rules in order: student exists and active, course exists and open,
not already enrolled, prerequisites met, capacity available. If all pass,
creates registration with confirmed status. Returns the registration.
Fails with specific reason if any rule fails.

Drop a student from a course given student id, course id, and optional reason.
Finds the registration, validates it can be dropped (must be confirmed, not
completed). Updates status to dropped, records reason if provided.
Returns updated registration. Fails if not found or cannot be dropped.

Complete a registration given student id, course id, and grade. Finds the
registration, validates it can be completed (must be confirmed). Sets grade
and status to completed. Returns updated registration.
Fails if not found, not confirmed, or grade invalid.

Check eligibility for a student to enroll in a course given student id and
course id. Runs all validation rules without making changes. Returns result
indicating whether eligible and list of all reasons if not. Reasons include:
- student_not_found: no student with that id
- student_not_active: student exists but status is not active
- course_not_found: no course with that id
- course_not_open: course exists but status is not open
- already_enrolled: registration already exists for this student and course
- missing_prerequisite: lists which prerequisites are not completed
- course_full: no available capacity

Get all enrollments for a student given student id. Returns all registrations
for that student with full course details included. Useful for showing a
student their schedule. Fails if student not found.

Get roster for a course given course id. Returns all confirmed registrations
with full student details included. Can optionally include other statuses.
Useful for instructors viewing their class. Fails if course not found.

tests:
Enroll succeeds when all rules pass
Enroll creates confirmed registration
Enroll fails when student not found
Enroll fails when student is inactive
Enroll fails when student is suspended
Enroll fails when course not found
Enroll fails when course is draft
Enroll fails when course is closed
Enroll fails when course is archived
Enroll fails when already enrolled with confirmed status
Enroll fails when already enrolled with pending status
Enroll succeeds when previous registration was dropped
Enroll fails when prerequisite not completed
Enroll fails when prerequisite only dropped
Enroll succeeds when all prerequisites completed
Enroll fails when course at capacity
Enroll succeeds when course has one slot left
Eligibility returns eligible true when can enroll
Eligibility returns all failure reasons at once
Eligibility does not create registration
Eligibility with unknown student returns student_not_found
Eligibility with inactive student returns student_not_active
Eligibility with unknown course returns course_not_found
Eligibility with closed course returns course_not_open
Eligibility with existing registration returns already_enrolled
Eligibility with missing prerequisite lists which ones
Eligibility with full course returns course_full
Drop succeeds for confirmed registration
Drop sets status to dropped
Drop records the reason if provided
Drop frees capacity slot
Drop fails for pending registration
Drop fails for completed registration
Drop fails for already dropped registration
Drop fails when registration not found
Complete succeeds for confirmed registration
Complete sets status and grade
Complete fails for pending registration
Complete fails for dropped registration
Complete fails for already completed registration
Complete fails when registration not found
Complete fails with invalid grade
Get enrollments returns all student registrations
Get enrollments includes course details
Get enrollments fails for unknown student
Get roster returns confirmed registrations
Get roster includes student details
Get roster can include other statuses
Get roster fails for unknown course
