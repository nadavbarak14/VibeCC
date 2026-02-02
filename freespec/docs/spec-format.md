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

