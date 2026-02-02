# course.spec

## Description
Represents a course available for student enrollment.

## Properties
- id: unique identifier (generated)
- code: course code (e.g., "CS101")
- title: course title
- capacity: maximum number of students
- prerequisites: list of course IDs required before enrollment
- status: draft | open | closed | archived
- createdAt: timestamp
- updatedAt: timestamp

## Constraints
- Code must be unique
- Capacity must be positive integer
- Prerequisites must reference existing courses
- Cannot create circular prerequisite chains
- Status defaults to "draft" on creation

## Tests
- Valid course has all required fields
- Duplicate code rejected
- Zero or negative capacity rejected
- Invalid prerequisite reference rejected
- Circular prerequisites rejected
