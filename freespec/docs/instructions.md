# Instructions for Writing FreeSpec Files

This guide is for the coding agent creating `.spec` files.

## Core Principle

**Each spec file is code.** Treat it like you're writing a source file, not documentation.

A spec file must be self-contained and complete. Anyone (human or AI) reading it should
understand exactly what this component is, what it does, and how to verify it works.

## What Goes in a Spec File

Everything relevant to that component:

- What it is
- What it does
- What it depends on
- What constraints apply
- What can go wrong
- How to test it

If something matters for implementation, it belongs in the spec.

## Writing Each Section

### description:

This is not a summary. It's the complete definition of what this component is.

Include:
- What the component represents or does
- Its properties/data (for entities)
- Constraints and validation rules
- Relationships to other components (@mentions)
- Edge cases and error conditions
- Security or performance considerations if relevant

Bad:
```
description:
A student entity.
```

Good:
```
description:
A student who can enroll in courses.

Has a unique email, name, and status (active, inactive, or suspended).
Tracks when created and last updated.

Email must be valid format and unique across all students.
Status defaults to active on creation.
```

### api:

Describe every operation this component provides. Be specific about:
- What the operation does
- What inputs it needs (conceptually, not typed parameters)
- What it returns or produces
- What can cause it to fail

For REST endpoints, include the HTTP method and path.
For services, describe each distinct operation.
For entities, describe CRUD and any special operations.

Bad:
```
api:
CRUD operations for students.
```

Good:
```
api:
Create a new student with name and email. Email must be unique.
Get a student by their ID.
Find a student by their email.
Update a student's information.
Delete a student (soft delete - sets inactive). Cannot delete if they have
active registrations.
List students with filtering and pagination.
```

### tests:

These are requirements, not suggestions. Every test listed must pass for the
implementation to be correct.

Write tests that:
- Cover the happy path
- Cover each failure mode mentioned in description/api
- Cover edge cases
- Cover security constraints (who can do what)

One test per line. Be specific enough that the test is unambiguous.

Bad:
```
tests:
Create works
Delete works
```

Good:
```
tests:
Create with valid data succeeds
Duplicate email rejected
Invalid email format rejected
Delete sets status inactive
Delete fails with active registrations
```

## Using @mentions

Reference other specs with `@path/name`:
- `@entities/student`
- `@services/enrollment`
- `@endpoints/courses`

Use them naturally in the text. They indicate dependencies - the compiler uses
these to determine build order and verify all references exist.

## File Organization

Mirror logical architecture:
- `entities/` - data structures, what things are
- `services/` - business logic, what operations exist
- `endpoints/` - HTTP interface, how to access operations
- `server.spec` - infrastructure, how it all connects

Each directory groups related specs. Each spec is one component.

## Completeness Checklist

Before finishing a spec file, verify:

- [ ] Description explains what it IS, not just what it does
- [ ] All properties/data are listed (for entities)
- [ ] All constraints are documented
- [ ] All operations are described in api section
- [ ] All failure modes have corresponding tests
- [ ] All @mentions point to real specs
- [ ] Someone could implement this without asking questions
