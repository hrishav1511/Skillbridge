# SkillBridge Audit Remediation Report

## 1. Executive Summary

This remediation addresses the critical and high-priority security findings in the supplied audit while retaining the existing FastAPI, Angular, WebSocket/chat, persistence, and UI architecture. The work removes sensitive configuration from the tracked tree, closes public role escalation, authenticates WebSocket handshakes, enforces ownership and privacy boundaries, makes guest reads genuinely public and redacted, strengthens registration/review/report/media/service validation, activates moderation controls, and repairs both frontend test/build pipelines.

After the follow-up implementation documented in Section 14, the backend finishes with 101 passing tests. The public Angular suite finishes with 34 passing tests and the admin suite with 16; both production builds complete successfully. Alembic reports one head and renders the complete upgrade chain successfully in offline MySQL mode.

The principal remaining work is operational or outside this follow-up's four-feature scope: rotate credentials that were ever exposed, coordinate any history purge, preflight and run the migrations on a real database, validate S3/deployment behavior in deployed infrastructure, remediate npm dependency advisories through controlled upgrades, and complete resource metadata/editing and attachment-specific moderation. No fake payment integration or placeholder completion was added.

## 2. Branch Safety

- Starting branch: `audit_test`
- Ending branch: `audit_test`
- Starting and ending base commit before any new commit: `04a974bb6df614292c6950468e2f3d4a174603a2`
- All implementation changes were made only in the `audit_test` worktree.
- `main` was not checked out for development, modified, reset, rebased, pushed, or force-pushed.
- No branch was merged into `main`, and no pull request into `main` was created.
- Changes are intentionally left uncommitted for review.

## 3. Files Changed

### Repository and sensitive configuration

- `AUDIT_REMEDIATION_REPORT.md` — records the complete remediation scope, verification evidence, limitations, and required owner actions.
- `.gitignore` — ignores private configuration keys and the development environment file.
- `configurationKeys/accessToTheServer.txt` — removed from the tracked tree; the local ignored copy is preserved for owner-controlled cleanup/rotation.
- `configurationKeys/skillbridge-ec2` — removed the private SSH key from the tracked tree; the local ignored copy is preserved.
- `configurationKeys/skillbridge-ec2.pub` — removed the associated deployment key material from the tracked tree; the local ignored copy is preserved.
- `skillbridge-be/.env.dev` — removed sensitive environment configuration from the tracked tree; the local ignored copy is preserved.
- `skillbridge-be/.env.example` — adds a safe, non-secret configuration template.

### Admin Angular application

- `skillbridge-admin/angular.json` — disables build-time remote font optimization so production builds do not require Google Fonts access.
- `skillbridge-admin/nginx.conf` — adds production-oriented response security headers without changing the UI.
- `skillbridge-admin/src/app/app.component.spec.ts` — updates stale root-component expectations and test setup.
- `skillbridge-admin/src/app/layout/dashboard/dashboard.component.html` — integrates tutor/service report lists and existing moderation actions into the dashboard.
- `skillbridge-admin/src/app/layout/dashboard/dashboard.component.spec.ts` — updates dashboard dependencies and fixture setup.
- `skillbridge-admin/src/app/layout/dashboard/dashboard.component.ts` — loads reports and implements atomic disable/discard UI actions.
- `skillbridge-admin/src/app/layout/layout-routing.module.ts` — protects admin routes with the role guard.
- `skillbridge-admin/src/app/layout/layout.component.spec.ts` — updates test dependencies.
- `skillbridge-admin/src/app/layout/service-approval/service-approval.component.spec.ts` — repairs stale component test setup.
- `skillbridge-admin/src/app/layout/service-approval/service-approval.component.ts` — safely handles absent local authentication data.
- `skillbridge-admin/src/app/layout/sidepanel/sidepanel.component.spec.ts` — repairs stale component test setup.
- `skillbridge-admin/src/app/layout/tutor-visibility/tutor-visibility.component.html` — connects the existing visibility/status controls.
- `skillbridge-admin/src/app/layout/tutor-visibility/tutor-visibility.component.ts` — calls the account-status endpoint and refreshes displayed state.
- `skillbridge-admin/src/app/layout/user-approval/user-approval.component.spec.ts` — repairs stale component test setup.
- `skillbridge-admin/src/app/layout/user-approval/user-approval.component.ts` — safely handles absent local authentication data.
- `skillbridge-admin/src/app/login/login.component.spec.ts` — updates login test dependencies.
- `skillbridge-admin/src/app/login/login.component.ts` — uses server-issued role/token data and stores refresh state without public role discovery.
- `skillbridge-admin/src/app/resources/ApiList.ts` — adds/fixes report, logout, refresh, and moderation API paths.
- `skillbridge-admin/src/app/resources/guards/role.guard.ts` — adds authenticated admin/super-admin route enforcement.
- `skillbridge-admin/src/app/resources/interceptors/auth.interceptor.spec.ts` — supplies the current interceptor dependencies.
- `skillbridge-admin/src/app/resources/modals/approval-card/approval-card.component.spec.ts` — repairs stale modal test setup.
- `skillbridge-admin/src/app/resources/modals/approval-card/approval-card.component.ts` — safely parses optional authentication state.
- `skillbridge-admin/src/app/resources/modals/reject-card/reject-card.component.spec.ts` — repairs stale modal test setup.
- `skillbridge-admin/src/app/resources/modals/user-action/user-action.component.spec.ts` — repairs stale modal test setup.
- `skillbridge-admin/src/app/resources/modals/user-action/user-action.component.ts` — safely parses optional authentication state.
- `skillbridge-admin/src/testing/skillbridge-testing.module.ts` — provides a shared Angular test module for current Material/application dependencies.

### Backend application and database

- `skillbridge-be/src/skillbridge/api/api_v1/api.py` — mounts the logout API and preserves the existing versioned router structure.
- `skillbridge-be/src/skillbridge/api/api_v1/endpoints/auth/logout.py` — scopes refresh-token deletion to the authenticated user.
- `skillbridge-be/src/skillbridge/api/api_v1/endpoints/auth/refresh.py` — changes refresh from a URL query operation to POST body handling.
- `skillbridge-be/src/skillbridge/api/api_v1/endpoints/report.py` — enforces actor authorization and makes moderation mutations transactional.
- `skillbridge-be/src/skillbridge/api/api_v1/endpoints/review.py` — derives reviewer identity from JWT and enforces completed-booking eligibility.
- `skillbridge-be/src/skillbridge/api/api_v1/endpoints/role.py` — restricts public roles and protects role creation with admin authorization.
- `skillbridge-be/src/skillbridge/api/api_v1/endpoints/service.py` — validates service/media input and cleans newly uploaded S3 objects after persistence failures.
- `skillbridge-be/src/skillbridge/api/api_v1/endpoints/service_booking.py` — scopes booking reads by student, tutor relationship, or administrator.
- `skillbridge-be/src/skillbridge/api/api_v1/endpoints/student.py` — enforces student ownership and uses the consistent profile-picture contract.
- `skillbridge-be/src/skillbridge/api/api_v1/endpoints/tutor.py` — enforces tutor ownership, safe public access, lifecycle filters, and disables unsafe standalone creation.
- `skillbridge-be/src/skillbridge/api/api_v1/endpoints/user.py` — restricts user enumeration to administrators.
- `skillbridge-be/src/skillbridge/api/api_v1/endpoints/ws.py` — authenticates the existing WebSocket handshake and enforces identity, status, role-pair, and room membership rules.
- `skillbridge-be/src/skillbridge/api/filters/service.py` — validates search/paging and expands service/tutor/tag relevance.
- `skillbridge-be/src/skillbridge/api/filters/service_booking.py` — applies booking ownership/role filters.
- `skillbridge-be/src/skillbridge/api/filters/tutor.py` — validates searches and adds tutor/service/tag relevance while preserving existing filters.
- `skillbridge-be/src/skillbridge/api/repositories/auth/config.py` — removes hardcoded production secret fallback and supplies only a process-local development fallback.
- `skillbridge-be/src/skillbridge/api/repositories/auth/login.py` — normalizes role selection, blocks inactive accounts, and removes credential logging.
- `skillbridge-be/src/skillbridge/api/repositories/auth/register.py` — normalizes email, rejects duplicates, and limits self-registration to student/tutor roles.
- `skillbridge-be/src/skillbridge/api/repositories/auth/token.py` — validates token type, UUID, account existence/status, optional public auth, refresh ownership, and logout scope.
- `skillbridge-be/src/skillbridge/api/repositories/auth/token_verifier.py` — avoids leaking low-level token errors.
- `skillbridge-be/src/skillbridge/api/repositories/report.py` — fixes report persistence and transaction ownership.
- `skillbridge-be/src/skillbridge/api/repositories/review.py` — checks eligibility and translates duplicate-review integrity failures into conflicts.
- `skillbridge-be/src/skillbridge/api/repositories/tutor.py` — restores reachable filter options and enforces public tutor/user lifecycle conditions.
- `skillbridge-be/src/skillbridge/api/repositories/user_role_association.py` — supports safe role-association lookup and uniqueness behavior.
- `skillbridge-be/src/skillbridge/api/schemas/login.py` — makes trusted role selection optional at login rather than requiring public role discovery.
- `skillbridge-be/src/skillbridge/api/schemas/report.py` — bounds and validates report reasons.
- `skillbridge-be/src/skillbridge/api/schemas/service_booking.py` — exposes the relationship data required for scoped booking checks.
- `skillbridge-be/src/skillbridge/api/schemas/user.py` — uses validated email input and backend Fulda-domain/password constraints.
- `skillbridge-be/src/skillbridge/api/services/media_service.py` — adds incremental size checks, extension/signature agreement, and supported image/video/document signatures.
- `skillbridge-be/src/skillbridge/api/validators/login.py` — removes unsafe logging and aligns login validation.
- `skillbridge-be/src/skillbridge/api/validators/service.py` — validates required fields, bounds, dates/times, URLs, tags, and media cardinality.
- `skillbridge-be/src/skillbridge/api/validators/user.py` — enforces normalized `@hs-fulda.de` email and password requirements.
- `skillbridge-be/src/skillbridge/app.py` — honors configured CORS origins, removes the unauthenticated debug WebSocket, and keeps safe development origins.
- `skillbridge-be/src/skillbridge/database/alembic/versions/2026_09_19_1200-7ac91e2d4f60_security_and_reporting.py` — creates report tables and adds email, role-association, and review uniqueness constraints.
- `skillbridge-be/src/skillbridge/database/models/sqlalchemy/service_reviews.py` — declares one review per student/service.
- `skillbridge-be/src/skillbridge/database/models/sqlalchemy/tutor_reviews.py` — declares one review per student/tutor.
- `skillbridge-be/src/skillbridge/database/models/sqlalchemy/user_role_associations.py` — declares unique user/role membership.
- `skillbridge-be/src/skillbridge/database/models/sqlalchemy/users.py` — makes email required, unique, and indexed.
- `skillbridge-be/src/skillbridge/exceptions.py` — prevents raw internal exception text from reaching clients.
- `skillbridge-be/src/skillbridge/utils/renderer.py` — redacts guest/public user data while retaining authenticated chat identity data.

### Backend tests

- `skillbridge-be/tests/test_input_security.py` — adds search validation and MIME/content-spoofing regression coverage.
- `skillbridge-be/tests/test_jwt_uuid_validation.py` — updates the stale UUID test and covers access/refresh/account validation.
- `skillbridge-be/tests/test_registration_security.py` — covers Fulda email validation, normalization, duplicates, and registration role restrictions.
- `skillbridge-be/tests/test_role_security.py` — covers public role filtering and admin-only role creation.
- `skillbridge-be/tests/test_tags_payloads.py` — aligns tag payload coverage with the strengthened validation.
- `skillbridge-be/tests/test_tutor_account_status.py` — verifies inactive-account behavior in the tutor lifecycle.
- `skillbridge-be/tests/test_tutor_filter.py` — verifies the repaired filter-options/search behavior.
- `skillbridge-be/tests/test_tutor_revision_workflow.py` — updates ownership/revision expectations.
- `skillbridge-be/tests/test_websocket_auth.py` — covers missing, invalid, refresh, mismatched, inactive, and valid WebSocket tokens.

### Public Angular application

- `skillbridge-fe/angular.json` — disables remote font optimization for deterministic production builds.
- `skillbridge-fe/nginx.conf` — adds production-oriented response security headers without altering presentation.
- `skillbridge-fe/src/app/app.component.spec.ts` — replaces stale title expectations with current root-component tests.
- `skillbridge-fe/src/app/auth/login/login.component.spec.ts` — updates the login fixture and service dependencies.
- `skillbridge-fe/src/app/auth/login/login.component.ts` — removes credential/token logging and keeps secure auth state handling.
- `skillbridge-fe/src/app/auth/sign-in/sign-in.component.spec.ts` — repairs stale sign-in test setup.
- `skillbridge-fe/src/app/resources/Modals/attachmentts/attachmentts.component.spec.ts` — updates attachment modal dependencies.
- `skillbridge-fe/src/app/resources/Modals/book-session/book-session.component.spec.ts` — updates booking modal fixture data and dependencies.
- `skillbridge-fe/src/app/resources/Modals/chatbox/chatbox.component.spec.ts` — updates chat modal dependencies.
- `skillbridge-fe/src/app/resources/Modals/chatbox/chatbox.component.ts` — safely handles missing local authentication state.
- `skillbridge-fe/src/app/resources/Modals/my-details-card/my-details-card.component.spec.ts` — repairs stale profile-card test setup.
- `skillbridge-fe/src/app/resources/Modals/reviews/reviews.component.spec.ts` — repairs stale review modal test setup.
- `skillbridge-fe/src/app/resources/Modals/service-card/service-card.component.ts` — removes the duplicate video form upload.
- `skillbridge-fe/src/app/resources/apiLists.ts` — aligns refresh/logout/report and profile-picture API paths.
- `skillbridge-fe/src/app/resources/guards/role.guard.ts` — adds student/tutor/authenticated route enforcement while retaining guest read routes.
- `skillbridge-fe/src/app/resources/services/auth.interceptor.spec.ts` — updates interceptor error/refresh coverage dependencies.
- `skillbridge-fe/src/app/resources/services/auth.interceptor.ts` — posts refresh tokens in the body and releases queued requests correctly after refresh failure.
- `skillbridge-fe/src/app/resources/services/notification.service.spec.ts` — repairs the current notification service test setup.
- `skillbridge-fe/src/app/resources/services/socket.service.spec.ts` — tests the current chat/socket service instead of a removed service name.
- `skillbridge-fe/src/app/student/chat-list/chat-list.component.spec.ts` — repairs stale chat-list test setup.
- `skillbridge-fe/src/app/student/chat-list/chat-list.component.ts` — avoids invalid empty JSON parsing and preserves chat behavior.
- `skillbridge-fe/src/app/student/dashboard/dashboard.component.spec.ts` — updates dashboard test dependencies.
- `skillbridge-fe/src/app/student/dashboard/dashboard.component.ts` — uses a real read-only guest role without a fake authorization token/socket.
- `skillbridge-fe/src/app/student/dashboard/service-list/service-list.component.html` — displays search validation feedback in the existing layout.
- `skillbridge-fe/src/app/student/dashboard/service-list/service-list.component.spec.ts` — repairs stale service-list test setup.
- `skillbridge-fe/src/app/student/dashboard/service-list/service-list.component.ts` — validates search length/punctuation without silently rewriting input.
- `skillbridge-fe/src/app/student/dashboard/tutor-list/tutor-list.component.html` — displays search validation feedback in the existing layout.
- `skillbridge-fe/src/app/student/dashboard/tutor-list/tutor-list.component.spec.ts` — repairs stale tutor-list test setup.
- `skillbridge-fe/src/app/student/dashboard/tutor-list/tutor-list.component.ts` — validates search length/punctuation without silently rewriting input.
- `skillbridge-fe/src/app/student/payment-portal/payment-portal.component.spec.ts` — repairs the existing demo payment-screen test setup; no payment integration is claimed.
- `skillbridge-fe/src/app/student/sessions-list/sessions-list.component.spec.ts` — repairs stale session-list test setup.
- `skillbridge-fe/src/app/student/student-routing.module.ts` — applies role guards while keeping the guest search/profile path available.
- `skillbridge-fe/src/app/student/student/student.component.spec.ts` — repairs stale student-shell test setup.
- `skillbridge-fe/src/app/student/student/student.component.ts` — calls API logout and safely clears local state on completion/failure.
- `skillbridge-fe/src/app/student/view-tutor/view-tutor.component.html` — exposes report controls and hides protected actions from guests in the existing design.
- `skillbridge-fe/src/app/student/view-tutor/view-tutor.component.spec.ts` — repairs stale tutor-detail test setup.
- `skillbridge-fe/src/app/student/view-tutor/view-tutor.component.ts` — implements validated tutor/service report submission and guest-safe behavior.
- `skillbridge-fe/src/app/tutor/my-profile/my-profile.component.spec.ts` — repairs stale profile test setup.
- `skillbridge-fe/src/app/tutor/tutor-chat/tutor-chat.component.spec.ts` — repairs stale tutor-chat test setup.
- `skillbridge-fe/src/app/tutor/tutor-chat/tutor-chat.component.ts` — safely handles missing local authentication state.
- `skillbridge-fe/src/app/tutor/tutor-dashboard/tutor-dashboard.component.spec.ts` — repairs stale tutor-dashboard test setup.
- `skillbridge-fe/src/app/tutor/tutor-dashboard/tutor-dashboard.component.ts` — safely handles missing local authentication state.
- `skillbridge-fe/src/app/tutor/tutor-routing.module.ts` — protects tutor routes with the role guard.
- `skillbridge-fe/src/app/tutor/tutor.component.spec.ts` — repairs stale tutor-shell test setup.
- `skillbridge-fe/src/app/tutor/tutor.component.ts` — calls API logout and safely clears local state on completion/failure.
- `skillbridge-fe/src/testing/skillbridge-testing.module.ts` — provides reusable Angular test dependencies for current components.

## 4. Audit Finding Resolution Table

| Audit Finding | Original Severity | Status | Files Changed | Fix | Verification |
|---|---:|---|---|---|---|
| Tracked secrets/private keys | Critical | PARTIALLY FIXED | `.gitignore`, secret paths, `.env.example`, auth config | Removed from tracked tree, ignored, safe template added, unsafe production fallback removed. Historical exposure and real credential rotation remain manual. | Git index/ignore checks and targeted source inspection |
| Public role privilege escalation | Critical | FIXED | role/register/login endpoints, repositories, schemas, tests | Only student/tutor roles are public/self-registerable; role creation is admin-controlled. | Backend automated tests |
| Unauthenticated/trusting WebSocket handshake | Critical | FIXED | `ws.py`, token repository, WebSocket tests | Validates access JWT and token subject, UUID match, user existence/status, room membership, and role pair. | Backend automated tests |
| Tutor/student IDOR and ownership | High/P1 | FIXED | tutor/student/service endpoints, token repository | Owner identity is derived from authentication; foreign profile/media/revision changes are denied. | Automated suite plus code inspection |
| Fake guest authorization and unsafe exposure | High/P1 | FIXED | optional auth, renderers, tutor/service filters, Angular guest flow | Public reads work without fake credentials; protected actions remain authenticated; PII is redacted. | Automated suite, build, and code inspection |
| Fulda-only registration | High/P1 | FIXED | user schema/validator/model, register repository, migration/tests | Validated normalized email, exact domain check, duplicate handling, DB uniqueness. | Backend automated tests; live migration pending |
| Broken reporting persistence/admin flow | High/P1 | FIXED | report endpoint/repository/schema, migration, both Angular apps | Correct transactions/auth, validated reasons, student report UI, and admin moderation UI. | Repository/HTTP tests in full suite; frontend tests/builds |
| Incomplete auth lifecycle | High/P1 | FIXED | logout/refresh/token APIs, interceptors, login/logout UI, guards | Mounted scoped logout, POST body refresh, no credential logging, route guards, failed-refresh queue release. | Backend and Angular automated suites |
| Booking and user enumeration privacy | High/P1 | FIXED | booking/user endpoints and filters | Results are scoped to the student, associated tutor, or administrator; user enumeration is admin-only. | Automated suite plus code inspection |
| Tutor/service review integrity | High/P1 | FIXED | review endpoint/repository/models/migration | JWT-derived student, completed-booking eligibility, uniqueness, safe 409 handling. | Backend automated suite; migration render |
| Search validation | P1 | FIXED | base/tutor/service filters and Angular lists, tests | 40-character bound and permitted-character checks on both layers; invalid input is rejected, not rewritten. | Backend and Angular automated suites |
| Tutor search relevance | P1 | FIXED | tutor/service filters | Searches name, program/subject, tutor tags, and related service names/tags with existing query architecture. | Backend tests and code inspection |
| Public tutor approval/visibility filtering | P1 | FIXED | tutor/service endpoint/repository/filters | Direct and list reads enforce approval, visibility, linked active user, and flow-specific acceptance. | Backend automated suite |
| Tutor profile create/edit/view lifecycle | P1 | FIXED | tutor endpoint/repository and Angular profile paths | Ownership/lifecycle protected; registration path retained; unsafe orphan create endpoint returns forbidden. | Automated suite and code inspection |
| Student profile-picture route mismatch | P1 | FIXED | student endpoint and public API list | Frontend and backend use `/profile-picture/`. | Angular build/tests and code inspection |
| Unreachable tutor filter options | P1 | FIXED | tutor repository/filter tests | Method restored to reachable repository scope. | Backend automated test |
| Media upload validation/cleanup | P1 | FIXED | media service and service endpoint, tests | Incremental size caps, signatures/extensions, cardinality, ownership, and new-upload rollback cleanup. | Backend spoofing tests; live S3 blocked by environment |
| Service creation validation | P1 | FIXED | service validator/endpoint and frontend service card | Validates core fields/bounds/times/URLs/tags/media before upload; duplicate video append removed. | Backend suite and Angular build/tests |
| Account moderation not enforced | P1 | FIXED | auth/token/ws/public filters and admin visibility UI | Inactive users are blocked at login, token validation, WebSocket, public visibility, and admin state control. | Backend tests and admin tests/build |
| CORS/error/secret/security-header configuration | P1 | FIXED | app/config/exceptions and Nginx files | Uses configured origins, safe local defaults, generic errors, no production secret fallback, security headers. | Backend suite, both production builds, code inspection |
| Stale backend UUID test | P1 | FIXED | JWT UUID tests/token repository | Test now reflects strict UUID/token/account behavior without weakening validation. | 91 backend tests pass |
| Broken Angular test compilation | P1 | FIXED | component/service specs and testing modules | Updated obsolete imports/expectations and supplied real current dependencies. | Public 30 tests; admin 15 tests |
| Build-time Google Fonts dependency | P1 | FIXED | both `angular.json` files | Build-time font inlining disabled; existing typography declarations remain. | Both production builds pass |
| Advanced filtering | P2 | PARTIALLY FIXED | existing tutor/service filters and list components | Combined price, sorting, availability, text/subject/tag relevance remain/improved; no complete language/format/rating-threshold model/UI. | Tests/builds and code inspection |
| Session state workflow | P2 | FIXED | booking model/repository/endpoints and student/tutor session UI | Persisted `PENDING`, `ACCEPTED`, `DECLINED`, and `CANCELLED` states with central transition validation, participant scoping, retained history, and notifications. | Backend transition/authorization tests; Angular tests/builds |
| Rescheduling workflow/history | P2 | FIXED | reschedule model/repository/endpoints and student/tutor session UI | Persistent proposals remain pending until the other participant accepts or rejects them; acceptance atomically updates the confirmed time. | Backend reschedule/history tests; Angular tests/builds |
| Resource metadata/editing/sharing | P2 | PARTIALLY FIXED | media service and existing attachment flow | Storage access and file validation are strengthened; full title/description/subject/edit metadata is absent. | Automated suite and code inspection |
| Review reporting | P2 | FIXED | reported-review model/repository/endpoints, public review UI, admin reports queue | Authenticated reporting, duplicate protection, admin dismissal, and transactional review removal are implemented. | Backend review-report tests; public/admin tests/builds |
| Media/resource moderation | P2 | PARTIALLY FIXED | existing tutor/service revision and admin paths | Existing tutor/service moderation works; attachment-specific admin moderation is not complete. | Automated suite and code inspection |
| Notification event coverage | P2 | FIXED FOR REQUESTED EVENTS | existing notification infrastructure plus booking/chat/review/tutor/report producers | Persistent producers cover the requested chat, booking, reschedule, review, tutor moderation, and reporting events without replacing read/read-all behavior. | Backend notification/workflow/report tests; Angular tests/builds |
| Favourites | P2 | ALREADY FIXED | — | Existing implementation was retained; no verified defect justified a rewrite. | Regression suite/builds |
| Real payment integration | P2/external | MANUAL ACTION REQUIRED | — | Existing screen remains demo/mock functionality; no provider or production credentials/configuration exist. | No real payment claim made |
| Fresh/live database migration | Deployment | BLOCKED BY ENVIRONMENT | new Alembic revision | One head and full offline SQL chain verify; no disposable/live MySQL target was available for execution. | Offline render PASS; live execution not tested |

## 5. Security Fixes

- **Role registration:** public role enumeration now returns only student/tutor roles; the backend rejects arbitrary/admin role IDs during registration; role creation requires an active administrator. Admin login can select the user's existing role without relying on a public admin-role lookup.
- **WebSocket authentication:** the existing endpoint now validates signed, unexpired access JWTs, parses the UUID subject, matches it to the URL identity, confirms an active account, and applies room/member/role-pair authorization.
- **Ownership:** tutor/student profile, revision, image, cover, and service-related mutations validate the authenticated owner. The unsafe unused standalone tutor-create route is disabled without changing registration.
- **Guest API exposure:** required tutor/service reads accept anonymous requests while applying approval/status/visibility filters. Guest responses omit email, phone, and moderation/private account data; authenticated chat flows retain the minimum identity fields they require.
- **Registration:** email uses proper parsing, lowercase normalization, exact `hs-fulda.de` enforcement, duplicate conflict handling, and a database constraint. Password rules remain enforced server-side.
- **Report security:** student identity comes from the token, administrator access is required for report lists/actions, reasons are bounded, and disable/discard operations are committed atomically with report removal.
- **Review security:** reviewer identity comes from the JWT, completed-booking eligibility is checked, duplicates are constrained at both application and database layers, and database conflicts become HTTP 409 responses.
- **Privacy:** booking visibility is role/relationship-scoped and user enumeration is administrator-only.
- **Media:** size is capped while reading, supported signatures must agree with extensions, malformed/spoofed content is rejected, cardinality is bounded, and new S3 uploads are removed if service persistence fails.
- **CORS/configuration:** configured origins are honored, development defaults are explicit localhost origins, raw exception details are suppressed, deployment must supply secrets, and both Nginx configurations carry baseline browser security headers.

## 6. Database Changes

Migration `7ac91e2d4f60` (`2026_09_19_1200-7ac91e2d4f60_security_and_reporting.py`) was added on top of `21f90e7b8d11`.

It:

- creates `reported_tutors` and `reported_services` tables;
- makes `users.email` non-null;
- adds a unique/indexed email constraint;
- adds a unique user/role association constraint;
- adds one-review-per-student/tutor and one-review-per-student/service constraints;
- supplies a reversible downgrade for those changes.

`python -m alembic heads` reports exactly `7ac91e2d4f60 (head)`. The complete MySQL upgrade chain rendered successfully with `--sql`. Before running against existing data, administrators must check for null/duplicate emails, duplicate user-role rows, and duplicate reviews. A live migration was not executed because no disposable/live database target was provided.

## 7. Frontend Changes

The public application now uses true anonymous guest browsing, enforces route roles, reports tutors/services, shows search validation, uses the correct photo endpoint, sends refresh data in a POST body, releases queued requests after refresh failure, calls backend logout, and avoids unsafe token/form logging. Protected tutor/contact/review/report actions are hidden or blocked for guests as appropriate.

The admin application stores the complete issued auth state, guards protected routes, shows tutor/service reports in the existing dashboard, performs report moderation, and connects tutor account status controls to the backend.

Stale unit tests were brought in line with the current components and dependencies. Both builds no longer depend on live Google Fonts during compilation. The existing page structure, styling, colors, layouts, and navigation design were preserved; UI changes are limited to validation, guards, report controls, and wiring existing administrative actions.

## 8. WebSocket Changes

The WebSocket architecture, room model, message/history behavior, and client transport were preserved. Security was added at the existing handshake and authorization boundaries:

1. Read the token already supplied by the client.
2. Validate signature, expiry, and `access` token type.
3. Parse the JWT `sub` as a UUID and require it to equal the requested URL user.
4. Confirm the account exists and is active before accepting the connection.
5. Preserve and enforce per-message room membership.
6. Restrict new direct-room role pairs to the existing allowed student/tutor/admin relationships.
7. Restrict group creation to administrators and require every participant to exist and be active.
8. Reject authentication failures before acceptance with WebSocket close code `4401`.

The unauthenticated debug WebSocket endpoint was removed.

## 9. Tests Added/Updated

New backend test modules cover input/MIME security, registration security, role security, and WebSocket authentication. Existing JWT, tag, account-status, tutor-filter, and tutor-revision tests were updated for the hardened behavior. These tests cover valid/invalid token types and UUIDs, active status, URL/token mismatches, allowed registration roles/domains, duplicates, unauthenticated role creation, search constraints, spoofed uploads, filter options, and lifecycle rules.

Public/admin Angular specs were updated to match current service names, templates, injected dependencies, and authentication data. Shared testing modules reduce repeated Material/application setup without mocking away production behavior.

The full backend suite and both complete Angular suites—not only the new tests—were run.

## 10. Verification Results

Commands and final observed results:

```text
Branch safety:
git branch --show-current
audit_test

git rev-parse HEAD
04a974bb6df614292c6950468e2f3d4a174603a2

Backend:
.\.venv\Scripts\python.exe -m pytest -q
91 passed, 1 warning in 13.74s
Warning: pytest could not create/access the repository .pytest_cache directory.

.\.venv\Scripts\python.exe -m alembic heads
7ac91e2d4f60 (head)

.\.venv\Scripts\python.exe -m alembic upgrade head --sql
PASS — complete MySQL offline upgrade SQL rendered through 7ac91e2d4f60.

Public Angular application:
npm ci
PASS — 1,034 packages installed; npm reported 71 advisories (8 low, 26 moderate, 35 high, 2 critical).

npm test -- --watch=false --browsers=ChromeHeadless
PASS — TOTAL: 30 SUCCESS

npm run build
PASS — production build completed (hash 7e0c640389f1b47b).
Warnings remain for one CSS selector, optional/nullish template expressions, a dashboard SCSS budget, and the initial bundle budget.

Admin Angular application:
npm ci
PASS — 992 packages installed; npm reported 63 advisories (7 low, 24 moderate, 31 high, 1 critical).

npm test -- --watch=false --browsers=ChromeHeadless
PASS — TOTAL: 15 SUCCESS

npm run build
PASS — production build completed (hash 4765d4e1db73441f).
One Autoprefixer alignment warning remains.

Diff integrity:
git diff --check
PASS — no whitespace errors (Git emitted only Windows LF/CRLF conversion notices).
```

Verification classification:

- Automated test PASS: backend logic and both Angular suites.
- Build PASS: public and admin production bundles.
- Static/offline migration PASS: single head and full SQL render.
- Code inspection PASS: branch safety, route mounting/guards, CORS/header configuration, local secret ignore/index state, privacy projections, and architecture preservation.
- Blocked by environment: executing the migration against a disposable/live MySQL database, live S3 upload/rollback, deployed HTTPS/CSP behavior, browser end-to-end user journeys, and external payment behavior.

## 11. Remaining Limitations

- Credentials that appeared in Git must be treated as compromised until every affected SSH/AWS/server/application credential is rotated. Removing current tracked files does not erase history.
- Git history still contains earlier secret objects unless the owner authorizes and coordinates a history rewrite with all collaborators/remotes.
- The new migration needs data-quality preflight and execution/rollback rehearsal against a backup or disposable MySQL clone.
- Live S3 behavior and deployed AWS permissions were not available for integration testing.
- No deployed environment was available to test HTTPS/HSTS/CSP, configured production CORS origins, or end-to-end browser flows.
- npm still reports dependency advisories. Automatic `npm audit fix --force` was intentionally avoided because it can introduce breaking framework changes; upgrades need controlled regression testing.
- The public build still reports bundle/style/template warnings, although it completes successfully.
- Resource metadata/editing and attachment-specific moderation remain incomplete; the session, rescheduling, requested notification-producer, and review-reporting follow-up scope is implemented in Section 14.
- The payment portal remains demo/mock UI. No payment provider was configured, and no fake payment processing was added.
- The repository `.pytest_cache` directory has a local permission issue; tests still pass, but the owner may wish to correct/remove it outside this remediation.

## 12. P1/P2 Status After Changes

### P1

Demonstrably completed P1 work includes public-role containment, WebSocket authentication, owner checks, guest-safe reads, Fulda registration enforcement, reporting persistence/UI, auth refresh/logout/guards, booking and user privacy, review integrity, consistent search validation/relevance, public lifecycle filtering, tutor profile lifecycle protection, photo-route repair, filter-options repair, media validation/rollback, service validation, account-status enforcement, CORS/error/security configuration, and test/build repair.

These claims are supported by automated tests/builds where available and otherwise explicitly by code inspection. Live infrastructure-dependent behavior remains classified separately rather than being presented as tested.

### P2

- Advanced filters: partial; current combined subject/text/tags, price, sorting, and availability behavior is preserved/improved, but language, tutoring-format, and complete rating filters need data/UI support.
- Session workflow: implemented; persisted states, centrally validated transitions, role-scoped actions, cancellation history, notifications, and existing-style student/tutor controls are present.
- Rescheduling: implemented; persistent participant proposals, recipient-only accept/reject, atomic confirmed-time updates, history, notifications, and UI controls are present.
- Resource metadata/sharing: partial; security/storage behavior is stronger, but required editable metadata is incomplete.
- Review reporting: implemented; reviews are authenticated report targets and the existing admin reports area supports dismissal and review removal.
- Media/resource moderation: partial; tutor/service revision moderation exists, but attachment-specific moderation is incomplete.
- Notifications: all events requested by the follow-up are implemented using the existing persistence/read-state and WebSocket delivery architecture.
- Favourites: already working and intentionally not rewritten.
- Payments: no real provider exists; the demo screen is not represented as production payment support.

No percentage is assigned because completeness depends on unimplemented product decisions and unavailable deployment verification.

## 13. Manual Actions Required

1. Immediately rotate every exposed server password, SSH key pair, AWS access key, database credential, JWT secret, and any other value that was stored in the removed files. Revoke the old values.
2. Update GitHub/repository secrets, CI/CD variables, EC2/server configuration, application hosting variables, and developer environments with the rotated values. Never copy real values into `.env.example`.
3. Decide whether to authorize a coordinated Git history purge (for example with `git filter-repo`). This requires communication and fresh clones/rebases for every collaborator; it was not performed here.
4. Set a strong production JWT/application secret and explicit production CORS origin list. Confirm development fallback behavior cannot be selected in production.
5. Back up the database; query and resolve null/duplicate emails, duplicate user-role associations, and duplicate tutor/service reviews; then run and rehearse revision `7ac91e2d4f60` against a staging clone before production.
6. Run live S3 upload, signature rejection, rollback cleanup, and IAM access tests in staging.
7. Verify CSP, HSTS, frame protection, CORS, guest flows, login/logout/refresh, WebSockets, reporting, moderation, and media workflows in the deployed HTTPS environment.
8. Plan controlled Angular/npm dependency upgrades for the reported advisories, followed by both complete test suites and production builds.
9. Product-design and implement the remaining P2 resource metadata/editing and attachment-specific moderation requirements if they remain in scope.
10. Keep the payment portal labelled/treated as demo functionality unless a real provider, threat model, compliance plan, webhook validation, and secure server-side integration are deliberately commissioned.

No changes were merged into `main`.

## 14. Follow-up Implementation — Session Workflow, Rescheduling, Notifications and Review Reporting

This section supersedes the earlier P2 status and test-count statements for these four areas. The follow-up started on `audit_test` at commit `5105f457dcc478820adc7655230d617911ac1738`; all changes remain in that worktree and were not merged into `main`.

### Session Workflow

- The existing `service_bookings` model now persists one of `PENDING`, `ACCEPTED`, `DECLINED`, or `CANCELLED`, plus the confirmed `scheduled_start_at`, status-update timestamp, and cancellation actor/reason metadata.
- One transition map is the source of truth: `PENDING -> ACCEPTED`, `PENDING -> DECLINED`, `PENDING -> CANCELLED`, and `ACCEPTED -> CANCELLED`. `DECLINED` and `CANCELLED` are terminal. Invalid or repeated transitions return HTTP 409.
- Creation derives the student from the authenticated user, validates the service, tutor approval/activity/request acceptance, and future requested time, then creates a `PENDING` booking and tutor notification in one transaction.
- Tutor accept/decline operations verify ownership through the booked service. Student/tutor/admin cancellation is participant- or role-scoped and retains the row rather than deleting it. Row locks and in-transaction state checks protect competing state changes.
- The service-booking API retains the existing create/list routes and adds `PATCH /{booking_id}/accept/`, `PATCH /{booking_id}/decline/`, and stateful `DELETE /{booking_id}/`. List responses expose the persisted state and confirmed time; meeting links are returned only for accepted bookings.
- The existing student sessions list and tutor dashboard display status and confirmed time and add only the applicable accept, decline, cancel, and reschedule actions. No page or style-system redesign was introduced.

### Rescheduling

- `booking_reschedule_proposals` stores booking, proposer, previous and proposed start times, `PENDING`/`ACCEPTED`/`REJECTED` status, creation/response timestamps, and responding user.
- Only the booking's student or associated tutor may propose, view history, or respond. The proposer cannot respond to their own proposal; only the other participant can accept or reject it.
- Proposals require an accepted booking, a future time, and no existing unresolved proposal. A proposal never changes the confirmed booking time by itself.
- Acceptance locks and revalidates the booking/proposal, updates the confirmed booking time and proposal state atomically, and notifies the proposer. Rejection persists the rejected state without changing the booking time and notifies the proposer. Repeated responses return HTTP 409.
- Routes are `POST /{booking_id}/reschedule/`, `PATCH /{booking_id}/reschedule/{proposal_id}/accept/`, `PATCH /{booking_id}/reschedule/{proposal_id}/reject/`, and `GET /{booking_id}/reschedule/`. The existing student and tutor views expose proposal/response controls and persisted history.

### Notifications

All producers use the existing notification table, read/read-all APIs, and best-effort WebSocket delivery. Domain changes and persistent notification creation share a transaction where practical; live delivery occurs only after commit. Chat retries use a client-generated message UUID and a database uniqueness constraint so the same event does not create another message or notification.

| Event | Recipient | Producer Location | Implemented | Test |
| ----- | --------- | ----------------- | ----------- | ---- |
| New chat message (`CHAT_MESSAGE_RECEIVED`) | Other chat member(s), never sender | `api/repositories/chat.py` and existing WebSocket endpoint | Yes, retry-idempotent | `tests/test_notifications.py` |
| Session request (`SESSION_REQUESTED`) | Service tutor | `api/repositories/service_booking.py` | Yes | `tests/test_session_workflow.py` |
| Session accepted (`SESSION_ACCEPTED`) | Booking student | `api/repositories/service_booking.py` | Yes | `tests/test_session_workflow.py` |
| Session declined (`SESSION_DECLINED`) | Booking student | `api/repositories/service_booking.py` | Yes | `tests/test_session_workflow.py` |
| Session cancelled (`SESSION_CANCELLED`) | Other booking participant | `api/repositories/service_booking.py` | Yes | `tests/test_service_booking_cancellation.py`, `tests/test_session_workflow.py` |
| Reschedule proposed (`RESCHEDULE_PROPOSED`) | Other booking participant | `api/repositories/service_booking.py` | Yes | `tests/test_session_workflow.py` |
| Reschedule accepted (`RESCHEDULE_ACCEPTED`) | Proposal creator | `api/repositories/service_booking.py` | Yes | `tests/test_session_workflow.py` |
| Reschedule rejected (`RESCHEDULE_REJECTED`) | Proposal creator | `api/repositories/service_booking.py` | Yes | `tests/test_session_workflow.py` |
| Tutor review created (`TUTOR_REVIEW_CREATED`) | Reviewed tutor | `api/repositories/review.py` | Yes | `tests/test_notifications.py` |
| Service review created (`SERVICE_REVIEW_CREATED`) | Service tutor | `api/repositories/review.py` | Yes | `tests/test_notifications.py` |
| Tutor profile approved (`TUTOR_PROFILE_APPROVED`) | Tutor | `api/repositories/tutor.py` | Yes | `tests/test_tutor_revision_workflow.py` |
| Tutor profile rejected (`TUTOR_PROFILE_REJECTED`) | Tutor | `api/repositories/tutor.py` | Yes | `tests/test_tutor_revision_workflow.py` |
| Tutor report created (`TUTOR_REPORTED`) | Active administrators | `api/repositories/report.py` | Yes | `tests/test_user_reporting.py` |
| Service report created (`SERVICE_REPORTED`) | Active administrators | `api/repositories/report.py` | Yes | `tests/test_user_reporting.py` |
| Review report created (`REVIEW_REPORTED`) | Active administrators | `api/repositories/report.py` | Yes | `tests/test_review_reporting.py` |
| Tutor/service disabled after report | Affected tutor | report moderation endpoints | Yes | Backend reporting regression tests and code inspection |
| Review report dismissed (`REVIEW_REPORT_DISMISSED`) | Reporter | `api/repositories/report.py` | Yes | `tests/test_review_reporting.py` |
| Reported review removed (`REVIEW_REMOVED`) | Review author | `api/repositories/report.py` | Yes | `tests/test_review_reporting.py` |

### Review Reporting

- `reported_reviews` extends the existing reporting domain with an authenticated reporter user, exactly one tutor-review or service-review target, reason, timestamp, useful indexes, foreign keys, and per-reporter/per-target uniqueness constraints.
- `POST /report/review/{review_type}/{review_id}/` derives the reporter from JWT, validates and trims a bounded non-empty reason, checks target existence, and rejects duplicates. Guests cannot submit.
- The existing review card adds a small authenticated report action with reason validation and success/error feedback; it is hidden from guests.
- The existing admin reports area now loads reported reviews with review text, rating, reason, and timestamp. `GET /report/review/` is admin-only.
- `DELETE /report/review/{report_id}/` dismisses the report while retaining the review. `DELETE /report/review/{report_id}/review/` transactionally removes the target review and all associated reports. Existing rating queries are computed from persisted reviews, so they immediately reflect removal. Non-admin moderation is denied.

### Database

- New revision: `a81d2f3c4b5e` (`2026_09_19_1800-a81d2f3c4b5e_session_workflow_and_review_reports.py`), following `7ac91e2d4f60`.
- `service_bookings`: constrained/non-null status, confirmed start time, status/cancellation timestamps, cancellation actor/reason, foreign key, and lookup indexes.
- `booking_reschedule_proposals`: participant proposal/history table with proposal-state checks, foreign keys, timestamps, and booking/status indexes.
- `reported_reviews`: review report table with exactly-one-target check, reporter/target uniqueness constraints, foreign keys, and moderation queue indexes.
- `chat_messages`: nullable `client_message_id` plus `(sender_id, client_message_id)` unique constraint and lookup index for retry idempotency. Existing clients remain compatible because the column is nullable.
- Legacy booking decision: existing rows are backfilled as `ACCEPTED`, because the old model represented already-booked sessions rather than pending requests. Confirmed start timestamps are backfilled from the existing service date/time before the column becomes non-null.
- Verification: `python -m alembic heads` reports the single head `a81d2f3c4b5e`; `python -m alembic upgrade head --sql` renders the entire MySQL chain successfully. No disposable/live MySQL database was available, so live execution and rollback rehearsal remain blocked by environment.

### Tests and Builds

Final commands run on 2026-09-19:

| Area | Exact command | Result |
| ---- | ------------- | ------ |
| Backend | `cd skillbridge-be; .\\.venv\\Scripts\\python.exe -m pytest -q` | PASS — 101 passed, 0 failed, 1 existing cache-permission warning |
| Public Angular | `cd skillbridge-fe; npm test -- --watch=false --browsers=ChromeHeadless` | PASS — 34 SUCCESS, 0 failed |
| Admin Angular | `cd skillbridge-admin; npm test -- --watch=false --browsers=ChromeHeadless` | PASS — 16 SUCCESS, 0 failed |
| Public production build | `cd skillbridge-fe; npm run build` | PASS — hash `e4b1c71d232df980`; existing budget/template/autoprefixer warnings remain |
| Admin production build | `cd skillbridge-admin; npm run build` | PASS — hash `99702efe8f2eeae1`; existing autoprefixer warning remains |
| Alembic head | `cd skillbridge-be; .\\.venv\\Scripts\\python.exe -m alembic heads` | PASS — one head: `a81d2f3c4b5e` |
| Migration SQL render | `cd skillbridge-be; .\\.venv\\Scripts\\python.exe -m alembic upgrade head --sql` | PASS — complete MySQL upgrade chain rendered |
| Diff integrity | `git diff --check` | PASS after documentation update; line-ending conversion notices are informational |

### Follow-up Remaining Limitations

- Migration SQL was rendered against the configured MySQL dialect, but the revision was not executed or rolled back against a disposable/live MySQL instance because one was not available.
- Browser component tests and production builds passed; no deployed end-to-end environment was available for multi-user WebSocket, notification delivery, or simultaneous-request load testing.
- Row locks, uniqueness constraints, transaction boundaries, and HTTP 409 state revalidation cover the identified races, but real-database concurrency stress testing remains an operational follow-up.
- Existing public bundle-size, template, CSS/autoprefixer, npm advisory, and local pytest cache-permission warnings remain; they were not broadened into this feature-only change.
- Resource metadata/editing, attachment-specific moderation, and real payment integration remain outside this follow-up scope.
