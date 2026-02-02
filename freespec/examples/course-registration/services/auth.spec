# auth.spec

description:
The auth service handles student authentication. It coordinates between @entities/student for credential verification and @entities/session for session management.

Login accepts an email and password. If the credentials are valid and the student is active, a new session is created and the token is returned. Failed login attempts should not reveal whether the email exists or the password was wrong; the error message is the same either way.

Logout invalidates the current session. It requires a valid session token.

Registration creates a new student account. It requires email, name, and password. After successful registration, the student can immediately log in.

The service enforces rate limiting on login attempts. After 5 failed attempts for the same email within 15 minutes, further attempts are temporarily blocked for that email.

exports:
- Login with email and password, returning a session token
- Logout using a session token
- Register a new student account
- Check if an email is rate-limited

tests:
- Login with correct credentials returns a session token
- Login with incorrect password fails with generic error
- Login with non-existent email fails with same generic error
- Login for inactive student fails
- Logout with valid token invalidates the session
- Logout with invalid token fails
- Logout with expired token fails
- Register with valid data creates a new student
- Register with existing email fails
- After 5 failed logins, further attempts for that email are rate-limited
- Rate limit resets after 15 minutes
- Successful login resets the failure count for that email
