# auth.spec

description:
Authentication service for student login and logout. Coordinates between @entities/student and @entities/session to manage access to the system.

Login requires email and password. The service finds the student by email, verifies the password, and creates a new session if successful. Only active students can log in. Failed login attempts should not reveal whether the email exists.

Logout invalidates the current session. A student can also log out of all devices, which revokes all their sessions.

Token validation is used by the API layer to authenticate requests. It returns the authenticated student or indicates the token is invalid.

exports:
Login with email and password, returning session token and student info
Logout by revoking the current session token
Logout from all devices by revoking all sessions for a student
Validate a token and return the authenticated student
Get current student from a valid token

tests:
Login with valid credentials returns token and student
Login with unknown email fails with generic error
Login with wrong password fails with generic error
Login with inactive student fails
Login with suspended student fails
Login creates new session in database
Logout invalidates the session token
Logout with invalid token fails silently
Logout all revokes all sessions for student
Validate returns student for valid token
Validate returns nothing for invalid token
Validate returns nothing for expired token
Validate returns nothing for revoked token
Get current student returns student data without password
