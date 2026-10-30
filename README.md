# UniLibrary

University library and learning resource management, built with React, TypeScript, TanStack Start and Tailwind. Firebase handles authentication and Firestore stores records. A built-in TypeScript server route verifies Firebase ID tokens and owns trusted changes.

## Current boundary

Without Firebase configuration, the app runs a clearly labeled browser-local demonstration. Live Firestore operation requires the setup below. No private credentials belong in frontend variables or source control.

## Firebase setup

1. Create a Firebase project, enable **Authentication → Email/password**, and create a **Firestore database**.
2. Register a Web app under Project settings. Add its public configuration to Vercel environment variables (or an uncommitted local environment file):
   - `VITE_FIREBASE_API_KEY`
   - `VITE_FIREBASE_AUTH_DOMAIN`
   - `VITE_FIREBASE_PROJECT_ID`
   - `VITE_FIREBASE_APP_ID`
3. Add your Vercel domain and localhost to Firebase Auth authorized domains.
4. Install Firebase CLI and deploy the checked-in rules: `firebase deploy --only firestore:rules --project YOUR_PROJECT_ID`.
5. Register the first real student account through UniLibrary. An operator then promotes that UID with the bootstrap command below. Public registration cannot grant elevated roles.

## One-step Vercel deployment

Everything — pages and the saving service (`/api/commands`) — deploys as **one Vercel project**. No Render or Python host is needed.

1. Import the GitHub repo in Vercel, Framework preset **Other**, build command `bun run build`. Do not set an output directory or rewrites.
2. Environment variables: the `VITE_FIREBASE_*` values above, plus **`FIREBASE_SERVICE_ACCOUNT_JSON`** (whole service-account JSON; server-only, never prefixed with `VITE_`).
3. Deploy, then open `https://YOUR-APP.vercel.app/api/commands` — it should show `"configured": true`.

### First administrator

Register through the app, then locally run:

```bash
FIREBASE_SERVICE_ACCOUNT_JSON="$(cat key.json)" bun scripts/bootstrap-admin.ts YOUR_UID scripts/catalog-seed.json
```

## Viva overview

- **Read:** real-time Firestore subscriptions load public catalog data and only the signed-in member's private rows (staff have operational access).
- **Create/update/delete:** the frontend obtains a Firebase token, calls the built-in `/api/commands` route, and waits for success. The API verifies the token, loads the separate role, validates the operation and commits a Firestore transaction. Listeners display the saved result.
- **Security:** users can initially create only their own restricted profile. All library mutations are denied to direct browser writes. Roles are provisioned by a trusted operator or administrator through the API.
- **Digital resources:** material links, not fabricated file uploads; files should be hosted on an authorized university file service and linked here.
- **Payments:** demo payments are browser-only. Live students pay at the cashier; authorized staff record payments or waivers.

Library hours and contact details need the university's real information. Optional course reading lists, direct file uploads and production-scale pagination are not implemented.

