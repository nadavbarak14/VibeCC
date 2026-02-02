# FreeSpec Format Reference

## File Structure

```
# filename.spec

## Description
What this component does.

## API
Functions this component provides.

## Tests
What must pass.
```

## Sections

### Description

What the component does, its purpose, constraints, and context.

```
## Description
Business logic for student enrollment. Enforces prerequisites,
capacity limits, and prevents duplicates.

Coordinates between @entities/student, @entities/course, and @entities/registration.
```

Include:
- Purpose and responsibility
- Properties (for entities)
- Constraints and business rules
- Dependencies via @mentions

### API

Functions this component provides. Format: `name(params) -> ReturnType`

```
## API
- enroll(studentId, courseId) -> Registration
  Enrolls student after validating all rules.

- checkEligibility(studentId, courseId) -> EligibilityResult
  Returns eligible (bool) and reasons (list) without making changes.
```

For REST endpoints, use HTTP method and path:

```
## API
- GET /students -> list[Student]
  List students. Query: status, search, page, limit.

- POST /students -> Student
  Create student. Body: email, name. Returns 201.
```

### Tests

What must pass. Free-form list of test cases.

```
## Tests
- Enroll succeeds when all rules pass
- Enroll fails if student not found
- Enroll fails if prerequisites not met
- Enroll fails if course full
```

## @ Mentions

Reference other specs inline using `@path/name`:

- `@entities/student` - References student entity
- `@services/enrollment` - References enrollment service
- `@endpoints/courses` - References courses endpoint

Mentions appear naturally in Description or API sections. No separate Mentions section needed.

## Types

Built-in: `string`, `int`, `float`, `bool`, `void`, `list[T]`, `T | null`

Custom types are defined by the component that owns them (e.g., `Student`, `EligibilityResult`).

## Example

```
# enrollment.spec

## Description
Business logic for student enrollment. Enforces prerequisites,
capacity limits, and prevents duplicates.

Coordinates between @entities/student, @entities/course, and @entities/registration.

## API
- enroll(studentId, courseId) -> Registration
  Enrolls student after validating all rules.
  Checks: student active, course open, prerequisites met, capacity available.

- drop(studentId, courseId, reason) -> Registration
  Student withdrawal. Cannot drop completed courses.

- checkEligibility(studentId, courseId) -> EligibilityResult
  Returns eligible (bool) and reasons (list) without making changes.

## Tests
- Enroll succeeds when all rules pass
- Enroll fails if student not found
- Enroll fails if course not open
- Enroll fails if prerequisites not met
- Enroll fails if course full
- Drop succeeds for confirmed enrollment
- Drop fails for completed enrollment
```
