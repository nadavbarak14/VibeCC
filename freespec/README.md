# FreeSpec

A specification-level meta-language where AI interprets structured natural language specs to generate code.

## Philosophy

FreeSpec is **not** a traditional programming language. It's a spec-level language where:

1. **Humans write** structured specifications in natural language
2. **AI interprets** specs during planning (interactive, questions allowed)
3. **Compilation** generates: API headers → verified imports → implementation + tests

## Quick Start

1. Create a `freespec.yaml` manifest in your project root
2. Write `.spec` files describing your components
3. Use `@mentions` to reference dependencies between specs
4. Run the FreeSpec compiler to generate code

## Spec File Format

```
# component.spec

## Description
High-level overview of what this component does.
Implementation details, algorithms, business rules.

## API
Contract-level interface definitions.
- functionName(params) -> ReturnType: Description

## Tests
Free-form use cases that MUST be fulfilled:
- Must handle: specific scenarios
- Should reject: error conditions

## Mentions
@dependency1, @dependency2
```

## Project Structure

```
your-project/
├── freespec.yaml           # Manifest
├── specs/
│   ├── domain/
│   │   ├── entity.spec
│   │   └── service.spec
│   └── ...
└── generated/              # Output directory
    ├── api/
    ├── src/
    └── tests/
```

## Compilation Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  .spec      │ ──▶ │ API Headers  │ ──▶ │ Verify      │ ──▶ │ Generate     │
│  files      │     │ (signatures) │     │ Imports     │     │ Code + Tests │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
```

## Documentation

- [Spec Format Reference](docs/spec-format.md) - Complete format specification
- [Examples](examples/) - Sample spec files

## Examples

See the [course-registration](examples/course-registration/) example for a complete domain model.
