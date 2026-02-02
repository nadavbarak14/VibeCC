# FreeSpec Format Reference

## Structure

```
# filename.spec

description:
Free text about what this is.

exports:
Functions, one per line.

tests:
Test cases, one per line.
```

Three sections only. No other labels.

## @mentions

Reference other specs inline: `@entities/student`, `@services/enrollment`

## Example

```
# student.spec

description:
A student who can enroll in courses. Has an id, email, name, and status.
Email must be unique and is case-insensitive. Status is active, inactive,
or suspended, defaulting to active.

Inactive or suspended students cannot enroll in new courses but keep
their existing @entities/registration records. Deleting a student sets
status to inactive. Cannot delete if they have active registrations.

exports:
Create a student with name and email.
Get a student by id.
Find a student by email.
Update a student.
Delete a student (soft delete).
List students with filtering and pagination.

tests:
Create with valid data succeeds
Create with duplicate email fails
Create with invalid email fails
Get returns student by id
Get returns nothing for unknown id
Update email to duplicate fails
Delete sets status to inactive
Delete with active registration fails
List filters by status
```
