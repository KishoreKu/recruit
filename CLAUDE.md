# westleyresource

## gstack

For all web browsing tasks, use the `/browse` skill from gstack. Never use the `mcp__claude-in-chrome__*` tools.

### Available gstack skills:
- `/office-hours`
- `/plan-ceo-review`
- `/plan-eng-review`
- `/plan-design-review`
- `/design-consultation`
- `/design-shotgun`
- `/design-html`
- `/review`
- `/ship`
- `/land-and-deploy`
- `/canary`
- `/benchmark`
- `/browse`
- `/connect-chrome`
- `/qa`
- `/qa-only`
- `/design-review`
- `/setup-browser-cookies`
- `/setup-deploy`
- `/setup-gbrain`
- `/retro`
- `/investigate`
- `/document-release`
- `/codex`
- `/cso`
- `/autoplan`
- `/plan-devex-review`
- `/devex-review`
- `/careful`
- `/freeze`
- `/guard`
- `/unfreeze`
- `/gstack-upgrade`
- `/learn`

## Infrastructure

- **Hosting**: Firebase Hosting (GCP) — auto-deploys on push to `main` via GitHub Actions
- **Project**: `westleyresource-5131d`
- **Backend**: Firebase Cloud Functions (2nd gen, Node 22, `us-central1`)
- **Local dev server**: `server/` — Express + MongoDB + PostgreSQL (not deployed, local only)

## Contact Form

- Frontend: `contact.html` — fetches `POST /api/contact` (relative URL)
- Function: `functions/index.js` — Cloud Function `contact` handles the request
- Routing: `firebase.json` rewrites `/api/contact` → `contact` function
- Email: Microsoft Graph API → sends to `support@westleyresource.com` (shared mailbox under `westley-group.com` tenant)
- Secrets stored in Firebase Secret Manager: `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_SENDER`
- Azure app registration: `Westley Website Mailer` (client ID: `73a42835-311f-4ad4-b454-124fc554328b`)

## Environment

- `server/.env` — local only, gitignored. Contains Graph API credentials for local dev.
- Never commit `.env`. Secrets for production live in Firebase Secret Manager only.
- M365 tenant: `westley-group.com` (admin: `kishore@westley-group.com`)
