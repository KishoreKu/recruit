# Westley Resource - Project Instructions

## Architecture & Infrastructure

- **Frontend**: Static HTML/CSS/JS hosted on **Firebase Hosting**.
- **Backend**: **Firebase Cloud Functions** (2nd Gen, Node 22).
- **Email Service**: **Microsoft Graph API** (via `axios` in Cloud Functions).
- **Secrets Management**: Handled via **Firebase Secret Manager**.
- **CI/CD**: Automatic deployment to Firebase on push to `main` via GitHub Actions.

## Contact Form Implementation

- **Location**: `contact.html`
- **Submission**: Sends POST request to `/api/contact`.
- **Backend Route**: Rewritten in `firebase.json` to point to the `contact` Cloud Function.
- **Form Handling**: 
  - Uses `e.stopImmediatePropagation()` to prevent conflicts with global handlers in `script.js`.
  - Provides detailed error feedback by displaying messages returned from the Microsoft Graph API.

## Local Development (Express)

- A local Express server exists in `server/` for development and testing of non-Firebase features.
- Local environment variables are stored in `server/.env` (gitignored).

## Secrets (Firebase Secret Manager)

The following secrets are required for the contact form to function:
- `MS_TENANT_ID`: Azure Active Directory Tenant ID.
- `MS_CLIENT_ID`: Azure App Registration Client ID.
- `MS_CLIENT_SECRET`: Azure App Registration Client Secret.
- `MS_SENDER`: The email address (support@westleyresource.com) authorized to send mail.

## Troubleshooting

- **Contact Form Errors**: If the form returns an error, check the Azure App Registration permissions (`Mail.Send` application permission + Admin Consent) and verify that secrets in Firebase match the Azure credentials.
- **Script Conflicts**: Ensure `e.stopImmediatePropagation()` is used in `contact.html` if adding new form logic to prevent global resets from `script.js`.

## Agentic AI Placement System (Azure Deployment)

The automated recruiter agents and orchestrator are deployed on **Microsoft Azure** to leverage the ISV Success credits:

- **Orchestrator URL**: `https://westley-agents.kindtree-748f04e0.centralus.azurecontainerapps.io`
- **Architecture**:
  - **Azure Container Apps**: Runs the 5 background agents (`ats-agent`, `vms-agent`, `matching-agent`, `submission-agent`, `self-healing-agent`) + the FastAPI orchestrator endpoint. Scaled to a minimum of `1 replica` to keep background loops active.
  - **Azure Database for PostgreSQL Flexible Server**: Hosted in `centralus` (`westley-db-pg`), enabled with `uuid-ossp` and `vector` extensions. Whitelisted for access from internal Azure resources (`AllowAllAzureIPs`).
  - **Azure Key Vault**: Stores credentials (`gemini-api-key`, `database-url`, and Microsoft Graph credentials).
  - **Azure Container Registry**: `westleyregistry.azurecr.io` builds the container image via cloud ACR Tasks.

- **Candidate Ingestion Flow**:
  - Candidates submit details and files on `candidates.html`.
  - The form intercepts submissions and uploads the data as `multipart/form-data` directly to `/ingest-resume-file` on the Azure Container App.
  - The orchestrator reads the file stream and uses **Gemini 2.0 Flash** directly in the cloud to extract raw text content, merging it with user metadata before enqueuing a self-healing `ingest_resume` task.

