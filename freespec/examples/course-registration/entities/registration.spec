# registration.spec

## Description
Represents a student's enrollment in a course.

## Properties
- id: unique identifier (generated)
- studentId: reference to @entities/student
- courseId: reference to @entities/course
- status: pending | confirmed | dropped | completed
- grade: optional, set on completion
- enrolledAt: timestamp
- completedAt: optional timestamp
- droppedAt: optional timestamp

## Constraints
- Student and course combination must be unique (no duplicate enrollments)
- Student must exist
- Course must exist
- Grade only set when status is "completed"
- completedAt only set when status is "completed"
- droppedAt only set when status is "dropped"

## Tests
- Valid registration links student and course
- Duplicate student-course pair rejected
- Invalid student reference rejected
- Invalid course reference rejected
- Grade without completed status rejected

## Mentions
@entities/student
@entities/course
