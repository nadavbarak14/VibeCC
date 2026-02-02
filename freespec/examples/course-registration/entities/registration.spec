# registration.spec

## Description
A student's enrollment in a course.

Properties: id, studentId (@entities/student), courseId (@entities/course),
status (pending/confirmed/dropped/completed), grade (optional),
enrolledAt, completedAt (optional), droppedAt (optional).

Student + course combination must be unique.
Grade only set when completed.

## API
- create(studentId, courseId) -> Registration
  Creates registration record.

- get(id) -> Registration | null
  Returns registration or null.

- getByStudentAndCourse(studentId, courseId) -> Registration | null
  Finds specific enrollment.

- listByStudent(studentId) -> list[Registration]
  Returns all registrations for a student.

- listByCourse(courseId) -> list[Registration]
  Returns all registrations for a course.

- updateStatus(id, status) -> Registration
  Changes registration status.

- setGrade(id, grade) -> Registration
  Sets grade and marks completed.

## Tests
- Create links student and course
- Duplicate student-course rejected
- Invalid student rejected
- Invalid course rejected
- Get returns registration
- List by student returns all enrollments
- List by course returns roster
- Set grade marks as completed
