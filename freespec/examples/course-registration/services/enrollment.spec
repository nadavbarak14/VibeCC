# enrollment.spec

## Description
Business logic for student enrollment. Enforces prerequisites,
capacity limits, and prevents duplicates.

Coordinates between @entities/student, @entities/course, and @entities/registration.

## API
- enroll(studentId, courseId) -> Registration
  Enrolls student after validating all rules.
  Checks: student active, course open, prerequisites met, capacity available, not duplicate.

- drop(studentId, courseId, reason) -> Registration
  Student withdrawal. Cannot drop completed courses.

- complete(studentId, courseId, grade) -> Registration
  Marks as completed with grade. Required for prerequisite checks.

- checkEligibility(studentId, courseId) -> EligibilityResult
  Returns eligible (bool) and reasons (list) without making changes.
  Reasons: student_not_found, student_not_active, course_not_found,
  course_not_open, already_enrolled, prerequisites_not_met, course_full.

- getEnrollments(studentId) -> list[Registration]
  All courses a student is enrolled in.

- getRoster(courseId) -> list[Registration]
  All students in a course.

## Tests
- Enroll succeeds when all rules pass
- Enroll fails if student not found
- Enroll fails if student not active
- Enroll fails if course not found
- Enroll fails if course not open
- Enroll fails if already enrolled
- Enroll fails if prerequisites not met
- Enroll fails if course full
- Drop succeeds for confirmed enrollment
- Drop fails for completed enrollment
- Complete sets grade and status
- Eligibility returns all failure reasons
- Dropping frees capacity slot
- Completed courses satisfy prerequisites
