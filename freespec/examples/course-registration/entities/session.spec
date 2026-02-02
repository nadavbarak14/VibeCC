# session.spec

description:
An authentication session for a logged-in @entities/student. Has an id, student id, token, created at timestamp, expires at timestamp, and revoked flag.

The token is a secure random string used to authenticate API requests. Tokens are generated on login and included in subsequent requests. Sessions expire after a configurable duration, defaulting to 24 hours.

A student can have multiple active sessions, allowing login from multiple devices. Sessions can be revoked individually or all at once for a student. Revoked sessions cannot be used for authentication.

Expired sessions are kept for audit purposes but are not valid for authentication. Session validation checks both expiration and revocation status.

exports:
Create a session for a student, returning the token
Get a session by token
Validate a session token, returning the student if valid
Revoke a session
Revoke all sessions for a student
List active sessions for a student
Clean up expired sessions older than a given age

tests:
Create session generates unique token
Create session sets correct expiration
Get by token returns session
Get by invalid token returns nothing
Validate returns student for valid unexpired session
Validate returns nothing for expired session
Validate returns nothing for revoked session
Validate returns nothing for invalid token
Revoke marks session as revoked
Revoke already revoked session succeeds silently
Revoke all invalidates all sessions for student
Revoke all does not affect other students
List returns only active non-expired sessions
Cleanup removes old expired sessions
Cleanup keeps recent expired sessions
