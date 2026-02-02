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

exports:
- What this component provides, one per line

tests:
- Test cases that must pass, one per line
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

### exports:

One line per logical export, each starting with `-`. Each line describes
something this component provides. For services, list each action. For
entities, list create, read, update, delete operations.

Don't write signatures or types. The target language isn't known yet.
Just describe each export in plain language.

### tests:

One test case per line, each starting with `-`. These are requirements - if
any test fails, the implementation is wrong.

Cover the normal case, each way it can fail, edge cases, and security rules.

## @mentions

Reference other specs with `@path/name` inline in your text:
- `@entities/student`
- `@services/enrollment`

Use them naturally where relevant.

## What Goes In vs Out

**IN the spec:** Everything needed to implement it. If it matters, write it.

**NOT in the spec:** Implementation details, language-specific types, code structure.

## Checklist Before Finishing

- [ ] Only three sections: description:, exports:, tests:
- [ ] No invented labels or sub-sections
- [ ] Description is natural prose, not structured lists
- [ ] All behavior and rules are documented
- [ ] All failure modes have corresponding tests
- [ ] @mentions point to real specs
- [ ] Someone could implement this without asking questions
