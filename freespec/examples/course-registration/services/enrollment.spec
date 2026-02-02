# enrollment.spec

description:
The enrollment service manages student course registration. It coordinates between @entities/student, @entities/course, and @entities/registration to handle the business logic of enrolling in courses.

When a student attempts to register for a course, several conditions are checked. The course must be open for registration. The course must have available seats. The student must have completed all prerequisite courses. The student must not already be enrolled in the course.

Dropping a course updates the registration status and frees up a seat for other students. Students can only drop courses they are currently enrolled in.

Completing a course is typically done by an administrator. It marks the student as having successfully finished the course, which then counts toward prerequisites for other courses.

The service can retrieve a student's schedule, showing all courses they are currently enrolled in, and their history, showing all registrations including completed and dropped courses.

exports:
- Register a student for a course
- Drop a student from a course
- Mark a student as having completed a course
- Get a student's current schedule
- Get a student's registration history
- Check if a student meets prerequisites for a course

tests:
- Registering for an open course with available seats succeeds
- Registering for a closed course fails
- Registering for a full course fails
- Registering without meeting prerequisites fails
- Registering for a course already enrolled in fails
- Dropping an enrolled course succeeds and frees a seat
- Dropping a course not enrolled in fails
- Dropping a completed course fails
- Completing a course marks the registration as completed
- Completed courses count toward prerequisites
- Schedule shows only currently enrolled courses
- History shows enrolled, completed, and dropped registrations
- Prerequisite check returns true when all prerequisites are completed
- Prerequisite check returns false when any prerequisite is missing
