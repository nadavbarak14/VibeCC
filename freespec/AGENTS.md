# FreeSpec: AI Agent Guide

This document explains the FreeSpec system for AI agents that will write spec files or generate implementations from them.

## What is FreeSpec?

FreeSpec is a **specification-level meta-language** where humans write structured specifications in natural language, and AI generates executable code. It bridges human intent and working software.

**Core principle:** Each `.spec` file is code. It completely defines a component's behavior, API, and test requirements. The spec is the source of truth.

## The Spec Language

### File Structure

Every `.spec` file has exactly **three sections**. No more, no less.

```
# filename.spec

description:
Free text about what this component is and does.

exports:
- What this component provides, one per line

tests:
- Test cases that must pass, one per line
```

**Critical rules:**
- Only these three section labels are allowed
- DO NOT invent other labels (no "Properties:", "Constraints:", "Status:", etc.)
- Description is natural prose, not structured lists
- Exports and tests are bullet lists (lines starting with `-`)

### The Three Sections

#### `description:`

Free-flowing prose explaining:
- What the component represents or does
- Its data and behavior
- Business rules and constraints
- Relationships to other components (using @mentions)
- Error conditions and edge cases
- Security or authorization considerations

Write naturally. Don't structure it with sub-labels. Let it flow as paragraphs.

#### `exports:`

One line per capability this component provides:
- For entities: CRUD operations and queries
- For services: Business actions and workflows
- For APIs: Endpoints and their purposes

Don't write type signatures or language-specific syntax. The target language isn't known yet.

#### `tests:`

One test case per line. These are **requirements**:
- If a test fails, the implementation is wrong
- Cover the happy path
- Cover each failure mode
- Cover edge cases
- Cover security rules

### @mentions: Declaring Dependencies

Reference other specs with `@category/name`:
- `@entities/student`
- `@services/enrollment`
- `@api/courses`

**MANDATORY:** If your component depends on another, you MUST @mention it at least once in the description. This:
- Makes dependencies explicit and traceable
- Enables the compiler to provide context during generation
- Allows circular dependencies through two-pass compilation

### Entry Points

If your spec describes an application entry point (not a library module), mention "main" in the description:

```
description:
REST API server for course registration.
Uses @api/routes to define endpoints.
The main entry point starts the HTTP server on port 8080.
```

This tells the compiler to generate a runnable program with appropriate entry point for the target language.

## Example Specs

### Entity Example: student.spec

```
# student.spec

description:
A student is a user who can authenticate and register for courses. Each
student has an email address which serves as their unique identifier and
login credential. Email addresses are case-insensitive, so "John@Example.com"
and "john@example.com" refer to the same student.

Students have a name for display purposes and a password for authentication.
Passwords are never stored in plain text; only a secure hash is kept. The
password must be at least 8 characters long.

Students can be active or inactive. Only active students can log in and
register for courses. A student starts as active when created.

exports:
- Create a new student with email, name, and password
- Find a student by their email address
- Find a student by their unique ID
- Update a student's name or password
- Deactivate a student
- Reactivate a student
- List all students with optional filters for active status
- Verify a password matches for a given student

tests:
- Creating a student with valid email, name, and password succeeds
- Creating a student with an already-used email fails
- Creating a student with email differing only in case from existing email fails
- Creating a student with password shorter than 8 characters fails
- Creating a student with invalid email format fails
- Finding a student by email is case-insensitive
- Verifying correct password returns success
- Verifying incorrect password returns failure
- Inactive students cannot have their password verified
- Updating password to one shorter than 8 characters fails
- Deactivating an already inactive student succeeds without error
```

### Service Example: enrollment.spec

```
# enrollment.spec

description:
The enrollment service manages student course registration. It coordinates
between @entities/student, @entities/course, and @entities/registration to
handle the business logic of enrolling in courses.

When a student attempts to register for a course, several conditions are
checked. The course must be open for registration. The course must have
available seats. The student must have completed all prerequisite courses.
The student must not already be enrolled in the course.

Dropping a course updates the registration status and frees up a seat for
other students. Students can only drop courses they are currently enrolled in.

Completing a course is typically done by an administrator. It marks the
student as having successfully finished the course, which then counts toward
prerequisites for other courses.

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
```

## Project Organization

### Directory Structure

```
my-project/
├── freespec.yaml              # Project configuration
├── specs/                     # Optional: dedicated specs directory
│   ├── entities/              # Data models
│   │   ├── student.spec
│   │   ├── course.spec
│   │   └── registration.spec
│   ├── services/              # Business logic
│   │   ├── auth.spec
│   │   └── enrollment.spec
│   └── api/                   # External interfaces
│       ├── courses.spec
│       └── students.spec
└── out/                       # Generated output
    └── python/
        ├── src/
        │   ├── entities/
        │   ├── services/
        │   └── api/
        ├── tests/
        └── .freespec_build.json
```

### Categories

Organize specs into categories by placing them in appropriately named directories:

| Category | Purpose | Examples |
|----------|---------|----------|
| `entities/` | Data models and persistence | student, course, order, user |
| `services/` | Business logic and workflows | enrollment, auth, payment |
| `api/` | External interfaces | REST endpoints, GraphQL, CLI |

The category becomes part of the spec ID: `entities/student`, `services/enrollment`.

### Configuration: freespec.yaml

```yaml
name: my-project
version: "0.1"

specs:
  - "specs/**/*.spec"      # Glob patterns for spec files

output:
  out: out/                 # Base output directory

settings:
  interactive: true         # Allow prompts during compilation
  test_coverage: high       # Test thoroughness level
```

**Note:** Language is NOT in config. It's specified via CLI flag `--lang python` or `--lang cpp`.

## The Compilation Pipeline

### Two-Pass Architecture

FreeSpec uses a two-pass compilation to support circular dependencies:

```
┌─────────────────────────────────────────────────────────────────┐
│                        PASS 1: HEADERS                          │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │student   │    │course    │    │enrollment│                  │
│  │.spec     │    │.spec     │    │.spec     │                  │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘                  │
│       │               │               │                         │
│       ▼               ▼               ▼                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │student.py│    │course.py │    │enrollment│                  │
│  │(stub)    │    │(stub)    │    │.py (stub)│                  │
│  └──────────┘    └──────────┘    └──────────┘                  │
│                                                                 │
│  All headers generated INDEPENDENTLY (no ordering needed)       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PASS 2: IMPLEMENTATIONS                      │
│                                                                 │
│  Each spec compiled with ALL headers as context                 │
│  → Circular @mentions work because all interfaces exist         │
│                                                                 │
│  For each spec:                                                 │
│  1. Generate implementation (fill in stub)                      │
│  2. Generate tests                                              │
│  3. Run tests                                                   │
│  4. If tests fail → fix and retry                              │
│  5. Review: validate exports match, spec fulfilled              │
│  6. If review fails → fix and retry                            │
└─────────────────────────────────────────────────────────────────┘
```

### What Gets Generated

For each spec, the compiler generates:

**Implementation file** (`out/{lang}/src/{category}/{name}.py`):
- Complete type hints
- All exports from the spec
- Full implementation of business logic
- Proper error handling

**Test file** (`out/{lang}/tests/{category}/test_{name}.py`):
- One test for each item in the `tests:` section
- Uses pytest (Python) or GoogleTest (C++)
- Tests must pass for compilation to succeed

### Incremental Rebuilding

The compiler tracks what needs rebuilding:

1. **Spec changed** → Regenerate header + implementation
2. **Dependency's header changed** → Regenerate implementation (transitively)
3. **Output file missing** → Regenerate

A manifest file (`out/{lang}/.freespec_build.json`) stores hashes to enable this.

## CLI Usage

```bash
# Compile for Python (default)
freespec compile

# Compile for C++
freespec compile --lang cpp

# Force full rebuild
freespec compile --force

# See what would be rebuilt
freespec compile --dry-run

# Verbose output
freespec compile -v
```

## Guidelines for AI Agents

### Writing Spec Files

1. **Be complete.** The spec must contain everything needed to implement. If it matters, write it.

2. **Be precise.** Ambiguity leads to wrong implementations. State exact rules.

3. **Test every requirement.** Each constraint in the description should have a corresponding test.

4. **Use @mentions religiously.** Every dependency must be explicitly declared.

5. **Write prose, not structure.** The description is natural language, not YAML/JSON.

6. **No implementation details.** Don't mention languages, frameworks, or code structure.

### Generating Implementations

When generating code from specs:

1. **Read the entire spec first.** Understand the full picture before writing code.

2. **Follow exports exactly.** The public API must match the exports section precisely:
   - Same names (appropriately cased for the language)
   - Same semantics
   - No additional public exports

3. **Implement all behaviors.** Every statement in the description is a requirement.

4. **Write tests for every test case.** Each bullet in `tests:` becomes a test function.

5. **Handle @mentioned dependencies.** Import and use the referenced components.

6. **Raise appropriate errors.** Failure modes in the description must raise exceptions.

### Review Criteria

After tests pass, implementations are reviewed for:

1. **Export consistency:** No new public exports added, none removed
2. **Spec fulfillment:** All described behaviors implemented
3. **Test coverage:** All test cases from spec covered
4. **Code quality:** Clean, idiomatic code for the target language

### Common Mistakes to Avoid

**In spec writing:**
- Adding extra section labels
- Structuring description with bullet points/sub-sections
- Forgetting @mentions for dependencies
- Vague test cases ("it works correctly")
- Implementation details in the spec

**In code generation:**
- Adding exports not in the spec
- Removing or renaming exports
- Ignoring edge cases described
- Not implementing all test cases
- Importing non-@mentioned dependencies

## Session Logging

The compiler logs all Claude interactions for investigation:

```
logs/{language}/compile/
├── 20250205_143052_session.log   # Human-readable full log
└── 20250205_143052_session.json  # Structured JSON for analysis
```

Each interaction records:
- Phase (header, impl, fix, review)
- Spec being compiled
- Full prompt and response
- Duration and success status
- Attempt number for retries

Use these logs to debug generation issues.

## Quick Reference

### Spec File Checklist

- [ ] Only three sections: `description:`, `exports:`, `tests:`
- [ ] No invented labels or sub-sections
- [ ] Description is natural prose
- [ ] All behavior and rules documented
- [ ] All failure modes have tests
- [ ] Every dependency has an @mention
- [ ] @mentions point to real specs
- [ ] Someone could implement without questions

### Generated Code Requirements

- [ ] All exports implemented exactly as specified
- [ ] No additional public exports
- [ ] All description behaviors implemented
- [ ] All test cases have corresponding tests
- [ ] Tests pass
- [ ] @mentioned dependencies properly imported
- [ ] Error cases raise appropriate exceptions
