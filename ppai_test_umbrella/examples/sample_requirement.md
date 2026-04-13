# Login and Member Setup

Actor: admin user
Acceptance: User can sign in with valid credentials and reach the dashboard.
Validation: Invalid username or password should show an error message.
Validation: Locked users cannot proceed.

The system should allow an admin to create a member from the member setup page.
Actor: admin user
Acceptance: Required fields must be validated before save.
Acceptance: Successful save should show a success toast and a generated member id.
Validation: Duplicate member data should be rejected.

The login API should return an auth token for valid users.
Validation: API should reject malformed payloads.
Validation: Response time for login should stay under 2 seconds under moderate load.

Database checks are needed to verify that member creation persists the generated member record.
