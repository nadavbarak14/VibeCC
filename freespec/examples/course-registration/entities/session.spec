# session.spec

description:
A session represents an authenticated login for a @entities/student. When a student successfully logs in, a session is created with a unique token they use for subsequent requests.

Sessions have an expiration time, after which they are no longer valid. The default session duration is 24 hours. Sessions can also be explicitly invalidated when the student logs out.

Each session token is a cryptographically random string that cannot be guessed. Tokens are unique across all sessions.

exports:
- Create a new session for a student
- Find a session by its token
- Check if a session is still valid
- Invalidate a session
- Invalidate all sessions for a student
- Extend a session's expiration time

tests:
- Creating a session generates a unique token
- Creating multiple sessions for the same student generates different tokens
- A newly created session is valid
- A session becomes invalid after its expiration time
- An invalidated session is no longer valid
- Finding a session by token returns the correct session
- Finding a session with an invalid token returns nothing
- Invalidating all sessions for a student invalidates all their active sessions
- Extending a session updates its expiration time
- Extending an already invalid session fails
