# enrollment-service.spec

description:
The enrollment service orchestrates the process of students enrolling in and withdrawing from courses. It enforces all business rules by coordinating between @entities/student, @entities/course, and @entities/enrollment. When a student attempts to enroll, the service verifies the student is eligible, the course can accept enrollments, and the student is not already enrolled. Upon successful enrollment, it creates the enrollment record and updates the course's enrollment count. Withdrawals reverse this process, updating the enrollment status and freeing up a spot in the course.

api:
Enroll a student in a course, performing all necessary validations and updates atomically. Withdraw a student from a course, updating the enrollment status and course count. Get all courses a student is currently enrolled in. Get all students currently enrolled in a course. Check whether a student can enroll in a specific course, returning the reason if not.

tests:
Enrolling an eligible student in an available course succeeds
Enrolling increases the course enrollment count by one
Enrolling a student who is not active fails with appropriate reason
Enrolling in a course that is not open fails with appropriate reason
Enrolling in a full course fails with appropriate reason
Enrolling when already enrolled in the same course fails
Withdrawing a student decreases the course enrollment count by one
Withdrawing changes the enrollment status to withdrawn
Withdrawing from a course the student is not enrolled in fails
Getting enrolled courses returns only active enrollments
Getting enrolled students returns only active enrollments
Enrollment check returns success for valid combinations
Enrollment check explains why student is ineligible
Enrollment check explains why course cannot accept students
