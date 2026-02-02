# FreeSpec Format Reference

This document defines the formal structure of `.spec` files.

## File Structure

A spec file consists of a header and multiple sections:

```
# filename.spec

## Section1
Content...

## Section2
Content...
```

## Header

The first line should be a comment with the filename:

```
# component.spec
```

## Sections

### Description (Required)

High-level overview of what this component does.

```
## Description
Handles student enrollment in courses. Core business logic for the
registration system. Must enforce prerequisites, capacity limits,
and prevent duplicate registrations.

Performance: Should handle 1000 concurrent registrations.
Security: Only authenticated students can register themselves.
```

**Contents:**
- Purpose and responsibility of the component
- Implementation details and algorithms
- Business rules and constraints
- Non-functional requirements (performance, security, scalability)

### API (Required)

Contract-level interface definitions. Format is flexible.

```
## API
- register(studentId, courseId) -> Registration
  Enrolls student in course. Returns registration record.

- unregister(studentId, courseId) -> bool
  Removes student from course. Returns success status.
```

**Supported formats:**
- Function signatures with descriptions
- Natural language descriptions
- Pseudo-code
- Mixed formats

**Guidelines:**
- Define inputs and outputs clearly
- Describe behavior, not implementation
- Include error conditions where relevant

### Tests (Required)

Free-form use cases that MUST be fulfilled by the implementation.

```
## Tests
- Successfully register student in available course
- Reject if student already registered for course
- Reject if course at capacity
- Reject if prerequisites not met
```

**Guidelines:**
- Use "Must" for required behavior
- Use "Should" for expected behavior
- Include both success and failure cases
- Reference @mentions for cross-component tests

### Mentions (Optional)

Explicit dependency declarations. Can also be inline in other sections.

```
## Mentions
@student - Student entity and operations
@course - Course entity with prerequisites and capacity
```

## @ Mentions

Dependencies are declared using `@` prefix:

- `@component` - References another spec file
- `@component.function` - References a specific function
- `@component.type` - References a type definition

Mentions can appear:
- In a dedicated Mentions section
- Inline within Description, API, or Tests sections

## Types

Types can be defined inline or reference standard types:

**Built-in types:**
- `string`, `int`, `float`, `bool`
- `list[T]`, `dict[K, V]`, `optional[T]`
- `void` (no return value)

**Custom types:**
- Defined in the component that owns them
- Referenced via @mentions from other specs

## Best Practices

1. **Keep specs focused** - One component per file
2. **Use clear names** - Function names should describe actions
3. **Document edge cases** - Include error conditions in Tests
4. **Link dependencies** - Use @mentions for cross-references
5. **Be specific in Tests** - Vague tests lead to vague implementations

## Example

```
# authentication.spec

## Description
Handles user authentication and session management.
Supports multiple auth methods: password, OAuth, API keys.
Sessions expire after 24 hours of inactivity.

Security: Passwords must be hashed with bcrypt.
Rate limiting: Max 5 failed attempts per minute.

## API
- login(email, password) -> Session
  Authenticates user with credentials. Returns session token.

- logout(sessionId) -> bool
  Invalidates the session. Returns success status.

- validateSession(sessionId) -> User | null
  Checks if session is valid. Returns user or null.

- refreshSession(sessionId) -> Session
  Extends session expiry. Returns updated session.

## Tests
- Successful login with valid credentials
- Reject login with invalid password
- Reject login with unknown email
- Lock account after 5 failed attempts
- Session expires after 24 hours
- Logout invalidates session immediately
- Cannot use session after logout
- Refresh extends expiry time

## Mentions
@user - User entity for credential storage
@session - Session entity for token management
```
