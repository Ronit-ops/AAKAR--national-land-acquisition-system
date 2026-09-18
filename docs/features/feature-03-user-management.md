# Feature 3 — User Management

## Purpose
Secure administrative management of AAKAR platform users.

## Scope
Feature 3 provides:
- User listing, search, filtering, and pagination
- User detail viewing
- Managed user creation
- Email and full-name updates
- Account activation/deactivation
- Self-account active-status protection
- Assigned-role visibility
- Audit integration
- Protection against password/password-hash exposure

Role assignment/removal remains part of Feature 2 — RBAC.

## Frontend
- `frontend/src/App.tsx`
- `frontend/src/App.css`
- `frontend/src/lib/api.ts`
- `frontend/src/types/users.ts`

## Backend
- `backend/app/api/v1/endpoints/users.py`
- `backend/app/services/user_management_service.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/audit_service.py`
- `backend/app/schemas/users.py`

All User Management endpoints require the `system_administrator` role.

## API
Base path: `/api/v1/users`

`GET /api/v1/users`
Supports `search`, `is_active`, `offset`, and `limit`.

`GET /api/v1/users/{user_id}`
Returns profile, status, timestamps, and assigned roles.

`POST /api/v1/users`
Creates a managed user. Passwords are hashed and never returned.

`PATCH /api/v1/users/{user_id}`
Updates email and full name.

`PATCH /api/v1/users/{user_id}/status`
Activates or deactivates an account.

## Database
Uses the `users` table with unique email addresses and standard account/profile timestamps.

Audit integration uses the `audit_events` table created by:
`41252a35472d_create_audit_events.py`

## Audit Events
- `user_created`
- `user_profile_updated`
- `user_status_changed`

Audit records contain actor/target context and relevant action details. Password and password-hash data are excluded.

User mutations and their audit records are committed within the same transaction.

## Validation and Errors
Implemented handling includes:
- `401` unauthenticated access
- `403` forbidden/non-administrator access
- `404` unknown users
- `409` duplicate email
- `422` invalid request data
- `400` protected self-status changes
- `500` database/server failures

## Security
- Backend RBAC enforcement
- Hashed passwords
- No password/password-hash API exposure
- No credential data in audit details
- Database-level email uniqueness
- System administrator cannot change their own active status

## Verification
Manual frontend verification completed for:
- User Management visibility
- Create user
- Edit profile
- Deactivate user
- Activate user
- Self-status protection
- Assigned-role display

Automated backend result:
`85 passed`

Migration verification:
`alembic check`
`No new upgrade operations detected.`

## Known Limitations
Audit history UI belongs to Feature 6.
Role assignment/removal belongs to Feature 2.
Department/authority association belongs to Feature 4.
Advanced permissions belong to Feature 5.

## Completion
Feature 3 is ready for final repository commit after documentation is added.
