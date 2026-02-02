# Instructions for Writing FreeSpec Files

This guide is for the coding agent creating `.spec` files.

## Core Principle

**Each spec file is code.** Treat it like you're writing a source file, not documentation.

A spec file must be self-contained and complete. Anyone reading it should
understand exactly what this component is, what it does, and how to verify it works.

## Format

There are exactly THREE sections. No more, no less.

```
# filename.spec

description:
Free text about what this component is and does.

api:
Operations this component provides, one per line.

tests:
Test cases that must pass, one per line.
```

**DO NOT invent other labels.** No "Properties:", no "Constraints:", no "Status:",
no "Authorization:", no sub-sections. Everything goes into one of the three sections
as natural free-flowing text.

## The Three Sections

### description:

Free text explaining what this component is. Write in natural paragraphs.
Include everything someone needs to understand this component:

- What it represents or does
- Its data and how it behaves
- Rules and constraints in plain language
- Relationships to other components using @mentions
- What can go wrong
- Security or authorization considerations

Just write it as prose. Don't structure it with labels or bullet points for
different categories. Let it flow naturally.

### api:

One operation per line. Each line describes a single thing you can do with
this component. For services, list each action. For REST endpoints, list
each route. For entities, list create, read, update, delete operations.

Don't write function signatures or parameter types. The target language isn't
known yet. Just describe each operation in plain language.

### tests:

One test case per line. These are requirements - if any test fails, the
implementation is wrong.

Cover:
- The normal case works
- Each way it can fail
- Edge cases
- Security/authorization rules

## @mentions

Reference other specs with `@path/name` inline in your text:
- `@entities/student`
- `@services/enrollment`

Use them naturally where relevant.

## What Goes In vs Out

**IN the spec:** Everything needed to implement it. If it matters, write it.

**NOT in the spec:** Implementation details, language-specific types, code structure.

## Example

```
# enrollment.spec

description:
Business logic for student enrollment. This service enforces all the rules
for enrolling students in courses. It coordinates between @entities/student,
@entities/course, and @entities/registration.

A student can only enroll if they are active, the course is open, they have
completed all prerequisites, the course has capacity, and they aren't already
enrolled. Prerequisites are courses the student has completed, not just enrolled in.

Dropping a course frees up a capacity slot. Completed courses cannot be dropped.

api:
Enroll a student in a course, checking all rules and returning the registration or failure reason
Drop a student from a course with an optional reason
Complete a registration with a grade
Check if a student is eligible to enroll, returning all failure reasons if not
Get all enrollments for a student
Get all students enrolled in a course

tests:
Enroll succeeds when all rules pass
Enroll fails when student not found
Enroll fails when student is inactive
Enroll fails when course not open
Enroll fails when already enrolled
Enroll fails when prerequisites not met
Enroll fails when course full
Drop succeeds for confirmed registration
Drop fails for completed registration
Complete sets the grade
Eligibility check returns all failure reasons
```

## Checklist Before Finishing

- [ ] Only three sections: description:, api:, tests:
- [ ] No invented labels or sub-sections
- [ ] Description is natural prose, not structured lists
- [ ] All behavior and rules are documented
- [ ] All failure modes have corresponding tests
- [ ] @mentions point to real specs
- [ ] Someone could implement this without asking questions
