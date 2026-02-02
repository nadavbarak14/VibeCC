# FreeSpec Format Reference

## Structure

```
# filename.spec

description:
Free text describing what this component does.

api:
Free text describing what operations this component provides.

tests:
List of test cases that must pass.
```

## Sections

### description:

What the component is and does. Free text. Include constraints, relationships,
and any context needed to understand it. Use @mentions to reference other specs.

### api:

What operations this component provides. Free text describing the capabilities.
For REST endpoints, describe the routes. For services, describe the operations.
The compiler figures out the actual signatures based on target language.

### tests:

What must pass. One test case per line. These are requirements the implementation
must fulfill.

## @mentions

Reference other specs inline: `@entities/student`, `@services/enrollment`

Just use them naturally in the text where relevant.

## Example

```
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

Check if a student is eligible to enroll in a course without making any changes.
Returns whether eligible and a list of reasons if not.

tests:
Enroll succeeds when all rules pass
Enroll fails if student not found
Enroll fails if prerequisites not met
Enroll fails if course full
Drop succeeds for confirmed enrollment
Drop fails for completed enrollment
```
