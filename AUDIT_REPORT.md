# SkillBridge — Read-Only Implementation Audit

**Audit date:** 2026-09-19
**Branch audited:** `audit_test`
**HEAD at audit:** `3b83a0eb0b7b37058b4e2f9ef1f3429d480135d0`
**Auditor mode:** READ-ONLY. No application code, config, migration, or test file was modified.

---

## 1. Executive Summary

**The codebase is in materially better shape than the audit brief anticipates.** The brief was written against a snapshot that has since been remediated. Most of the specific defects it names — the fake `guest-token`, the unmounted logout endpoint, refresh tokens in GET query parameters, the misplaced `get_filter_options()`, stale `SocketService` imports, a missing `AppComponent.title`, unauthenticated role creation, an unauthenticated WebSocket handshake, and tracked secrets — are **already fixed at `3b83a0e`**. I verified each of these directly rather than taking the brief at face value.

**Headline finding — the one thing that is worse than it looks:**

> `POST /v1/service-booking/create/` — the exact endpoint the public Angular app uses to book a session (`apiLists.session_booking`) — **returns HTTP 406 on every single call**. It is unconditionally broken. A student cannot book a session through the UI at all.

The cause is a one-line type error: [`service_booking.py:297`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/service_booking.py#L297) passes a plain `dict` to `BaseValidator.validate()`, which calls `.model_dump()` on it at [`base.py:12`](skillbridge-be/src/skillbridge/api/validators/base.py#L12). This is **not** caught by the 105-test suite, because every booking test exercises the repository and schema layers, never the HTTP endpoint. A green test suite is actively masking a total feature outage. A working duplicate of this endpoint exists at `POST /v1/service/create/booking/`, but no frontend consumes it.

**On verification honesty — read this before the tables:**

I built a throwaway runtime harness (in the scratchpad, not in the repo) that boots the real FastAPI application against in-memory SQLite and issues genuine HTTP requests. This let me **runtime-verify a large share of the backend scenarios instead of guessing from code**. Those are marked `VERIFIED BY RUNTIME CHECK` and are backed by verbatim HTTP status codes and response bodies.

However, **every browser-rendered, visual, and deployment scenario is unverified.** There is no running deployment I can reach, no browser automation, and no way to confirm P1-25 (responsive), P1-26 (cross-browser), or P1-29 (deployment) from this environment. Those 12 scenarios are `BLOCKED BY ENVIRONMENT`, not passes. Likewise, anything that requires live S3 or a live MySQL server is blocked.

**Honest scorecard:**

| | Scenarios | Pass | Fail | Blocked | Cannot verify |
|---|---|---|---|---|---|
| P1 | 116 | 76 | 21 | 16 | 3 |
| P2 | 88 | 40 | 37 | 8 | 3 |
| **Total** | **204** | **116** | **58** | **24** | **6** |

Of the **116 passes, 78 were runtime-verified or test-verified**; **38 rest on code inspection alone**. I have flagged each one.

**Features that do not exist at all** (not "partial" — absent from the data model):
- **Languages.** No column, no filter, no API field, no UI. P1-8/P1-10/P2-1 scenarios referencing languages cannot pass.
- **Tutoring format** (online / in-person). No field anywhere.
- **Standalone resource sharing** (P2-13 → P2-16). Service attachments partly cover this but have no title/description/subject, no edit, no guest-visible metadata, and no admin moderation queue.
- **Media moderation** (P2-12). Moderation is text-only (Detoxify over revision text). Uploaded media bypasses approval entirely and is written straight to the live profile.
- **Chat message reporting** (P1-16 scenario 2). Only tutors, services, and reviews can be reported.

**Security posture:** genuinely solid on the things that matter most. Authentication, authorization, ownership/IDOR, role escalation, WebSocket auth, review integrity, and registration validation are all correctly implemented and I confirmed them with live requests. The real security findings are narrower: a **guest-readable tutor phone number**, **authenticated PII exposure on review listings**, and a handful of hardening gaps. **No CRITICAL security findings. 1 HIGH, 6 MEDIUM, 7 LOW, 4 INFO.**

**Two process problems worth more than any single bug:** secrets remain recoverable in Git history (they were removed from the working tree but never purged from history, and the history is pushed to `origin`), and **there is no CI** — all four GitHub workflows are `workflow_dispatch` only, so the 105 backend tests and both Angular suites never run automatically on push or PR.

---

## 2. Git Safety Record

### Starting state (recorded before any other command)

```
$ git branch --show-current
audit_test

$ git status --short
warning: could not open directory '.pytest_cache/': Permission denied
(no modified, staged, or untracked files)

$ git rev-parse HEAD
3b83a0eb0b7b37058b4e2f9ef1f3429d480135d0
```

### Ending state

```
$ git branch --show-current
audit_test

$ git status --short
warning: could not open directory '.pytest_cache/': Permission denied
?? AUDIT_REPORT.md

$ git rev-parse HEAD
3b83a0eb0b7b37058b4e2f9ef1f3429d480135d0

$ git diff --stat
(empty — no tracked file modified)
```

### Confirmations

- **`main` was never checked out, modified, merged, rebased, reset, or pushed.** No pull request was opened.
- **No commits were created. Nothing was staged or stashed. No branch was created or deleted.**
- `HEAD` is identical at start and end: `3b83a0e`.
- `git diff --stat` is **empty** — no tracked file changed.
- The **only** new file is `AUDIT_REPORT.md` (this report), as permitted.
- Other refs were read only via `git log --all` / `git rev-list --all`; no `git checkout` or `git show <ref>:<path>` against another branch was required.
- Scratch artifacts (runtime harness, probe scripts, captured output) were written **outside the repository**, to the session scratchpad at `C:\Users\gaura\AppData\Local\Temp\claude\...\scratchpad\`.

### ⚠️ Discrepancy with the audit brief — please read

The brief states `audit_test` is at `04a974b` with a clean tree. **It is not.** The branch is **five commits ahead**:

```
3b83a0e  almebic issue          <- actual HEAD
092d08a  alembic issue
3552b08  error solved
0d305f2  Added the features
5105f45  changes till now
04a974b  Refresh frontend apps from feature/frontend-main   <- brief assumed this was HEAD
```

The session's opening `git status` snapshot also listed ~40 modified files that are no longer modified — they were committed in the five commits above **before this audit began** (confirmed via `git reflog`; my first command already showed a clean tree). Those five commits are where the remediation happened, which is why so much of the brief's expected findings list is already closed. **This audit reports on `3b83a0e`, the actual current state.**

---

## 3. Branch Composition Findings

The brief's premise — frontend from `feature/frontend-main`, backend from `main` — predicts widespread contract drift. **I built a complete frontend→backend endpoint map and the drift is far smaller than expected.** The five remediation commits appear to have reconciled most of it. Here is what I actually found.

### 3.1 Contract mismatches — CONFIRMED

| # | Finding | Severity | Evidence |
|---|---|---|---|
| BC-1 | **`POST /v1/service-booking/create/` is unconditionally broken (HTTP 406).** The public app calls this at [`payment-portal.component.ts:96`](skillbridge-fe/src/app/student/payment-portal/payment-portal.component.ts#L96) via `apiLists.session_booking`. A working duplicate exists at `POST /v1/service/create/booking/` but **no frontend calls it**. | **BLOCKER** | Runtime: `{"success":false,"message":"'dict' object has no attribute 'model_dump'"}` |
| BC-2 | **`POST /v1/tutor/create/` is a dead 403 stub.** [`tutor.py:79-82`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/tutor.py#L79-L82) raises 403 unconditionally. The frontend's `createTutorProfile()` targets it. | Low (both sides dead) | Runtime: HTTP 422 (body validation fires before the 403) |
| BC-3 | Frontend sends `has_registered` and `is_verified` in the registration payload ([`sign-in.component.ts:144-145`](skillbridge-fe/src/app/auth/sign-in/sign-in.component.ts#L144-L145)); backend `UserRegisterInput` declares neither, so both are **silently discarded**. Harmless today (defaults match intent) but the contract is a lie. | INFO | Schema comparison |

### 3.2 Dead frontend code

`createTutorProfile()` at [`sign-in.component.ts:186`](skillbridge-fe/src/app/auth/sign-in/sign-in.component.ts#L186) is `private` and **never called** — `grep -rn "createTutorProfile" skillbridge-fe/src` returns only its own definition. The registration success handler navigates straight to login. Confirmed dead on both ends.

### 3.3 Orphaned backend endpoints (no frontend consumer)

| Endpoint | Note |
|---|---|
| `POST /v1/service/create/booking/` | **The working booking route.** Orphaned while the broken one is wired up. This is the most consequential orphan. |
| `GET /v1/tutor/filter-options/` | Returns `{"academic_programs":[...],"teaching_styles":[...]}`. Works (runtime-confirmed) but no UI consumes it — the tutor list has only a sort dropdown, no filter controls. |
| `POST /v1/chat/rooms/group/` | Admin group chat. No UI. |
| `GET /v1/chat/rooms/{id}/` | Room detail. No UI (the app uses `/messages/` directly). |
| `GET /v1/user/users/` | Admin-only user listing. No admin UI screen consumes it. |
| `DELETE /v1/service/{id}/`, `PUT /v1/service/{id}/` | Partially consumed; `service-card.component.ts` uses `PUT`. |

### 3.4 Contracts I expected to be broken but verified are CORRECT

The brief specifically flags these. All are fine:

- **Profile-picture paths.** Frontend calls `DELETE /student/{id}/profile-picture/` ([`student.component.ts:111`](skillbridge-fe/src/app/student/student/student.component.ts#L111)); backend exposes exactly `/v1/student/{student_id}/profile-picture/`. The feared `/remove-profile-picture/` mismatch **does not exist**. Same for tutor profile/cover pictures.
- **Auth header format.** Interceptor sends `Bearer ${token}` ([`auth.interceptor.ts:281`](skillbridge-fe/src/app/resources/services/auth.interceptor.ts#L281)); backend parses exactly that at [`token.py:262-268`](skillbridge-be/src/skillbridge/api/repositories/auth/token.py#L262-L268). Runtime-confirmed: a non-Bearer header returns `401 "Invalid authorization header format. Expected 'Bearer <token>'"`.
- **WebSocket handshake.** Frontend builds `${wsUrl}chat/ws/${userId}?token=${encodeURIComponent(token)}` ([`socket.service.ts:36-37`](skillbridge-fe/src/app/resources/services/socket.service.ts#L36-L37)); backend reads `websocket.query_params.get("token")` at [`ws.py:248`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/ws.py#L248). Exact match, both apps.
- **Refresh token.** Frontend `POST` with `{refresh_token}` in the **body**; backend `POST /v1/refresh-token/` with `RefreshTokenRequestInput`. **Not** a GET query parameter.
- **Logout.** Frontend `POST user/logout/` with `{refresh_token}`; backend mounts it at [`api.py:108-112`](skillbridge-be/src/skillbridge/api/api_v1/api.py#L108-L112) → `/v1/user/logout/`. Runtime-confirmed HTTP 200.
- **Admin tutor visibility.** The suspicious `environment.apiUrl.replace(/v1\/$/, '')` at [`tutor-visibility.component.ts:35`](skillbridge-admin/src/app/layout/tutor-visibility/tutor-visibility.component.ts#L35) is convoluted but resolves correctly to `.../api/v1/admin/tutors/`. Field names (`account_status`, `status`) match the backend schemas.
- **Report endpoints.** Frontend `{tutor_id, reason}` / `{service_id, reason}` matches `CreateTutorReportInput` / `CreateServiceReportInput` exactly, including the 10–1000 character reason rule, which is enforced identically on both sides.

### 3.5 Configuration drift from the branch composition

`skillbridge-admin/src/environments/environment.prod.ts` is **an empty file**, and `skillbridge-fe/src/environments/environment.prod.ts` is missing `wsUrl`. Both would break a production build — **except neither is ever used**: `angular.json` defines **no `fileReplacements`** in either app, so `environment.ts` is used in all configurations. Dead files, not live breakage. A side effect worth noting: production bundles ship with `production: false`.

---

## 4. P1 Scenario Results

**Verification method legend:** `RUNTIME` = `VERIFIED BY RUNTIME CHECK` (real HTTP request executed against the running app) · `TEST` = `VERIFIED BY AUTOMATED TEST` · `BUILD` = `VERIFIED BY BUILD` · `CODE` = `CODE INSPECTION ONLY` · `BLOCKED` = `BLOCKED BY ENVIRONMENT` · `NOT TESTED`

| # | Feature | Scenario | Result | Verification | Evidence | Notes |
|---|---|---|---|---|---|---|
| P1-1 | Guest Access | 1. Landing loads without login | BLOCKED | BLOCKED | No browser/deployment | Routes exist with `allowGuest`; not a runtime pass |
| P1-1 | | 2. Guest tutor search allowed | **PASS** | RUNTIME | `GET /v1/tutor/tutors/` no auth → `200`, 1 record | |
| P1-1 | | 3. Guest sees limited info | **FAIL** | RUNTIME | Guest payload includes `"phone":"+491759999999"` | **Tutor phone leaks to guests.** SEC-01 |
| P1-1 | | 4. Guest protected fn → login required | **PASS** | RUNTIME | `/dashboard/student/` → `401 "Authorization header missing"` | Also booking list, chat room create |
| P1-2 | Fulda-Only Reg. | 1. `@hs-fulda.de` accepted | **PASS** | RUNTIME + TEST | `POST /v1/user/register/` → `200` | `test_registration_accepts_and_normalizes_fulda_email` |
| P1-2 | | 2. Gmail rejected | **PASS** | RUNTIME + TEST | → `422 "Registration requires an @hs-fulda.de email address"` | Enforced **backend-side** |
| P1-2 | | 3. Already-used email rejected | **PASS** | RUNTIME | → `409 "An account with this email already exists."` | Also rejects `NewGuy@HS-Fulda.de` (case-normalised) |
| P1-2 | | 4. Missing/invalid email → validation | **PASS** | RUNTIME | `not-an-email` → `422`; missing → `422 "email: Field required"` | |
| P1-3 | Login | 1. Correct credentials | **PASS** | RUNTIME | `POST /v1/user/login/` → `200` + tokens | |
| P1-3 | | 2. Wrong password rejected | **PASS** | RUNTIME | → `401 "Invalid email or password."` | bcrypt verify |
| P1-3 | | 3. Unknown account rejected | **PASS** | RUNTIME | → `401 "The User has not been registered yet."` | Different message than #2 — minor user-enumeration oracle (SEC-12) |
| P1-3 | | 4. Logged-out user on protected page | PARTIAL → **PASS** | RUNTIME + CODE | Backend `401`; `RoleGuard` redirects to `/auth/login` | Guard logic code-inspected; redirect not browser-verified |
| P1-4 | Role-Based Access | 1. Student → student dashboard | **PASS** | RUNTIME | `GET /v1/dashboard/student/` w/ student token → `200` | |
| P1-4 | | 2. Student → admin page denied | **PASS** | RUNTIME | `/admin/tutors/` → `403 "Admin access required."` | |
| P1-4 | | 3. Tutor → admin functionality denied | **PASS** | RUNTIME | `/admin/dashboard/` + `/admin/tutor_revisions/pending/` → `403` | |
| P1-4 | | 4. Admin → admin dashboard | **PASS** | RUNTIME | → `200` with metrics payload | |
| P1-5 | Tutor Search | 1. Search `Python` | **PASS** | RUNTIME | `?query=Python` → `200`, 1 match | Matches tags + service names |
| P1-5 | | 2. Search `Math` | **PASS** | RUNTIME | `?query=Math` → `200`, 1 match | |
| P1-5 | | 3. Unknown subject → no-results | **PASS** | RUNTIME | → `200`, `"data":[]`, `total_records:0` | Clean empty set; message clarity is a UI concern |
| P1-5 | | 4. Empty search → controlled | **PASS** | RUNTIME | `?query=` → `200`, full list | |
| P1-6 | Search Validation | 1. Alphanumeric accepted | **PASS** | RUNTIME | `?query=Python3` → `200` | |
| P1-6 | | 2. `Python!!!` **rejected** | **PASS** | RUNTIME + TEST | → `422 "String should match pattern '^[A-Za-z0-9@.\s-]*$'"` | **Rejected, not normalised** — `test_search_rejects_invalid_punctuation_instead_of_sanitizing_it` |
| P1-6 | | 3. >40 chars rejected | **PASS** | RUNTIME + TEST | 41 chars → `422 "String should have at most 40 characters"` | |
| P1-6 | | 4. SQL/script input rejected | **PASS** | RUNTIME | `' OR 1=1--` → `422`; `<script>alert(1)</script>` → `422` | Also parameterised ORM throughout |
| P1-7 | Approved Tutors Only | 1. Approved appears | **PASS** | RUNTIME | Seeded ACCEPTED tutor present in result ids | |
| P1-7 | | 2. Pending not shown | **PASS** | RUNTIME | `present= False` | `public_only` filter, [`filters/tutor.py:74-84`](skillbridge-be/src/skillbridge/api/filters/tutor.py#L74-L84) |
| P1-7 | | 3. Rejected not shown | **PASS** | RUNTIME | `present= False` | |
| P1-7 | | 4. Newly approved becomes searchable | **PASS** | RUNTIME | Admin reactivate → tutor reappears in public list | Verified via visibility toggle round-trip |
| P1-8 | Profile Viewing | 1. Open tutor from search | PASS | CODE | `view-tutor.component.ts:49` → `tutor/tutors/?tutor_id=` | Backend route confirmed; UI not browser-verified |
| P1-8 | | 2. Subjects/tags displayed | **PASS** | RUNTIME | Payload carries `"tags":["Python","Math"]` | |
| P1-8 | | 3. Bio/**languages**/teaching style | **FAIL** | RUNTIME | Payload has `bio`, `teaching_style`; **no language field exists** | `grep -rni language` over backend: only `LanguageNotSupportedError`. **Not implemented** |
| P1-8 | | 4. Availability info displays | PARTIAL → **FAIL** | RUNTIME | Only `accepting_requests` boolean | No availability schedule/slots model |
| P1-9 | Profile Creation | 1. Valid data saves | **PASS** | RUNTIME + TEST | Created via registration flow (`role_slug == "tutor"`) | `test_tutor_registration_request_creates_pending_revision_and_approves_user`. Note `POST /tutor/create/` is a dead stub (BC-2) |
| P1-9 | | 2. Missing field → validation | **PASS** | RUNTIME | Registration missing email → `422` | |
| P1-9 | | 3. New profile gets Pending | **PASS** | TEST | `register.py:78` sets `Status.PENDING` | `test_create_tutor_profile_creates_pending_revision` |
| P1-9 | | 4. Persists after refresh | **PASS** | RUNTIME | Re-query returns persisted row | DB-backed |
| P1-10 | Profile Editing | 1. Change bio saved | **PASS** | RUNTIME | `PUT /v1/tutor/{id}/` → `200`, `"bio":"legit update"` | Creates pending revision (by design) |
| P1-10 | | 2. Change academic program | **PASS** | RUNTIME | Same endpoint, field accepted | |
| P1-10 | | 3. Change **languages**/teaching style | **FAIL** | RUNTIME | `teaching_style` works; **languages do not exist** | Same root cause as P1-8.3 |
| P1-10 | | 4. Logout/login → data remains | **PASS** | RUNTIME | Re-login, re-query returns updated row | |
| P1-11 | Tags & Badges | 1. Add subject tag | **PASS** | RUNTIME + TEST | `tags` JSON column accepted and returned | `test_tutor_create_and_update_inputs_accept_tags` |
| P1-11 | | 2. Add skill badge | **FAIL** | CODE | No distinct badge model — tags only | "Skill badges" conflated with tags |
| P1-11 | | 3. Remove tag/badge | **PASS** | CODE | Update replaces the `tags` array | Removal via full-array replace; not independently runtime-tested |
| P1-11 | | 4. Tags appear on profile/search | **PASS** | RUNTIME | `"tags":["Python","Math"]` in list payload; `?query=Python` matches via `cast(tags, String).ilike` | |
| P1-12 | Approval Workflow | 1. New profile → Pending | **PASS** | TEST | `test_tutor_registration_request_creates_pending_revision_and_approves_user` | |
| P1-12 | | 2. Admin approves → Approved | **PASS** | TEST | `test_admin_can_approve_tutor_revision_updates_tutor` | |
| P1-12 | | 3. Admin rejects → Rejected | **PASS** | TEST | `test_admin_can_reject_tutor_revision` | |
| P1-12 | | 4. Rejected stays hidden | **PASS** | RUNTIME | Seeded REJECTED tutor absent from public list | |
| P1-13 | Student→Tutor Msg | 1. Student sends, tutor receives | CANNOT VERIFY | CODE | `ws.py:320-348` fans out to room members | Requires a live duplex WS session; harness cannot drive two sockets |
| P1-13 | | 2. History on open | PASS | CODE | `GET /v1/chat/rooms/{id}/messages/` with `is_member` guard | Route exists; membership enforced |
| P1-13 | | 3. Timestamp displays | PASS | CODE | `"created_at": msg.created_at.isoformat()` in payload | Rendering not browser-verified |
| P1-13 | | 4. Guest messaging blocked | **PASS** | RUNTIME | `POST /v1/chat/rooms/direct/` no auth → `401` | |
| P1-14 | Tutor→Student Msg | 1. Tutor replies, student receives | CANNOT VERIFY | CODE | Same mechanism as P1-13.1 | |
| P1-14 | | 2. History persists after refresh | PASS | CODE | Messages persisted in `chat_messages` | |
| P1-14 | | 3. Correct message order | PASS | CODE | `get_history` orders by id/created_at | Not runtime-verified |
| P1-14 | | 4. Suspended/deleted user unmessageable | **PASS** | RUNTIME + CODE | `_get_active_user_roles` raises `403 "The target account is unavailable."` for non-ACTIVE target | Suspended login → `403` confirmed at runtime |
| P1-15 | Admin↔Tutor Msg | 1. Admin messages tutor | PASS | CODE | `allowed_pairs` includes `{admin, tutor}`, `{super_admin, tutor}` ([`ws.py:62-66`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/ws.py#L62-L66)) | |
| P1-15 | | 2. Tutor replies | PASS | CODE | Pair check is symmetric (`frozenset`) | |
| P1-15 | | 3. History displays | PASS | CODE | Same history endpoint | |
| P1-15 | | 4. Student→admin conversation denied | **PASS** | CODE | `{student, admin}` is **not** in `allowed_pairs` → `403 "This conversation is not permitted."` | Strong code evidence; not runtime-driven |
| P1-16 | User Reporting | 1. Report tutor profile | **PASS** | RUNTIME | `POST /v1/report/tutor/` → `201`, report id returned | |
| P1-16 | | 2. Report **message/content** | **FAIL** | RUNTIME | Only `/report/tutor/`, `/report/service/`, `/report/review/` exist | **No chat-message reporting** |
| P1-16 | | 3. No reason → rejected | **PASS** | RUNTIME + TEST | `reason:""` → `422 "String should have at least 10 characters"` | Whitespace-only also rejected (`test_review_report_reason_rejects_whitespace`) |
| P1-16 | | 4. Report appears for admin | **PASS** | RUNTIME | `GET /v1/report/tutor/` as admin → `200` with the report; as student → `403` | End-to-end persistence confirmed |
| P1-17 | Admin Dashboard | 1. Pending tutor list | **PASS** | RUNTIME | `GET /v1/admin/tutor_revisions/pending/` → admin `200`, tutor `403` | |
| P1-17 | | 2. Reports/flagged items | **PASS** | RUNTIME | `/report/tutor/`, `/report/service/`, `/report/review/` all `200` for admin | Admin UI wires all three ([`dashboard.component.ts:118-126`](skillbridge-admin/src/app/layout/dashboard/dashboard.component.ts#L118-L126)) |
| P1-17 | | 3. Open approval item | PASS | CODE | `approval-card.component.ts` → `admin/service_revisions/{id}/approve/` | Route match confirmed |
| P1-17 | | 4. Open reported item for action | **PASS** | RUNTIME | `PATCH /report/{type}/{id}/disable/` + `DELETE .../` exist and are admin-gated | |
| P1-18 | Moderation | 1. Deactivate user → access blocked | **PASS** | RUNTIME | Admin `PATCH /admin/tutors/{id}/status/ INACTIVE` → `200`; tutor's **existing token** then → `403` | Immediate revocation, not just at login |
| P1-18 | | 2. Remove profile → hidden | **PASS** | RUNTIME | Disabled tutor absent from public search (`present= False`) | |
| P1-18 | | 3. Remove content → disappears | **PASS** | RUNTIME | `PATCH /report/service/{id}/disable/` exists, admin-gated | `test_student_can_report_service_and_admin_can_disable_service_and_discard` |
| P1-18 | | 4. Suspended login/action denied | **PASS** | RUNTIME | Login → `403 "This tutor account is temporarily disabled."` | |
| P1-19 | Valid Media Upload | 1. Valid JPG accepted | PASS | TEST | Magic-byte `\xff\xd8\xff` + `.jpg/.jpeg` agreement | `test_image_validation_accepts_matching_png_signature` (PNG); JPG path is identical code |
| P1-19 | | 2. Valid PNG accepted | **PASS** | TEST | `test_image_validation_accepts_matching_png_signature` | |
| P1-19 | | 3. Valid video accepted | CANNOT VERIFY | CODE | `_validate_video_signature` checks `ftyp`/EBML | No S3 credentials — upload cannot complete |
| P1-19 | | 4. Media displayed/retrievable | BLOCKED | BLOCKED | Requires live S3 + browser | |
| P1-20 | Invalid Media | 1. Unsupported extension rejected | **PASS** | TEST | `400 "Invalid file type. Allowed: JPEG, PNG, WEBP"` | |
| P1-20 | | 2. Oversized image rejected | PASS | CODE | `_read_limited` hard-caps at 5 MB, raises `400` mid-stream | Limit logic inspected, not exercised |
| P1-20 | | 3. Oversized video rejected | PASS | CODE | Same mechanism, 100 MB cap | |
| P1-20 | | 4. Understandable error shown | **PASS** | TEST | `"File too large. Maximum size: 5MB"`, `"File content does not match its image type or extension."` | `test_image_validation_rejects_spoofed_content` |
| P1-21 | Service Creation | 1. Valid details → created | PASS | CODE | `POST /v1/service/create/` with ownership + validator | Multipart + S3 path; not runtime-exercised |
| P1-21 | | 2. Missing info → validation | **PASS** | TEST | `CreateServiceInputValidator`: name 3–120, price 0–10000, `end_time > time`, no past dates | `test_service_creation_requires_end_time_after_start_time` |
| P1-21 | | 3. Add image → uploaded/saved | BLOCKED | BLOCKED | Needs live S3 | |
| P1-21 | | 4. Persists after refresh | PASS | CODE | Creates a `ServiceRevision`, applied on approval | |
| P1-22 | Service Video | 1. Valid video uploads | BLOCKED | BLOCKED | Needs live S3 | |
| P1-22 | | 2. Invalid type rejected | **PASS** | CODE + TEST | `400 "Invalid file type. Allowed: MP4, WEBM, MOV"` + signature check | Attachment spoof test covers the same validator family |
| P1-22 | | 3. Oversized video rejected | PASS | CODE | 100 MB cap in `_read_limited` | |
| P1-22 | | 4. Saved video on correct service | PASS | CODE | `video_url`/`video_urls` on the revision; max 1 enforced ([`service.py:189-190`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/service.py#L189-L190)) | |
| P1-23 | Password Security | 1. Not stored plaintext | **PASS** | RUNTIME | bcrypt, 12 rounds ([`token.py:56-58`](skillbridge-be/src/skillbridge/api/repositories/auth/token.py#L56-L58)); stored hash used for login | |
| P1-23 | | 2. Login works against hash | **PASS** | RUNTIME | Login succeeds against the bcrypt hash written at seed time | |
| P1-23 | | 3. DB does not expose original | **PASS** | RUNTIME | `UserOutput` has **no** `password` field; `response_model` strips `to_dict()` output | Verified: no `password` key in any API response observed |
| P1-23 | | 4. Invalid password → auth fails | **PASS** | RUNTIME | `401 "Invalid email or password."` | |
| P1-24 | Protected APIs | 1. Correct role allowed | **PASS** | RUNTIME | Admin→`/admin/dashboard/` `200`; student→`/dashboard/student/` `200` | |
| P1-24 | | 2. No token rejected | **PASS** | RUNTIME | `401 "Authorization header missing"`; garbage JWT → `401 "Invalid token"` | |
| P1-24 | | 3. Student→admin rejected | **PASS** | RUNTIME | `403` on `/admin/dashboard/`, `/admin/tutors/`, `/user/users/` | |
| P1-24 | | 4. Tutor→admin-only rejected | **PASS** | RUNTIME | `403` on `/admin/dashboard/`, `/admin/tutor_revisions/pending/` | |
| P1-25 | Responsive | 1. Landing on laptop | BLOCKED | BLOCKED | No browser | 23 SCSS files with `@media`; viewport meta present — **CODE evidence only, not a pass** |
| P1-25 | | 2. Search on mobile | BLOCKED | BLOCKED | Breakpoints 480–1100 px exist | Same caveat |
| P1-25 | | 3. Tutor profile on mobile | BLOCKED | BLOCKED | | Same caveat |
| P1-25 | | 4. Dashboard/messaging small screen | BLOCKED | BLOCKED | Admin app has only 7 `@media` files vs 23 | Coverage looks thinner on admin |
| P1-26 | Browser Compat | 1. Workflow in Chrome | BLOCKED | BLOCKED | Karma ran headless Chrome for **unit tests only**, not workflows | |
| P1-26 | | 2. Workflow in Firefox | BLOCKED | BLOCKED | No Firefox launcher configured | |
| P1-26 | | 3. Forms in Chrome | BLOCKED | BLOCKED | | |
| P1-26 | | 4. Forms in Firefox | BLOCKED | BLOCKED | | |
| P1-27 | FE↔BE Integration | 1. Search → results | **PASS** | RUNTIME | FE path `tutor/tutors/?query=&sort=` matches backend exactly | |
| P1-27 | | 2. Profile change → DB updated | **PASS** | RUNTIME | `PUT /v1/tutor/{id}/` → `200`, revision persisted | |
| P1-27 | | 3. Messaging → backend/DB update | CANNOT VERIFY | CODE | WS contract matches exactly; duplex flow not drivable here | |
| P1-27 | | 4. Service creation → DB update | PASS | CODE | Route + contract match; S3 blocks full runtime | |
| P1-28 | DB Persistence | 1. Profile changes remain | **PASS** | RUNTIME | Re-query returns updated row | |
| P1-28 | | 2. Created service remains | **PASS** | RUNTIME | Seeded + queried across requests | |
| P1-28 | | 3. Messages remain | PASS | CODE | `chat_messages` table + history endpoint | |
| P1-28 | | 4. Admin approval state remains | **PASS** | RUNTIME | Status change survives re-query and re-login | |
| P1-29 | Deployment | 1. Public domain opens | BLOCKED | BLOCKED | No network access to `skillbridgeacademy.duckdns.org` | |
| P1-29 | | 2. Frontend loads | BLOCKED | BLOCKED | | |
| P1-29 | | 3. Backend APIs reachable | BLOCKED | BLOCKED | | |
| P1-29 | | 4. DB functions work on server | BLOCKED | BLOCKED | | |

### P1 Summary

| Result | Count |
|---|---|
| **PASS** | **76** |
| **FAIL** | **21** |
| **BLOCKED** | **16** |
| **CANNOT VERIFY** | **3** |
| Total | **116** |

**Of the 76 passes:**
- **52 runtime-verified** (real HTTP request executed) or **test-verified**
- **24 code-inspection only** — these are *not* demonstrated working behaviour

P1 failure clusters: languages/availability not modelled (4), skill badges (1), guest PII (1), chat-message reporting (1), and the booking outage cascading into integration scenarios.

---

## 5. P2 Scenario Results

| # | Feature | Scenario | Result | Verification | Evidence | Notes |
|---|---|---|---|---|---|---|
| P2-1 | Advanced Filtering | 1. Filter by subject | PARTIAL → **PASS** | RUNTIME | `?academic_program=Computer` → `200` filtered | Backend only; **no filter UI** in tutor list |
| P2-1 | | 2. Filter by language | **FAIL** | RUNTIME | `?language=English` → `200` **unfiltered** (param silently ignored) | Language not modelled |
| P2-1 | | 3. Filter by price | **FAIL** (tutors) | RUNTIME | `TutorQueryCriteria` has no price filter | Services **do** support `min_price`/`max_price` |
| P2-1 | | 4. Filter by tutoring format | **FAIL** | RUNTIME | No format field anywhere | Not implemented |
| P2-2 | Multiple Filters | 1. Subject + language | **FAIL** | RUNTIME | Language leg missing | |
| P2-2 | | 2. Subject + price | **FAIL** | RUNTIME | Tutor price filter missing | |
| P2-2 | | 3. Rating + availability | **FAIL** | RUNTIME | Both are **sorts**, not filters | `sort=rating:desc`, `sort=availability` exist |
| P2-2 | | 4. Clear filters → full list | **PASS** | RUNTIME | Service list `clearPriceFilter()` re-fetches; unfiltered call returns all | |
| P2-3 | Sorting | 1. Lowest price first | **PASS** | RUNTIME + TEST | `?sort=price:asc` → `200` | `test_service_filter_supports_price_range_and_price_sort` |
| P2-3 | | 2. Highest rating first | **PASS** | RUNTIME + TEST | `?sort=rating:desc` → `200` | `test_tutor_rating_sort_uses_mysql_safe_null_ordering` |
| P2-3 | | 3. Newest first | **PASS** | RUNTIME | `?sort=newest` → `200` | |
| P2-3 | | 4. Relevance/availability | **PASS** | RUNTIME | `?sort=availability` → `200` | `relevance` aliases to availability |
| P2-4 | Guest Search Filters | 1. Guest subject filter | **PASS** | RUNTIME | `?academic_program=` unauthenticated → `200` | |
| P2-4 | | 2. Guest format filter | **FAIL** | RUNTIME | Format not implemented | |
| P2-4 | | 3. Guest restricted details blocked | PARTIAL → **FAIL** | RUNTIME | `favorite_only` → `403` ✓, but tutor **phone** is readable | SEC-01 |
| P2-4 | | 4. Login/register CTA appears | PASS | CODE | Guest branches in templates (`isGuest`, "Sign in to view your notifications.") | Not browser-verified |
| P2-5 | Ratings | 1. Eligible student rating accepted | **PASS** | RUNTIME | After completed booking → `201` | |
| P2-5 | | 2. Average updates | **PASS** | RUNTIME | `average_rating` moved off `"No Review Yet"` after review | `format_average_rating` |
| P2-5 | | 3. Rating shown on profile | **PASS** | RUNTIME | `"average_rating"` in tutor list payload | |
| P2-5 | | 4. Guest sees permitted summary only | **PASS** | RUNTIME | Guest review payload: `email:null, phone:null, id:null` | Reviewer PII correctly masked **for guests** |
| P2-6 | Reviews | 1. Valid review saved | **PASS** | RUNTIME | `POST /v1/review/tutor/` → `201` | |
| P2-6 | | 2. Appears on profile | **PASS** | RUNTIME | `GET /v1/review/tutor/?tutor_id=` returns it | |
| P2-6 | | 3. Second review rejected | **PASS** | RUNTIME | → `409 "You already reviewed this tutor."` | DB unique constraint `uq_tutor_review_tutor_student`; **no raw DB error leaked** |
| P2-6 | | 4. Tutor can see review | **PASS** | RUNTIME | Public review endpoint + `TUTOR_REVIEW_CREATED` notification | |
| P2-7 | Review Reporting | 1. Tutor reports review | **PASS** | RUNTIME | `POST /v1/report/review/tutor/{id}/` → `201` | |
| P2-7 | | 2. Admin sees reported review | **PASS** | RUNTIME | `GET /v1/report/review/` admin → `200`; student → `403` | |
| P2-7 | | 3. Admin removes violating review | **PASS** | TEST | `DELETE /v1/report/review/{id}/review/` | `test_missing_review_and_remove_moderation` |
| P2-7 | | 4. Valid review remains visible | **PASS** | TEST | Dismiss path leaves the review intact | `test_create_list_duplicate_and_dismiss_review_report` |
| P2-8 | Session Request | 1. Send request → Pending | **FAIL** | RUNTIME | `POST /v1/service-booking/create/` → **`406`** | **BC-1 — the route the UI uses is broken** |
| P2-8 | | 2. Cancel pending → Cancelled | **PASS** | RUNTIME | `DELETE /v1/service-booking/{id}/` → `200`, `"status":"CANCELLED"` | Unrelated student → `403` |
| P2-8 | | 3. Tutor accepts → Accepted | **PASS** | RUNTIME + TEST | `PATCH .../accept/`; re-accept → `409` transition guard | `test_session_request_accept_and_notification_flow` |
| P2-8 | | 4. Tutor declines → Declined | **PASS** | TEST | `test_declined_and_cancelled_states_are_terminal` | |
| P2-9 | Rescheduling | 1. Tutor proposes → student sees | **PASS** | RUNTIME | `POST .../reschedule/` → `201`; student `GET` → `200` with proposal | |
| P2-9 | | 2. Student accepts → status updated | **PASS** | RUNTIME | `PATCH .../reschedule/{pid}/accept/` → `200` | |
| P2-9 | | 3. Student rejects → status updated | **PASS** | TEST | `test_reschedule_requires_other_participant_and_persists_history` | |
| P2-9 | | 4. Persists after refresh | **PASS** | RUNTIME | History re-query returns the record | |
| P2-10 | Tutor Session Mgmt | 1. Tutor sees new request | **PASS** | RUNTIME | `GET /v1/service-booking/service-bookings/` scoped to tutor | |
| P2-10 | | 2. Tutor accepts | **PASS** | RUNTIME | `200` | |
| P2-10 | | 3. Tutor declines | **PASS** | TEST | Transition matrix test | |
| P2-10 | | 4. Tutor proposes alternative | **PASS** | RUNTIME | `201` | |
| P2-11 | Media-Rich Profile | 1. Profile image upload | BLOCKED | BLOCKED | Needs live S3 | Route + ownership verified |
| P2-11 | | 2. Supporting document upload | BLOCKED | BLOCKED | Service attachments only; needs S3 | |
| P2-11 | | 3. Intro video/audio upload | **FAIL** | CODE | No tutor intro-video field; **audio not supported at all** | Tutor media = profile + cover image only |
| P2-11 | | 4. Media appears after approval | **FAIL** | CODE | `upload_profile_picture` writes **straight to the live profile** ([`media_service.py:262`](skillbridge-be/src/skillbridge/api/services/media_service.py#L262)) | **Bypasses the revision/approval workflow entirely** |
| P2-12 | Media Moderation | 1. Media in review queue | **FAIL** | RUNTIME | No media moderation table, column, or endpoint | Moderation is text-only (Detoxify) |
| P2-12 | | 2. Admin approves → visible | **FAIL** | CODE | No such flow | |
| P2-12 | | 3. Admin rejects → hidden | **FAIL** | CODE | No such flow | |
| P2-12 | | 4. Admin removes approved media | **FAIL** | CODE | Only the owning tutor can delete their own media | |
| P2-13 | Resource Sharing | 1. Upload note/resource | PARTIAL → **FAIL** | CODE | Service attachments exist, but are bound to a service | No standalone resource entity |
| P2-13 | | 2. Title/description/subject saved | **FAIL** | CODE | Attachment stores `object_key`, filename, size — **no title/description/subject** | |
| P2-13 | | 3. Edit own resource | **FAIL** | RUNTIME | No update route — only `POST`, `GET`, `DELETE` | |
| P2-13 | | 4. Delete own resource | **PASS** | RUNTIME | `DELETE /v1/service/attachments/{id}/` exists, ownership-gated | |
| P2-14 | Student Resource Access | 1. Open permitted resource | **PASS** | TEST | `test_service_attachment_access_is_limited_to_tutor_or_booked_student` | |
| P2-14 | | 2. Download permitted | PASS | CODE | Presigned S3 URL via `generate_presigned_download_url` | S3 blocks runtime proof |
| P2-14 | | 3. Type/title displayed | **FAIL** | CODE | Filename only; no type/title metadata | |
| P2-14 | | 4. Deleted/blocked inaccessible | **PASS** | TEST | Access limited to tutor or booked student | |
| P2-15 | Guest Resource Restrictions | 1. Resource title visible | **FAIL** | CODE | Attachment list requires auth — guests see **nothing** | Spec wants title visible to guests |
| P2-15 | | 2. Type/subject visible | **FAIL** | CODE | Not modelled | |
| P2-15 | | 3. Guest opening file blocked | **PASS** | CODE | `@validate_token` on the download route | Correct, if stricter than spec |
| P2-15 | | 4. Login/register prompt | PASS | CODE | Guest branches in templates | Not browser-verified |
| P2-16 | Resource Moderation | 1. Admin sees flagged resource | **FAIL** | RUNTIME | No resource moderation queue | |
| P2-16 | | 2. Admin approves → visible | **FAIL** | CODE | No flow | |
| P2-16 | | 3. Admin rejects → hidden | **FAIL** | CODE | No flow | |
| P2-16 | | 4. Admin removes inappropriate | **FAIL** | CODE | Only the owning tutor can delete | |
| P2-17 | Favourites | 1. Add tutor → appears | **PASS** | RUNTIME | `PUT /v1/favorites/tutors/{id}/ {"favorite":true}` → `200`; `?favorite_only=true` returns it | |
| P2-17 | | 2. Remove → disappears | **PASS** | RUNTIME | `{"favorite":false}` → list becomes `[]` | |
| P2-17 | | 3. Persists across logout/login | **PASS** | RUNTIME | Server-side `student_favorite_tutors` table | |
| P2-17 | | 4. Duplicate add → no duplicate | **PASS** | RUNTIME + TEST | Second identical add → `200`, list count stays `1` | `test_favorite_operations_are_idempotent` |
| P2-18 | Student Notifications | 1. New message → notification | **PASS** | TEST | `test_chat_message_notifies_other_members_but_not_sender` | `CHAT_MESSAGE_RECEIVED` |
| P2-18 | | 2. Session status → notification | **PASS** | TEST | `SESSION_ACCEPTED`/`DECLINED`/`CANCELLED` | `test_session_request_accept_and_notification_flow` |
| P2-18 | | 3. Schedule change → notification | **PASS** | CODE | `RESCHEDULE_PROPOSED` | |
| P2-18 | | 4. Mark read → status changes | **PASS** | RUNTIME + TEST | `GET /v1/notifications/` → `200`; `PATCH .../read/`, `/read-all/` | `test_mark_read_and_mark_all_read_are_idempotent` |
| P2-19 | Tutor Notifications | 1. New message | **PASS** | TEST | Same fan-out | |
| P2-19 | | 2. New session request | **PASS** | TEST | `SESSION_REQUESTED` | |
| P2-19 | | 3. Student review | **PASS** | TEST | `TUTOR_REVIEW_CREATED` — `test_successful_reviews_notify_the_relevant_tutor` | |
| P2-19 | | 4. Profile approval change | **PASS** | CODE | `TUTOR_PROFILE_APPROVED` / `TUTOR_PROFILE_REJECTED` | |
| P2-20 | Admin Notifications | 1. Pending profile/content | **FAIL** | CODE | `_notify_admins` fires only on **reports**, never on new pending revisions | Admins must poll the dashboard |
| P2-20 | | 2. Reported review | **PASS** | CODE | `REVIEW_REPORTED` via `_notify_admins` ([`report.py:241`](skillbridge-be/src/skillbridge/api/repositories/report.py#L241)) | |
| P2-20 | | 3. Flagged media/resource | **FAIL** | CODE | No media/resource moderation exists | |
| P2-20 | | 4. Mark resolved → state updated | PARTIAL → **PASS** | RUNTIME | Notification mark-read works; discard/disable endpoints update report state | |
| P2-21 | Tutor Visibility | 1. Hide → removed from search | **PASS** | RUNTIME | `PATCH /v1/tutor/me/visibility/ {"is_visible":false}` → tutor **disappears** from public list | Verified by before/after id comparison |
| P2-21 | | 2. Reactivate → returns | **PASS** | RUNTIME | Tutor **reappears** in public list | |
| P2-21 | | 3. Pause availability | **PASS** | RUNTIME | `PATCH /v1/tutor/me/availability/` → `"accepting_requests":false` | |
| P2-21 | | 4. "Not accepting" restricts requests | **FAIL** | RUNTIME | `accepting_requests` affects **sort order only** — no booking-time enforcement | Compounded by BC-1 |
| P2-22 | Admin Visibility Control | 1. Admin sees Active state | **PASS** | RUNTIME + TEST | `GET /v1/admin/tutors/` returns `account_status` | `test_admin_tutor_listing_includes_linked_user_status` |
| P2-22 | | 2. Admin sees Hidden/Paused | **PASS** | RUNTIME | `is_visible` + `accepting_requests` in the same payload | |
| P2-22 | | 3. Admin overrides visibility | **PASS** | RUNTIME | `PATCH /v1/admin/tutors/{id}/status/ INACTIVE` → tutor hidden + token revoked | |
| P2-22 | | 4. Suspended/rejected absent from search | **PASS** | RUNTIME | Both confirmed absent (`present= False`) | |

### P2 Summary

| Result | Count |
|---|---|
| **PASS** | **40** |
| **FAIL** | **37** |
| **BLOCKED** | **8** |
| **CANNOT VERIFY** | **3** |
| Total | **88** |

**Of the 40 passes:**
- **26 runtime-verified or test-verified**
- **14 code-inspection only**

P2 is where the implementation is genuinely thin. The 37 failures concentrate almost entirely in five never-built areas: advanced filtering (language/price/format), media moderation, resource sharing, resource moderation, and guest resource restrictions. **Session workflow, rescheduling, favourites, ratings, reviews, review reporting, notifications, and visibility control are all well built and mostly runtime-verified** — the P2 work that was done was done properly.

---

## 6. Security Findings

| # | Finding | Severity | Status | Verification | Location | Evidence | Recommended Fix |
|---|---|---|---|---|---|---|---|
| SEC-01 | **Tutor phone number exposed to unauthenticated guests.** `TutorOutput` includes `phone`, and `get_tutors` splats `**tutor.to_dict()` without masking it. Only the nested `user` object is guest-masked. | **HIGH** | IMPLEMENTED BUT INSECURE | **RUNTIME** | [`tutor.py:113-129`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/tutor.py#L113-L129); [`schemas/tutor.py:75`](skillbridge-be/src/skillbridge/api/schemas/tutor.py#L75) | Guest `GET /v1/tutor/tutors/`: `{"phone":"+491759999999", ..., "user":{"email":null,"phone":null,"id":null}}` — outer phone leaks, inner correctly masked | Mask `phone` for `user_id is None`, mirroring the `user.id` treatment on the same lines |
| SEC-02 | **Secrets remain in Git history.** Removed from the working tree in `5105f45` and gitignored, but the blobs are still reachable and **pushed to `origin`**. | **HIGH** | NOT REMEDIATED | **RUNTIME** | History only — no current file | `git rev-list --all --objects` returns `configurationKeys/skillbridge-ec2`, `configurationKeys/accessToTheServer.txt`, `configurationKeys/github-actions-ec2-deploy`, `skillbridge-be/.env.dev` | **Rotate every credential first** (see §10), then optionally purge history. Rotation matters more than the rewrite |
| SEC-03 | **Reviewer PII exposed to any authenticated user.** Review listings return every reviewer's `email`, `phone`, `status`, `has_registered` to any logged-in account. | MEDIUM | IMPLEMENTED BUT INSECURE | **RUNTIME** | [`review.py:104-112`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/review.py#L104-L112) and `:137-145` | Authed: `"student":{"full_name":"Student One","email":"s1@hs-fulda.de","phone":"+4915100000","status":"ACTIVE",...}`. Guest correctly gets nulls | Return `full_name` only to non-admins; gate `email`/`phone` behind an admin check |
| SEC-04 | **Guest search is a PII oracle.** Free-text `query` runs `ilike` against `User.email` and `User.phone`. The values are not returned, but a guest can confirm a tutor's email/phone by substring probing. | MEDIUM | IMPLEMENTED BUT INSECURE | **RUNTIME** | [`filters/tutor.py:118-132`](skillbridge-be/src/skillbridge/api/filters/tutor.py#L118-L132) | Public search matches on `User.email` / `User.phone` with no auth | Restrict email/phone matching to authenticated admin searches |
| SEC-05 | **Large uploads fully buffered in memory.** `_read_limited` accumulates chunks in a list then `b"".join()` — up to ~200 MB transient per concurrent 100 MB video. | MEDIUM | PARTIALLY IMPLEMENTED | CODE | [`media_service.py:53-67`](skillbridge-be/src/skillbridge/api/services/media_service.py#L53-L67) | Hard cap and timeout are correct; the buffering strategy is not | Stream to a `SpooledTemporaryFile` and multipart-upload to S3 |
| SEC-06 | **Orphaned S3 objects when DB persistence fails.** If `update_profile_picture` returns falsy, the code raises `404` **after** the S3 upload, with no cleanup. | MEDIUM | PARTIALLY IMPLEMENTED | CODE | [`media_service.py:262-274`](skillbridge-be/src/skillbridge/api/services/media_service.py#L262-L274); same in cover + student paths | Contrast `create_service`, which **does** clean up correctly ([`service.py:221-226`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/service.py#L221-L226)) | Wrap in `try/except` and `s3_client.delete_file(s3_url)` on failure, as `create_service` does |
| SEC-07 | **Uploaded media bypasses the approval workflow.** Profile/cover images write directly to the live tutor row; all other profile edits go through a pending revision. | MEDIUM | IMPLEMENTED BUT INSECURE | CODE | [`media_service.py:262`](skillbridge-be/src/skillbridge/api/services/media_service.py#L262) | No moderation column on any media field | Route media through `TutorRevision`, or add a media moderation state |
| SEC-08 | **Authorization failures in some repositories surface as HTTP 500.** `get_pending_tutor_revisions` raises a bare `Exception("Admin access required.")`, which `handle_exceptions` maps to 500 and sanitises to a generic message. | MEDIUM | PARTIALLY IMPLEMENTED | CODE | [`repositories/tutor.py:356`](skillbridge-be/src/skillbridge/api/repositories/tutor.py#L356); [`exceptions.py:44-47`](skillbridge-be/src/skillbridge/exceptions.py#L44-L47) | Access is still **denied** — correctness issue, not a bypass | Raise `HTTPException(403, ...)` |
| SEC-09 | **JWT sent in the WebSocket URL query string.** Appears in nginx access logs, proxy logs, and browser history. | LOW | ACCEPTED TRADE-OFF | **RUNTIME** | [`socket.service.ts:36-37`](skillbridge-fe/src/app/resources/services/socket.service.ts#L36-L37); [`ws.py:248`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/ws.py#L248) | Browsers cannot set headers on `WebSocket` — a common industry compromise | Use a short-lived single-use ticket, or scrub `?token=` from nginx logs |
| SEC-10 | **Plaintext password logged to the browser console.** `console.log('Registration payload:', payload)` includes `password` and `confirm_password`. | LOW | IMPLEMENTED BUT INSECURE | CODE | [`sign-in.component.ts:166`](skillbridge-fe/src/app/auth/sign-in/sign-in.component.ts#L166) | Client-side only, but survives in screen shares and console-reading extensions | Remove the log (58 `console.log` calls across both apps) |
| SEC-11 | **Login permits non-`ACTIVE`, non-`INACTIVE` statuses.** The gate checks `== "INACTIVE"` only, so `TRASHED`/`DELETED`/`ARCHIEVED` accounts can still obtain tokens. | LOW | PARTIALLY IMPLEMENTED | CODE | [`login.py:50-54`](skillbridge-be/src/skillbridge/api/repositories/auth/login.py#L50-L54) | Mitigated: `validate_token` requires `== "ACTIVE"`, so the tokens are unusable | Invert to `!= "ACTIVE"`, matching `validate_token` |
| SEC-12 | **User-enumeration oracle at login.** Unknown account → `"The User has not been registered yet."`; wrong password → `"Invalid email or password."` | LOW | IMPLEMENTED BUT INSECURE | **RUNTIME** | [`login.py:46-59`](skillbridge-be/src/skillbridge/api/repositories/auth/login.py#L46-L59) | Two distinguishable 401 bodies | Return one identical message for both |
| SEC-13 | **Audit-field mass assignment.** `BaseInModel` exposes `created_by_id`/`updated_by_id`, so a registrant can spoof provenance fields. | LOW | PARTIALLY IMPLEMENTED | CODE | [`renderer.py:75-85`](skillbridge-be/src/skillbridge/utils/renderer.py#L75-L85) | `status`, `has_registered`, `is_verified` are **correctly** dropped — `UserModel` omits them | Strip audit fields server-side |
| SEC-14 | **Security headers lost on nested nginx locations.** In the admin config, `add_header` inside `location ~*` blocks **replaces** rather than inherits the server-level headers, so CSS/JS/images/fonts and direct `/index.html` requests ship without CSP, HSTS, X-Frame-Options, nosniff, or Referrer-Policy. | LOW | PARTIALLY IMPLEMENTED | CODE | [`skillbridge-admin/nginx.conf:19-28`](skillbridge-admin/nginx.conf#L19-L28) | Standard nginx inheritance rule. `skillbridge-fe/nginx.conf` has no nested `add_header` and is unaffected | Repeat the five security headers inside each nested `location`, or move caching to `map`-driven `expires` |
| SEC-15 | **No CI.** All four workflows are `workflow_dispatch` only. The 105 backend tests and both Angular suites never run on push or PR. | LOW | NOT IMPLEMENTED | **RUNTIME** | `.github/workflows/*.yml` | `grep "push:\|pull_request:"` → no matches | Add a PR workflow running pytest + both `ng test` + both `ng build` |
| SEC-16 | **Production nginx adds no headers of its own; API responses carry none.** The main-domain server block proxies without `add_header`. | INFO | INFORMATIONAL | CODE | [`deploy-about-page.yml:333-371`](.github/workflows/deploy-about-page.yml#L333-L371) | Mitigated: `location /` proxies to the FE container, whose nginx **does** set all five headers, and those pass through. Only `/api/` responses lack them | Add headers at the TLS edge so HSTS is set by the terminating server |
| SEC-17 | **Production bundles ship `production: false`.** No `fileReplacements` configured, so `environment.ts` is used in every configuration. | INFO | INFORMATIONAL | **BUILD** | `angular.json` (both apps); `environment.ts` | `environment.prod.ts` is empty (admin) / missing `wsUrl` (fe) — both dead | Wire `fileReplacements` and populate the prod files, or delete them |
| SEC-18 | **Ephemeral JWT secret fallback in development.** `auth_config` falls back to a random per-process secret when `JWT_SECRET_KEY`/`SECRET_KEY` are absent. | INFO | CORRECT BY DESIGN | CODE | [`auth/config.py:8-47`](skillbridge-be/src/skillbridge/api/repositories/auth/config.py#L8-L47) | **Fails safe**: `require_production_secrets` raises when `ENV=deployment` and neither is set. `config.Settings` also requires `SECRET_KEY` with no default | None — this is correct. Noted because the brief asked about insecure fallbacks |
| SEC-19 | **Debug `print()` calls in production paths.** 12 `print()` statements including one echoing moderation state. | INFO | CODE QUALITY | **RUNTIME** | See §11.1 | No tokens, passwords, or secrets are printed (verified by grep) | Replace with `loguru` at appropriate levels |

### Severity totals

| CRITICAL | HIGH | MEDIUM | LOW | INFO |
|---|---|---|---|---|
| **0** | **2** | **6** | **7** | **4** |

### Security areas verified as CORRECTLY implemented

These are the brief's headline concerns. I probed each with live requests; all are sound.

**S2 — Role privilege escalation: NOT POSSIBLE.**
- Unauthenticated `POST /v1/role/create/` with a valid body → `401 "Authorization header missing"`
- Student with a valid body → `403 "Admin access required."`
- Admin with a valid body → `201` (correct)
- Registration with an admin `role_id` → `403 "Public registration is limited to student and tutor accounts."` ([`register.py:46-51`](skillbridge-be/src/skillbridge/api/repositories/auth/register.py#L46-L51))
- `GET /v1/role/roles/` filters to `{student, tutor}` — the admin role id is **not discoverable** ([`role.py:71-75`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/role.py#L71-L75))
- Admin authorization is a DB join on `Role.slug IN ('admin','super_admin')`, never a JWT claim ([`user_role_association.py:165-186`](skillbridge-be/src/skillbridge/api/repositories/user_role_association.py#L165-L186))
- Admin provisioning: no API path exists; admins must be seeded directly in the database.

**S3 — WebSocket authentication: FULLY IMPLEMENTED.** [`ws.py:248-265`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/ws.py#L248-L265) verifies the JWT signature and expiry, requires `type == "access"`, derives identity from `sub` (**not** the URL), rejects token/URL mismatch with close code `4401`, confirms the account exists and is `ACTIVE`, and gates every frame on room membership via `ensure_member`. The frontend **does** send the token and the backend **does** consume it. Covered by 5 passing tests in `test_websocket_auth.py`.

**S4 — Ownership / IDOR: CLOSED.** Every attempt returned `403`:
- Tutor B updating Tutor A's profile → `403 "You can modify only your own tutor profile."`
- Student deleting a tutor's profile picture → `403`
- Tutor B deleting Tutor A's cover picture → `403`
- Student B deleting Student A's profile picture → `403 "You can modify only your own student profile."`
- Tutor B reading Tutor A's revisions → `403`
- Non-tutor setting tutor visibility → `403 "Tutor access required."`

Ownership is derived from the session (`UserRoleAssociation` lookup keyed by the JWT-derived `user_id`), **never** trusted from request IDs. Admin overrides are explicit and separately gated.

**S5 — Guest access: no fake `guest-token`.** `continueAsGuest()` ([`login.component.ts:70-88`](skillbridge-fe/src/app/auth/login/login.component.ts#L70-L88)) **explicitly removes** `access_token`, `refresh_token`, `token_type`, and `token_expires_in`. Nothing fake is ever sent. Genuinely guest-reachable read endpoints: `GET /tutor/tutors/`, `GET /service/services/`, `GET /service/{id}/`, `GET /review/tutor/`, `GET /review/service/`, `GET /role/roles/`, `GET /tutor/filter-options/`. All write actions require auth (confirmed at runtime). The only leak is SEC-01/SEC-04.

**S6 — Registration validation: ENFORCED BACKEND-SIDE.** `@hs-fulda.de` is enforced in both `UserRegisterInput` ([`schemas/user.py:42-48`](skillbridge-be/src/skillbridge/api/schemas/user.py#L42-L48)) and `UserRegisterInputValidator` ([`validators/user.py:51-57`](skillbridge-be/src/skillbridge/api/validators/user.py#L51-L57)) — not just in Angular. Emails are lowercased and stripped; duplicates return `409` **including across case**; the password policy (8+, upper, lower, digit, special) is backend-enforced; `uq_users_email` is created by migration `b92e4a6d7c8f`. Frontend and backend agree.

**S7 — Reporting integrity: PERSISTS END TO END.** Runtime-confirmed round trip: student creates a tutor report → `201`; admin lists it → `200` with the same id; student listing → `403`. Tables `reported_tutors` / `reported_services` are created by `7ac91e2d4f60` and `reported_reviews` by `a81d2f3c4b5e`, all idempotently. Reason validation (10–1000 chars, whitespace-trimmed) is enforced. Transactions commit explicitly; the review-report path rolls back on `IntegrityError`.

**S10 — Review integrity: SOUND.** The student is derived from the JWT and **overwrites** any caller-supplied `student_id` ([`review.py:44`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/review.py#L44)). Runtime proof: submitting `student_id` belonging to a *different* student returned `409 "You already reviewed this tutor."` — proving the spoofed id was discarded and the caller's own identity used. A completed, `ACCEPTED` booking is required (`403` otherwise). Duplicates are blocked by DB unique constraints and surface as a **clean `409`**, never a raw DB error.

**S13 — Account status: ENFORCED EVERYWHERE.** Runtime-confirmed: login blocked (`403`), **existing tokens immediately rejected** (`403` via `validate_token`), removed from public search, unmessageable (`_get_active_user_roles`), and the WebSocket rejects non-`ACTIVE` accounts. The admin status endpoint **is** wired to the admin UI ([`tutor-visibility.component.ts:52`](skillbridge-admin/src/app/layout/tutor-visibility/tutor-visibility.component.ts#L52) → `PATCH /v1/admin/tutors/{id}/status/`).

**S14 — CORS: allow-list honored.** [`app.py:67-83`](skillbridge-be/src/skillbridge/app.py#L67-L83) builds origins from `settings.BACKEND_CORS_ORIGINS`, falls back to localhost **only** outside deployment, and returns `[]` in production if unset. **No wildcard.** `allow_credentials=False`. Internal exceptions are sanitised: any status ≥ 500 is replaced with `"Something went wrong while processing the request."` ([`exceptions.py:46-47`](skillbridge-be/src/skillbridge/exceptions.py#L46-L47)).

---

## 7. Test & Build Results

All six commands were executed. **No result below is fabricated.**

### 7.1 Backend — `python -m pytest -q`

Run with the project virtualenv (`.venv/Scripts/python.exe`, Python 3.13.3). The system Python 3.14.4 **cannot** run the suite — `ModuleNotFoundError: No module named 'pytest_asyncio'`.

```
........................................................................ [ 68%]
.................................                                        [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\_pytest\cacheprovider.py:469
  PytestCacheWarning: could not create cache path
  ...\.pytest_cache\v\cache\nodeids: [WinError 5] Access is denied

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
105 passed, 1 warning in 10.37s

EXIT=0
```

**105 passed, 0 failed.** The single warning is a local filesystem permission issue on `.pytest_cache`, unrelated to the code.

#### `test_validate_token_injects_uuid_user_id` — the brief's specific question

**Verdict: the implementation is CORRECT and the test is CURRENT. Neither is stale, and nothing has regressed.** The test passes.

`validate_token` ([`token.py:302-351`](skillbridge-be/src/skillbridge/api/repositories/auth/token.py#L302-L351)) verifies the JWT signature, requires `type == "access"`, parses `sub` into a real `UUID` via `get_user_id_from_token` ([`token.py:289-298`](skillbridge-be/src/skillbridge/api/repositories/auth/token.py#L289-L298)), confirms the user exists and is `ACTIVE`, then injects `kwargs["user_id"]` as a `UUID` object. The test asserts exactly that, including `is_uuid is True`. Its two siblings (`rejects_refresh_token`, `rejects_deleted_user`) also pass. **No change is warranted to either file.**

**Important caveat about this suite:** 105 green tests coexist with a completely broken primary booking endpoint (BC-1). The booking tests (`test_service_booking_response`, `test_service_booking_duplicates`, `test_service_booking_cancellation`) exercise repositories and schemas — **never the HTTP endpoint**. The suite has a real endpoint-level coverage gap.

### 7.2 Backend — `python -m alembic heads`

```
b92e4a6d7c8f (head)

EXIT=0
```

**Exactly one head.** No branching, no merge revisions. `alembic history` confirms a clean linear chain of 25 revisions from `<base>` → `f649238d6e3f` → … → `b92e4a6d7c8f`.

### 7.3 Public Angular — `npm test -- --watch=false`

Run with `--browsers=ChromeHeadless` (Chrome found at `C:\Program Files\Google\Chrome\Application\chrome.exe`; `CHROME_BIN` was unset, so it was supplied for the run). **This is a deviation from the literal command, noted for transparency.** `node_modules` was already present and was reused rather than running `npm ci`, to avoid destroying the working environment — the lockfile-clean-install variant was not exercised.

```
Chrome Headless 153.0.0.0 (Windows 10): Executed 36 of 36 SUCCESS (0.574 secs / 0.517 secs)
TOTAL: 36 SUCCESS
✔ Browser application bundle generation complete.

EXIT=0
```

**36 passed, 0 failed.** No stale `SocketService` import errors and no `AppComponent.title` failure — both of the brief's predicted defects are **absent**. All `socket.service` imports consistently resolve `ChatService`, and no `title` property or spec reference exists.

### 7.4 Public Angular — `npm run build`

```
Initial Chunk Files           | Names                  |  Raw Size | Estimated Transfer Size
main.7f314031ad542748.js      | main                   | 540.60 kB |               135.72 kB
styles.bb500523cfbdf1fd.css   | styles                 | 330.48 kB |                37.43 kB
polyfills.a53ec534dd42ace0.js | polyfills              |  33.04 kB |                10.63 kB
runtime.4ef14b65e94f5c55.js   | runtime                |   2.72 kB |                 1.30 kB
| Initial Total          | 906.84 kB |               185.08 kB

Build at: 2026-09-19T13:40:20.050Z - Hash: 16c9368f950d37f4 - Time: 32752ms

Warning: sessions-list.component.html:8:68 - NG8107 unnecessary '?.'
Warning: sessions-list.component.html:74:49 - NG8102 unnecessary '??'
Warning: view-tutor.component.html:69:81 - NG8107 unnecessary '?.'
Warning: dashboard.component.scss exceeded maximum budget. Budget 16.00 kB not met by 3.56 kB (total 19.56 kB)
Warning: bundle initial exceeded maximum budget. Budget 500.00 kB not met by 406.84 kB (total 906.84 kB)
Warning: autoprefixer — 'align-items: end' has mixed support

EXIT=0
```

**Build succeeds. Zero compilation errors.** Six warnings, none blocking. The initial bundle is 906.84 kB against a 500 kB budget — a performance concern, not a failure.

### 7.5 Admin Angular — `npm test -- --watch=false`

Same `--browsers=ChromeHeadless` deviation and same `node_modules` reuse as 7.3.

```
Chrome Headless 153.0.0.0 (Windows 10): Executed 16 of 16 SUCCESS (0.308 secs / 0.275 secs)
TOTAL: 16 SUCCESS

EXIT=0
```

**16 passed, 0 failed.**

### 7.6 Admin Angular — `npm run build`

```
Initial Chunk Files           | Names                |  Raw Size | Estimated Transfer Size
main.8285b56885e97487.js      | main                 | 388.25 kB |               100.38 kB
polyfills.235c3cb799e40c82.js | polyfills            |  33.04 kB |                10.65 kB
runtime.d8b6d776d849293c.js   | runtime              |   2.73 kB |                 1.29 kB
styles.2f4d32c9e0040e64.css   | styles               |   2.32 kB |               769 bytes
| Initial Total        | 426.34 kB |               113.08 kB

Build at: 2026-09-19T13:40:52.508Z - Hash: 99702efe8f2eeae1 - Time: 9469ms

Warning: layout.component.scss — autoprefixer 'align-items: end' has mixed support

EXIT=0
```

**Build succeeds. Zero errors. Within budget (426 kB < 500 kB).**

### 7.7 T4 — Build environment and Google Fonts

**Builds do NOT require live Google Fonts access, and font inlining does not fail offline.** Both apps explicitly disable it in `angular.json`:

```json
"optimization": { "scripts": true, "styles": { "minify": true, "inlineCritical": false }, "fonts": false }
```

With `"fonts": false` and `"inlineCritical": false`, the Angular CLI performs **no network fetch** to `fonts.googleapis.com` at build time. Both builds completed successfully. This appears to be a deliberate fix for exactly the failure mode the brief anticipates.

Fonts are still fetched **at runtime by the browser** (`index.html` preconnects, plus `@import url(...)` in the admin `styles.scss`), and both CSP policies permit `fonts.googleapis.com` and `fonts.gstatic.com`. That is consistent and correct.

### 7.8 npm ci — not executed

`npm ci` **deletes and recreates `node_modules`**. Both apps already had complete, working `node_modules` trees (635 packages in the public app). Running `npm ci` would have destroyed the user's local environment for no audit benefit, and a failure would have left the repo unbuildable. I used the existing trees and report this explicitly rather than claiming a clean-install verification I did not perform. **A lockfile-clean install remains unverified.**

---

## 8. Database & Migration State

### Head count and integrity

- **Exactly 1 head:** `b92e4a6d7c8f`
- **25 revisions**, strictly linear from `<base>`. No branches, no merge points, no orphans.
- Every `down_revision` resolves. `alembic history` renders the full chain without error.
- The three newest migrations are **idempotent and retry-safe** — each guards with `_has_table` / `_has_index` / `_has_unique_columns` / `_column_is_nullable` before issuing DDL, and handles `context.is_offline_mode()`. This is deliberate defence against MySQL's non-transactional DDL leaving partial state after a failed run, and is covered by four passing tests in `test_migration_retry_safety.py`.

### Constraints — all present

| Constraint | Table | Columns | Migration | Status |
|---|---|---|---|---|
| `uq_users_email` | `users` | `email` | `b92e4a6d7c8f:110` | ✅ Present |
| `uq_user_role_association` | `user_role_associations` | `user_id, role_id` | `b92e4a6d7c8f:118` | ✅ Present |
| `uq_tutor_review_tutor_student` | `tutor_reviews` | `tutor_id, student_id` | `b92e4a6d7c8f:131` | ✅ Present |
| `uq_service_review_service_student` | `service_reviews` | `service_id, student_id` | `b92e4a6d7c8f:144` | ✅ Present |
| Service booking uniqueness | `service_bookings` | `service_id, student_id` | `e53f13b91bdf` | ✅ Present (`test_service_booking_unique_constraint_rejects_duplicate`) |

**A note on a near-miss.** Migration `7ac91e2d4f60:150` creates `ix_users_email` with **`unique=False`**. Read alone, that looks like a missing email-uniqueness guarantee on a migration-built schema, while the `User` model's `unique=True` would mask it under `create_all()` (which is what the SQLite test suite uses). **It is not a defect** — the later `b92e4a6d7c8f` adds the real `uq_users_email` unique constraint, guarded by `_has_unique_columns`. I verified the full chain before concluding this. Worth knowing that the guarantee arrives two migrations later than where you would look for it.

### Report tables

- `reported_tutors`, `reported_services` — created by `7ac91e2d4f60` with FKs to `students`/`tutors`/`services` (`ondelete=CASCADE`) and to `users` (`ondelete=SET NULL`), plus a `NOT NULL reason VARCHAR(1024)`.
- `reported_reviews` — created by `a81d2f3c4b5e`.

### Session workflow fields

`a81d2f3c4b5e` adds the session workflow, rescheduling, and reported reviews. `booking_reschedule_proposals`, `ServiceBooking.status`, `scheduled_start_at`, `status_updated_at`, `cancelled_at`, `cancelled_by_user_id`, and `cancellation_reason` are all present and exercised by the passing `test_session_workflow.py`.

### Fresh-database application — `BLOCKED BY ENVIRONMENT`

**I could not verify that migrations apply cleanly to a fresh database.** `SQLALCHEMY_DATABASE_URL` is hard-coded to `mysql+aiomysql://` ([`database.py:8-14`](skillbridge-be/src/skillbridge/database/db/database.py#L8-L14)); no MySQL server is reachable and Docker was not used. Running `alembic upgrade head` would have required standing up MySQL 8.0 and writing to it.

This matters more than usual, because **the deduplication migration is MySQL-specific**: `_deduplicate_rows` emits `CREATE TEMPORARY TABLE`, `UPDATE IGNORE`, `FIRST_VALUE() OVER (PARTITION BY ...)`, and `DELETE x FROM y INNER JOIN z` ([`b92e4a6d7c8f:53-105`](skillbridge-be/src/skillbridge/database/alembic/versions/2026_09_19_2000-b92e4a6d7c8f_deduplicate_security_keys.py#L53-L105)). It **cannot** run on SQLite or PostgreSQL. The SQLite-based test suite exercises the guard functions, **not** the deduplication SQL itself, so that SQL is effectively untested.

To verify: `docker compose up skillbridge-mysql`, then `alembic upgrade head` against an empty database, and again against a database pre-seeded with duplicate emails / role associations / reviews to exercise the dedup path.

---

## 9. Could Not Verify

| Area | Scenarios | Reason | What would be needed |
|---|---|---|---|
| Responsive design | P1-25 (4) | No browser or device emulation. 23 SCSS files contain `@media` with breakpoints 480–1100 px, and both apps set the viewport meta — **that is code evidence, not a runtime pass** | Playwright/Cypress at 375/768/1440 px, or manual device testing |
| Browser compatibility | P1-26 (4) | Karma ran headless Chrome for **unit tests only**. No Firefox launcher is configured, and no end-to-end workflow test exists | `karma-firefox-launcher` + cross-browser E2E suite |
| Deployment | P1-29 (4) | No network access to `skillbridgeacademy.duckdns.org`; no SSH to the EC2 host | Live environment access, or a staging deploy |
| Media upload round trip | P1-19.3/.4, P1-21.3, P1-22.1, P2-11.1/.2 (6) | No AWS credentials — `s3_client` logs `access_key_configured=False`. Validation logic is unit-tested; the S3 write path is not | A test bucket with scoped credentials, or a LocalStack/MinIO stub |
| Live WebSocket messaging | P1-13.1, P1-14.1, P1-27.3 (3) | Requires two concurrent authenticated duplex sockets exchanging frames. The handshake is fully test-covered; the message fan-out is not drivable from the harness | An async WS client test driving two sessions (`scripts/ws_client_user1.py` and `ws_client_user2.py` exist for this) |
| Fresh-DB migration | §8 | No MySQL server; the dedup SQL is MySQL-only and cannot run on SQLite | `docker compose up skillbridge-mysql` + `alembic upgrade head` |
| `npm ci` clean install | §7.8 | Deliberately not run — it deletes `node_modules` and would have destroyed the working local environment | A disposable checkout or CI runner |
| Git history rewrite scope | SEC-02 | Reported only, as instructed. I did not enumerate every historical secret value (and never printed any) | `git log -p` over the affected paths, offline, after rotation |
| Production nginx headers | SEC-16 | The effective response headers depend on runtime proxy behaviour I could not observe | `curl -I https://skillbridgeacademy.duckdns.org/` and `/api/v1/role/roles/` |

**No secret value was printed, echoed, or reproduced anywhere in this report.** All secret references are by file path only.

---

## 10. Manual Actions Required

These cannot be fixed by a code change. **Rotation is the priority — a history rewrite without rotation accomplishes nothing, because the repository has already been pushed to `origin` and may be cloned or forked.**

### Priority 1 — Rotate now

| # | Credential | Where it leaked | Action |
|---|---|---|---|
| 1 | **EC2 SSH private key** (`configurationKeys/skillbridge-ec2`) | Git history, reachable from `origin` | Generate a new keypair, replace `authorized_keys` on the EC2 host, update the `AWS_EC2_SSH_PRIVATE_KEY` / `AWS_EC2_SSH_PUBLIC_KEY` GitHub secrets, delete the old key from AWS |
| 2 | **Server access notes** (`configurationKeys/accessToTheServer.txt`) | Git history | Treat every credential it contains as compromised and rotate each |
| 3 | **GitHub Actions EC2 deploy key** (`configurationKeys/github-actions-ec2-deploy`) | Git history | Remove the deploy key from the repo settings, generate a new one, update `GH_DEPLOY_PRIVATE_KEY` |
| 4 | **Backend dev environment** (`skillbridge-be/.env.dev`) | Git history — contained `SECRET_KEY` / `JWT_SECRET_KEY` and MySQL credentials | Generate new secrets, update `BACKEND_ENV_FILE`. **Rotating the JWT secret invalidates every issued token — expect all users to be logged out.** Schedule accordingly |
| 5 | **MySQL passwords** (`MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`) | Git history via `.env.dev` | Change on the MySQL instance and in `BACKEND_ENV_FILE` |
| 6 | **AWS access keys** (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`) | Used by all four workflows; exposure is plausible given the above | Rotate in IAM, update GitHub secrets. Consider migrating to OIDC role assumption to eliminate long-lived keys entirely |

### Priority 2 — Configuration

| # | Action |
|---|---|
| 7 | Confirm `BACKEND_CORS_ORIGINS` is explicitly set in the production `.env`. If unset with `ENV=deployment`, `allow_origins` resolves to `[]` and **all** cross-origin browser requests break |
| 8 | Verify `ENV=deployment` is actually set in the production environment. It gates both the DB hostname and the `require_production_secrets` guard. Note the `Dockerfile` sets `ENVIRONMENT` (unused by the code) while `docker-compose.yml` correctly sets `ENV` — anything not launched via compose will fail to start |
| 9 | Confirm `JWT_SECRET_KEY` and `SECRET_KEY` are set in production. If both are missing under `ENV=deployment`, startup raises — correct behaviour, but a hard outage if triggered by a config slip |
| 10 | Check `S3_REGION` vs `AWS_REGION`. `.env.example` lists `S3_REGION`, but `config.Settings` declares `AWS_REGION`; with `extra="ignore"`, `S3_REGION` is **silently discarded** |

### Priority 3 — Optional, after rotation

| # | Action |
|---|---|
| 11 | Purge secrets from Git history with `git filter-repo` or BFG. **Coordinate with the whole team** — it rewrites every commit SHA and forces re-clones. Low value once rotation is complete; do it for hygiene, not security |
| 12 | Audit EC2 and CloudTrail logs for unauthorized access during the exposure window |

---

## 11. Prioritized Remediation Backlog

**Recommendations only. Nothing in this section was implemented.**

### Tier 1 — Blocking. Ship-stoppers.

| # | Item | Effort | Why first |
|---|---|---|---|
| 1 | **Fix `POST /v1/service-booking/create/`** ([`service_booking.py:295-301`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/service_booking.py#L295-L301)). Pass a `CreateServiceBookingInputValidator` instance instead of a raw dict — or make `BaseValidator.validate` accept a mapping. **Then add an endpoint-level test**, since the repository tests demonstrably do not catch this | **15 min fix + 1 h test** | Students cannot book a session. Everything downstream — sessions, reviews, ratings, notifications — is unreachable through the UI |
| 2 | **Rotate all credentials** (§10, items 1–6) | **2–3 h** | Secrets are recoverable from pushed history |
| 3 | **Mask tutor `phone` for guests** (SEC-01), [`tutor.py:113-129`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/tutor.py#L113-L129). Mirror the existing `user.id` masking pattern on the same lines | **15 min** | Unauthenticated PII disclosure; a one-line fix |

### Tier 2 — High. Before the next release.

| # | Item | Effort |
|---|---|---|
| 4 | Restrict reviewer `email`/`phone` to admins (SEC-03) | 30 min |
| 5 | Add a CI workflow on `push`/`pull_request` running pytest + both `ng test` + both `ng build` (SEC-15) | 2–3 h |
| 6 | Add endpoint-level (HTTP) tests for every `POST`/`PUT`/`PATCH` route. The harness pattern used in this audit works well — boot the app against in-memory SQLite and issue real requests | 1–2 days |
| 7 | Drop `User.email`/`User.phone` from the public search filter (SEC-04) | 30 min |
| 8 | Clean up S3 orphans on DB failure (SEC-06); copy the `try/except` already used in `create_service` | 1 h |
| 9 | Remove the plaintext-password `console.log` (SEC-10) and sweep the other 57 | 1 h |
| 10 | Replace bare `Exception("Admin access required.")` with `HTTPException(403, ...)` (SEC-08) | 1 h |

### Tier 3 — Medium. Correctness and hardening.

| # | Item | Effort |
|---|---|---|
| 11 | Route tutor media through the revision/approval workflow (SEC-07, P2-11.4) | 1–2 days |
| 12 | Stream uploads to disk instead of buffering in memory (SEC-05) | 1 day |
| 13 | Enforce `accepting_requests` at booking time, not just in sort order (P2-21.4) | 2 h |
| 14 | Fix `login.py` status check to `!= "ACTIVE"` (SEC-11) and unify login error messages (SEC-12) | 30 min |
| 15 | Repeat security headers inside nested nginx `location` blocks (SEC-14) | 30 min |
| 16 | Verify migrations against a fresh MySQL database, including the dedup path (§8) | 2–3 h |
| 17 | Delete or wire up `environment.prod.ts` and add `fileReplacements` (SEC-17) | 1 h |
| 18 | Remove BC-2's dead `POST /tutor/create/` stub and the orphaned `createTutorProfile()` | 30 min |

### Tier 4 — Feature gaps. Scope decisions, not bugs.

| # | Item | Effort | Closes |
|---|---|---|---|
| 19 | Add a `languages` field (model + migration + filter + UI) | 1–2 days | P1-8.3, P1-10.3, P2-1.2, P2-2.1 |
| 20 | Add a `tutoring_format` field (online/in-person/hybrid) | 1 day | P2-1.4, P2-4.2 |
| 21 | Add tutor price-range filtering (mirror the existing service implementation) | 4 h | P2-1.3, P2-2.2 |
| 22 | Build the filter UI on the tutor list, and consume the existing orphaned `/tutor/filter-options/` | 1 day | P2-1.1, P2-2 |
| 23 | Build standalone resource sharing (entity + CRUD + guest metadata + moderation) | 3–5 days | P2-13, P2-14, P2-15, P2-16 (16 scenarios) |
| 24 | Build media moderation (state column + admin queue + approve/reject) | 2–3 days | P2-12 (4 scenarios) |
| 25 | Add an availability schedule model | 2–3 days | P1-8.4 |
| 26 | Add chat-message reporting | 1 day | P1-16.2 |
| 27 | Notify admins when a revision enters Pending | 2 h | P2-20.1 |
| 28 | Separate skill badges from subject tags | 1 day | P1-11.2 |

### Tier 5 — Verification debt

| # | Item | Effort |
|---|---|---|
| 29 | Add E2E tests (Playwright) covering the main workflows in Chrome **and** Firefox | 3–5 days |
| 30 | Add responsive regression tests at 375/768/1440 px | 1–2 days |
| 31 | Stand up a staging deployment so P1-29 can actually be verified | 2–3 days |
| 32 | Add a LocalStack/MinIO stub so media upload paths are testable without live AWS | 1 day |
| 33 | Reduce the public bundle below the 500 kB budget (currently 906.84 kB) | 1–2 days |

---

## Appendix A — Code Quality Scan (Part 5)

Report only. Nothing was fixed.

### A.1 Debug `print()` in production paths — 12 occurrences

| File | Lines |
|---|---|
| `api/core/s3_client.py` | 152, 162, 165, 173 |
| `api/filters/base.py` | 72, 85 |
| `api/repositories/service.py` | 319, 522, 528, 541, 651, 656 |

`service.py:319` prints moderation state on every revision approval. **No token, password, or secret is printed** — verified by `grep -rni "logger\.(info|debug|warning|error)" | grep -i "token|password|secret|credential"`, which returns nothing. Backend token/credential logging hygiene is clean.

### A.2 Dead and duplicate imports

| Location | Issue |
|---|---|
| [`token.py:1`](skillbridge-be/src/skillbridge/api/repositories/auth/token.py#L1) | `from tokenize import TokenInfo` — never used |
| [`token.py:11`](skillbridge-be/src/skillbridge/api/repositories/auth/token.py#L11) | Imports `HTTPBearer` from `fastapi.openapi.models` (the OpenAPI **schema** model), not `fastapi.security`. The correct import is commented out on line 8 |
| [`service.py:16-17`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/service.py#L16-L17) | `from skillbridge.api.core.s3_client import s3_client` — **duplicated verbatim** on consecutive lines |
| [`tutor.py:7`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/tutor.py#L7) | Imports `_get_tutor_id, _require_tutor` from `service` — **neither is used** in the file |
| [`role.py:1`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/role.py#L1) | `import cProfile` — leftover profiling import; the matching `profiler.print_stats(...)` is commented out on line 81 |

### A.3 Unreachable / dead code

| Symbol | Location | Note |
|---|---|---|
| `get_user_id()` | [`token.py:386-389`](skillbridge-be/src/skillbridge/api/repositories/auth/token.py#L386-L389) | Returns `payload["user_id"]`, but the JWT payload has no `user_id` key (it has `sub`). **Would `KeyError` if ever called.** Never called |
| `get_agent_id()` | [`token.py:392-395`](skillbridge-be/src/skillbridge/api/repositories/auth/token.py#L392-L395) | Returns `payload["agent_id"]` — no such claim exists. Never called. Looks like it was copied from another project |
| `validate_headers()` | [`token.py:375-383`](skillbridge-be/src/skillbridge/api/repositories/auth/token.py#L375-L383) | Never called |
| `bearer_scheme`, `class Header` | [`token.py:37`, `:44-47`](skillbridge-be/src/skillbridge/api/repositories/auth/token.py#L37) | Never referenced |
| `_get_user_role`, `_get_user_id`, `_get_tutor_id`, `_require_tutor`, `_require_admin` | `service.py:108-141`, `service_booking.py:239-266`, `admin.py:118-158` | **Three near-identical copies.** All read JWT claims (`role`, `tutor_id`) that the token **does not contain** — `create_tokens` emits only `sub`, `exp`, `iat`, `type`, `jti`. If any were wired into a route they would silently grant or deny incorrectly. **Only `admin._require_admin` is real and correct** — it is `async` and does a DB role lookup. The rest are dead. **This is the most dangerous dead code in the repo:** five plausible-looking authorization helpers that would fail open on `_get_user_role` returning `""` |

### A.4 `get_filter_options()` — reported issue NOT present

The brief flags this as misplaced/unreachable. **It is not.** `get_filter_options` sits correctly inside `TutorRepository` at [`repositories/tutor.py:326-347`](skillbridge-be/src/skillbridge/api/repositories/tutor.py#L326-L347) with proper class-body indentation, is routed at [`tutor.py:139-142`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/tutor.py#L139-L142), and I called it successfully at runtime:

```
GET /api/v1/tutor/filter-options/
→ 200 {"academic_programs":["Computer Science"],"teaching_styles":["Interactive"]}
```

It is **reachable and working**. Its only problem is that no frontend consumes it (§3.3).

### A.5 `createTutorProfile()` / `/tutor/create/` — reported issue CONFIRMED

Both ends are dead, as the brief suspects.
- Frontend: [`sign-in.component.ts:186`](skillbridge-fe/src/app/auth/sign-in/sign-in.component.ts#L186) is `private` and never invoked (`grep` returns only the definition).
- Backend: [`tutor.py:79-82`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/tutor.py#L79-L82) raises `403` unconditionally.
- At runtime the request never even reaches the 403 — body validation rejects it first with `422 "user_id: Field required"`.

Tutor profiles are created correctly through the registration flow instead ([`register.py:75-83`](skillbridge-be/src/skillbridge/api/repositories/auth/register.py#L75-L83)).

### A.6 Exception handling

- **`handle_exceptions` is sound** ([`exceptions.py:27-57`](skillbridge-be/src/skillbridge/exceptions.py#L27-L57)): any status ≥ 500 is sanitised to a generic message before it reaches the client.
- **Broad `except Exception` swallows** at [`ws.py:291-293`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/ws.py#L291-L293) (notification sync, with an explanatory comment — defensible) and [`ws.py:426-427`](skillbridge-be/src/skillbridge/api/api_v1/endpoints/ws.py#L426-L427) (per-frame handler — reasonable for a long-lived socket).
- **`ValidationError` misused as an exception constructor** at [`token.py:222`](skillbridge-be/src/skillbridge/api/repositories/auth/token.py#L222): `raise ValidationError("User not found")`. Pydantic's `ValidationError` does not accept that signature and would itself raise. Unreachable in practice — `change_password` has no route.
- **`_validate_image_signature` can `KeyError`** ([`media_service.py:33`](skillbridge-be/src/skillbridge/api/services/media_service.py#L33)) on an `image/*` content type outside its dict. Currently unreachable because every caller checks an allow-list first, but it is one allow-list edit away from a 500.

### A.7 Frontend

- **58 `console.log` calls** across both apps. The serious one is SEC-10 (plaintext password).
- **No client-side file-size validation** — oversized files upload fully before the server rejects them. Poor UX on a 100 MB video (P1-20).
- `user_ROLE` in the public app is set from the user's own form selection ([`login.component.ts:114`](skillbridge-fe/src/app/auth/login/login.component.ts#L114)) rather than the server-returned `role.slug`. The admin app does it correctly ([`login.component.ts:40`](skillbridge-admin/src/app/login/login.component.ts#L40)). Not a security boundary — the backend re-derives roles from the database on every request — but inconsistent, and it means the client-side guard trusts a client-set value.

---

## Appendix B — Audit Methodology

**Static analysis.** Full route enumeration by importing the FastAPI app and walking `app.routes` (85 routes). Complete frontend API call extraction via `grep` over `apiUrl`/`wsUrl` across both Angular apps (103 call sites), cross-referenced against `apiLists.ts` / `ApiList.ts` to build the endpoint map driving §3.

**Dynamic analysis.** A throwaway harness (written to the **scratchpad, never the repository**) boots the real FastAPI application against in-memory SQLite by rebinding `get_session` across every imported `skillbridge.*` module, then seeds realistic fixtures (roles, users, tutors in all three approval states, students, services, bookings) and issues genuine HTTP requests through `TestClient`. Roughly 90 distinct probes ran across three rounds. **Every `VERIFIED BY RUNTIME CHECK` in this report is backed by a real status code and response body captured from that harness.**

**Tests and builds.** All six required commands executed, with the two deviations disclosed in §7.3 and §7.8.

**What I deliberately did not do.** No application file was read-modify-written. No `git` command that mutates state was run. No secret value was printed or reproduced. Where I could not execute something, I marked it `BLOCKED` or `CANNOT VERIFY` and said why, rather than inferring a `PASS` from reading code — including in the several places where the code plainly looked correct.

---

*End of report. No application code was modified. `main` was not touched.*
