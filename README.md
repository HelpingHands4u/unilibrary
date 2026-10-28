# UniLibrary

University library and learning resource management, built with React, TypeScript, TanStack Start and Tailwind. Firebase handles authentication and Firestore stores records. The separate FastAPI service verifies Firebase ID tokens and owns trusted changes.

## Current boundary

Without Firebase configuration, the app runs a clearly labeled browser-local demonstration. Live Firestore operation requires the setup below. No private credentials belong in frontend variables or source control. The preview does not run the Python service, and no live Firebase project has been connected or verified here.

## Firebase setup

1. Create a Firebase project, enable **Authentication → Email/password**, and create a **Firestore database**.
2. Register a Web app under Project settings. Add its public configuration to Vercel environment variables (or an uncommitted local environment file):
   - `VITE_FIREBASE_API_KEY`
   - `VITE_FIREBASE_AUTH_DOMAIN`
   - `VITE_FIREBASE_PROJECT_ID`
   - `VITE_FIREBASE_APP_ID`
   - `VITE_LIBRARY_API_URL` — HTTPS origin of the separately deployed Python service.
3. Add your Vercel domain and localhost to Firebase Auth authorized domains.
4. Install Firebase CLI and deploy the checked-in rules: `firebase deploy --only firestore:rules --project YOUR_PROJECT_ID`.
5. Register the first real student account through UniLibrary. An operator then promotes that UID with the bootstrap command below. Public registration cannot grant elevated roles.

## Python service

Use Python 3.11+ on a host supporting Python web services (for example Cloud Run or Render):

```sh
python -m pip install -r backend/requirements.txt
# From the backend directory:
uvicorn main:app --host 0.0.0.0 --port 8000
```

Configure `ALLOWED_ORIGINS` as a comma-separated list of exact frontend origins. Configure `FIREBASE_SERVICE_ACCOUNT_JSON` in the Python host's secret store, or use Application Default Credentials on Google Cloud. Never add this credential to Vercel's VITE variables or commit it.

`GET /health` checks service availability. `POST /commands` requires a valid Firebase bearer ID token and uses the role document, not the request body. Firestore transactions enforce eligibility and update books, copies, loans, fines, holds, notifications and audit records atomically. For this academic-sized system a shared revision serializes commands and the service reads library collections per command; large production libraries need narrower transactional queries and pagination.

### Initial administrator and catalog

```sh
bun scripts/export-seed.ts
# With Python host credentials available, from backend:
python bootstrap.py --admin-uid EXISTING_FIREBASE_UID --seed ../backend/catalog-seed.json
```

The operator must select a real, existing account. The script imports catalog/copies/resource sample metadata and settings only, not demo users, loans, fines, or fabricated verified reviews. Sample resource records without links are visibly marked as files not supplied. Faculty can submit HTTPS material links; administrators approve them.

### Vercel

Import the repository with Framework preset **Other**, use `bun install` and `bun run build`. `VERCEL` selects Nitro's Vercel output automatically; do not use a single-page fallback rewrite or set `dist` as the output directory. Deploy the Python service separately first and set its HTTPS URL in `VITE_LIBRARY_API_URL`. Deployments have not been executed or verified here.

## Tests

```sh
bun run test
PYTHONPATH=backend python -m pytest backend/tests -q
```

The application includes rule tests and Python authorization/transaction-domain tests. Live authentication, Firestore rule enforcement, persistence and Vercel deployment must additionally be tested against your configured services. Current default policy is 14-day loans, ₹5/day late fines, four loans, two renewals and borrowing blocked when unpaid fines exceed ₹100. These are editable starting values, not verified university policy.

## Viva overview

- **Read:** real-time Firestore subscriptions load public catalog data and only the signed-in member's private rows (staff have operational access).
- **Create/update/delete:** the frontend obtains a Firebase token, calls FastAPI, and waits for success. The API verifies the token, loads the separate role, validates the operation and commits a Firestore transaction. Listeners display the saved result.
- **Security:** users can initially create only their own restricted profile. All library mutations are denied to direct browser writes. Roles are provisioned by a trusted operator or administrator through the API.
- **Digital resources:** material links, not fabricated file uploads; files should be hosted on an authorized university file service and linked here.
- **Payments:** demo payments are browser-only. Live students pay at the cashier; authorized staff record payments or waivers.

Library hours and contact details need the university's real information. Optional course reading lists, direct file uploads and production-scale pagination are not implemented.
