# enrollment.spec

## Description
Business logic for student enrollment in courses. Enforces all
registration rules including prerequisites, capacity, and eligibility.

This is the core service that coordinates between entities and
enforces business rules that span multiple entities.

## API
- enroll(studentId, courseId) -> Registration
  Enrolls student in course after validating all rules.
  Creates registration with status "confirmed".

- drop(studentId, courseId, reason) -> Registration
  Student-initiated withdrawal from course.
  Updates registration status to "dropped".

- complete(studentId, courseId, grade) -> Registration
  Marks enrollment as completed with final grade.
  Updates registration status to "completed".

- checkEligibility(studentId, courseId) -> EligibilityResult
  Checks if student can enroll without making changes.
  Returns detailed result with pass/fail and reasons.

- getEnrollments(studentId) -> list[Registration]
  Returns all registrations for a student.

- getRoster(courseId) -> list[Registration]
  Returns all registrations for a course.

## Business Rules
- Student must exist and be active
- Course must exist and be open for registration
- Student cannot enroll in same course twice
- All prerequisites must be completed (status = "completed")
- Course must have available capacity
- Cannot drop a completed course
- Cannot complete an already completed course

## EligibilityResult Structure
- eligible: boolean
- reasons: list of failure reasons (empty if eligible)
  - "student_not_found"
  - "student_not_active"
  - "course_not_found"
  - "course_not_open"
  - "already_enrolled"
  - "prerequisites_not_met" (includes which ones)
  - "course_full"

## Tests
- Enroll succeeds when all rules pass
- Enroll fails if student not found
- Enroll fails if student not active
- Enroll fails if course not found
- Enroll fails if course not open
- Enroll fails if already enrolled
- Enroll fails if prerequisites not met
- Enroll fails if course at capacity
- Drop succeeds for confirmed enrollment
- Drop fails for completed enrollment
- Complete sets grade and status
- Complete fails if already completed
- Eligibility check returns all failure reasons
- Enrolling frees capacity slot on drop
- Completed prerequisite allows enrollment

## Mentions
@entities/student
@entities/course
@entities/registration
