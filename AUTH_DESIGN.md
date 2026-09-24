# Section 2 — Authentication & Authorization design notes

## What's implemented in this repo

Basic JWT auth: `POST /auth/login` checks a username/password against
the `users` table (passwords stored hashed, never in plain text) and
returns a signed JWT containing the username and role. Every protected
endpoint requires that JWT in an `Authorization: Bearer <token>`
header, and `require_role(...)` further restricts some endpoints to
specific roles.

## Extending to production SSO/OIDC

**The chain:** `Application → SSO/OAuth2/OIDC → Identity Provider → JWT → API Gateway → AI Service`

In plain English: right now, this app *is* the identity provider — it
checks the password itself. In production, you don't want every
internal app reinventing login (and every app storing its own copy of
passwords, which is a growing security liability). Instead:

1. The user tries to log into the app, and the app redirects them to a
   **central Identity Provider** (Okta, Auth0, Azure AD, Google
   Workspace, etc.) instead of showing its own password box.
2. The user authenticates once with the Identity Provider (which can
   itself enforce MFA, company SSO, etc.).
3. The Identity Provider redirects the user back to the app with a
   **JWT it issued and signed** — the app never sees or stores the
   user's actual password at all.
4. That JWT is what gets sent on every subsequent API call, exactly
   like the JWT this repo already issues — the *format* barely
   changes, only *who* is allowed to mint the token changes (a trusted
   central authority instead of our own app).
5. In front of the actual FastAPI service, an **API Gateway** (or a
   sidecar/ingress) verifies the JWT's signature against the Identity
   Provider's public key before the request is even allowed to reach
   the AI service — so the AI service itself can stay simple and just
   trust "if this request got this far, the gateway already verified
   it."

This is a genuinely small code change in this repo: `decode_token()`
in `app/auth.py` would verify against the Identity Provider's public
key instead of our own `JWT_SECRET_KEY`, and `/auth/login` would be
replaced by a redirect to the Identity Provider. Everything downstream
(`get_current_user`, `require_role`) stays exactly the same, because
it only ever looked at claims *inside* the JWT.

## RBAC (Role-Based Access Control)

RBAC means permissions are attached to a **role**, not to each
individual user — you assign a user a role once, and every permission
that role carries comes along with it. This repo implements it for
real, not just in theory:

| Role | Can do | Enforced by |
|---|---|---|
| **Admin** | Use `/chat`, plus view aggregate usage via `/admin/stats` | `require_role("admin")` |
| **User** | Use `/chat` only | `require_role("admin", "user")` |
| **Read-only** | Neither `/chat` nor `/admin/stats` — in a fuller build, this role would be given a `GET /reports` style endpoint for viewing permitted data without being able to trigger new (costly) LLM calls | Blocked by `require_role` returning 403 |

The mechanism (`require_role` in `app/auth.py`) is a small factory
function: each protected endpoint declares which roles may enter, and
FastAPI runs that check *before* the endpoint's own code executes. In
a full production RBAC system this table of role→permission mappings
would typically live in the Identity Provider or a dedicated policy
service rather than hard-coded in the app, so permissions can be
changed centrally without a code deploy — but the enforcement pattern
at the API layer stays the same.
