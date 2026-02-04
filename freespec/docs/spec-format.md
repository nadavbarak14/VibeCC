# FreeSpec Format Reference

## Structure

```
# filename.spec

description:
Free text about what this is.

exports:
- What this provides, one per line

tests:
- Test cases, one per line
```

Three sections only. No other labels.

## @mentions

Reference other specs inline: `@entities/student`, `@services/enrollment`

**Required:** You MUST @mention every spec your component depends on at least once.

## Entry Points (main)

If your spec describes an application entry point (not just a library module), mention "main" in your description. This tells the compiler to generate a runnable program, not just an importable module.

Example for a CLI app:
```
description:
Command-line interface for the course registration system.
Uses @services/enrollment to handle registrations.
The main entry point starts the CLI and handles user commands.
```

Example for an API server:
```
description:
REST API server for course registration.
Uses @api/routes to define endpoints.
The main entry point starts the HTTP server on the configured port.
```

The compiler will generate the appropriate entry point for the target language:
- Python: `main()` function with `if __name__ == "__main__":`
- Go: `func main()` in `package main`
- Rust: `fn main()`
- Node.js: Direct execution or exports for the runtime
