AAKAR (आकार)
National Land Acquisition & Management System
> **Shaping land. Empowering development.**
AAKAR is a production-minded digital platform being developed for
Smart India Hackathon (SIH) 2026 to support secure, transparent,
auditable, and scalable land acquisition and management workflows.
Current status: Foundation complete --- core operational development
next.
---
Current Progress
The following six features are implemented, tested, browser-verified
where applicable, and locked:
[x] Authentication
[x] Role-Based Access Control (RBAC)
[x] User Management
[x] Department & Authority Management
[x] Permission Management
[x] Audit & Activity History
The next stage begins the core operational functionality of AAKAR.
> The complete land-acquisition platform is still under active
> development. Features not listed as completed are planned or in
> development.
---
What Features 1--6 Provide
1. Authentication
Provides secure user authentication and the foundation for protected API
access.
Real-world question: Who are you?
2. Role-Based Access Control
Associates users with defined system roles and provides role-based
authorization.
Real-world question: What role do you have?
3. User Management
Allows authorized administrators to create, update, activate,
deactivate, and organize system users.
Real-world question: Who is allowed to have an AAKAR account?
4. Department & Authority Management
Models the organizational structure used by the system.
``` text
Department
    |
    +-- Authority
            |
            +-- User
```
Authorities currently support Central, State, District, and Other types.
Real-world question: Where does this user belong?
5. Permission Management
Provides fine-grained authorization in addition to roles.
Examples include:
``` text
user.read
user.create
user.update
user.activate
user.deactivate
user.organization_update

role.read
role.assign
role.remove

permission.read
permission.create
permission.update
permission.assign

department.read
department.create
department.update
department.manage_status

authority.read
authority.create
authority.update
authority.manage_status

audit.read
```
Permissions are checked at request time. Multiple active roles
contribute permissions, while inactive roles and permissions do not
grant access.
Real-world question: What exactly are you allowed to do?
6. Audit & Activity History
Records important administrative actions with:
Actor
Timestamp
Action
Entity type
Entity ID
Result
Additional context
Current event coverage includes:
``` text
user_created
user_updated
user_status_changed
user_organization_changed

department_created
department_updated
department_status_changed

authority_created
authority_updated
authority_status_changed

permission_created
permission_updated
permission_status_changed

role_permission_assigned
role_permission_removed
```
The Audit workspace supports search, actor/action/entity/result filters,
date ranges, pagination, and event details. Audit APIs are read-only.
Real-world question: Who performed an important action, what
happened, and when?
---
System Administration Foundation
Features 1--6 form the System Administration / Identity & Access
Foundation of AAKAR.
``` text
+--------------------------------------+
|       SYSTEM ADMINISTRATION          |
+--------------------------------------+
| Authentication                       |
| RBAC                                 |
| User Management                      |
| Department & Authority Management    |
| Permission Management                |
| Audit & Activity History             |
+--------------------------------------+
                    |
                    v
        Core Operational Modules
```
This foundation will support the operational land-management domain that
follows.
---
Technology Stack
Frontend
React
TypeScript
Vite
CSS
MapLibre GL for GIS capabilities
Backend
Python
FastAPI
Uvicorn
SQLAlchemy
Pydantic
Pydantic Settings
Alembic
Database
PostgreSQL
PostGIS
Security
JWT authentication
HS256
Argon2 password hashing
Role-based authorization
Permission-based authorization
Request-time authorization
Audit logging
Development
Git
GitHub
Visual Studio Code
---
Architecture
``` text
                         AAKAR
                           |
                           v
                  Authentication
                           |
                           v
                    Identity / Users
                           |
                           v
                         RBAC
                           |
                           v
              Department & Authority
                           |
                           v
                     Permissions
                           |
                           v
                  Audit & Accountability
                           |
                           v
              Core Operational Modules
                           |
                           v
                    GIS / Monitoring
                           |
                           v
                 Future AI / Intelligence
```
---
Database Foundation
The current administration layer contains entities including:
``` text
Users
Roles
User Roles
Departments
Authorities
Permissions
Role Permissions
Audit Events
```
Alembic is used for database migrations.
---
API Architecture
AAKAR uses a REST-style FastAPI backend with separated areas for:
Authentication
RBAC
User Management
Organization Management
Permissions
Audit History
Authorization is enforced by the backend. Frontend visibility is not
treated as a security boundary.
---
Verification Status
The current Feature 1--6 checkpoint has been verified with:
``` text
Backend regression:     259 passed
Backend failures:      0
Frontend ESLint:       Passed
TypeScript build:      Passed
Vite production build: Passed
Alembic check:         Passed
Browser verification:  Passed for Audit workspace
Git working tree:      Clean
```
---
Development Philosophy
A feature is not considered complete merely because its UI works.
Each feature is verified across:
``` text
Frontend
+
Backend
+
Database
+
API
+
Validation
+
Authorization
+
Business Logic
+
Error Handling
+
Integration
+
Testing
+
Security
+
Browser Verification
```
Only after these checks pass is a feature considered complete and
locked.
---
Development Workflow
``` text
Feature Specification
        |
        v
Architecture / Data Model
        |
        v
Database Migration
        |
        v
Backend
        |
        v
API + Authorization
        |
        v
Frontend
        |
        v
Integration
        |
        v
Automated Tests
        |
        v
Browser Verification
        |
        v
Regression Testing
        |
        v
Git Commit
        |
        v
GitHub Push
        |
        v
Feature Locked
```
---
Roadmap
Completed
[x] Authentication
[x] Role-Based Access Control
[x] User Management
[x] Department & Authority Management
[x] Permission Management
[x] Audit & Activity History
Next Development Stage
[ ] Core operational modules
Planned Areas
Project management
Land acquisition management
Parcel management
Landowner / right-holder information
Notifications and proceedings
Compensation management
Rehabilitation & resettlement
Possession management
GIS-based land visualization
Monitoring and reporting
Decision-support capabilities
Earth observation / geospatial intelligence
AI-assisted analysis
Planned functionality is not represented as completed functionality.
---
GIS & AI Direction
The longer-term AAKAR vision includes GIS and responsible AI
capabilities.
Potential future capabilities include:
Parcel-level change detection
Encroachment detection
Construction progress monitoring
Geospatial analysis
Risk identification
Decision support
AI is intended to be assistive, explainable, auditable, and supportive
of human decision-making.
These capabilities are planned and are not represented as fully
implemented in the current repository.
---
Security Principles
AAKAR is being developed with strong security principles:
Backend authorization
Least-privilege access
Role-based access control
Permission-based authorization
Organization-aware access
Secure password hashing
JWT-based authentication
Auditability
No secrets committed to source control
Database migrations through Alembic
API boundary validation
Explicit error handling
Read-only audit history APIs
---
Project Structure
``` text
AAKAR/
|
+-- backend/
|   +-- app/
|   |   +-- api/
|   |   +-- models/
|   |   +-- schemas/
|   |   +-- services/
|   |   +-- ...
|   |
|   +-- alembic/
|   |   +-- versions/
|   |
|   +-- tests/
|   +-- ...
|
+-- frontend/
|   +-- src/
|       +-- components/
|       +-- lib/
|       +-- types/
|       +-- ...
|
+-- README.md
```
---
Local Development
Backend
From the `backend` directory:
``` bash
alembic upgrade head
python -m pytest -q
```
Start the FastAPI application using the project's configured Uvicorn
entry point.
Frontend
From the `frontend` directory:
``` bash
npm install
npm run dev
```
Production verification:
``` bash
npm run lint
npm run build
```
---
Git Checkpoints
Important development checkpoints currently include:
``` text
a69c08a  feat(auth): complete authentication feature
991a63d  feat(user-management): complete feature 3
0ba6caa  feat(rbac): complete role-based access control
e9fc151  feat(org-management): complete feature 4
902ee34  feat: complete permission management and audit history
```
The repository uses the `main` branch.
---
Current Project Status
``` text
Features completed: 1–6
Backend tests:       259 passed
Frontend lint:       Passed
Frontend build:      Passed
Alembic check:       Passed
Working tree:        Clean
```
---
Disclaimer
AAKAR is an actively developed SIH 2026 project.
This repository represents the current development state and should not
be interpreted as a deployed government production system.
Only explicitly completed features are represented as implemented.
Remaining capabilities are under development or planned.
---
Vision
AAKAR aims to evolve into a comprehensive digital platform for land
acquisition and management built around:
``` text
Secure Identity
      +
Organizational Control
      +
Fine-Grained Authorization
      +
Auditability
      +
Operational Workflows
      +
GIS
      +
Monitoring
      +
Decision Support
      +
Responsible AI
```
> **AAKAR (आकार) --- Shaping land. Empowering development.**
