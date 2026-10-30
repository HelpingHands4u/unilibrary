<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Architecture
- Keep all pages in TanStack Start routes and global UI in the root shell; this preserves the generated route tree and SSR boundaries.
- Use Firebase Auth and scoped Firestore listeners for live reads, with mutations sent to the same-origin /api/commands server route; it verifies the Firebase ID token with firebase-admin and enforces business rules in Firestore transactions.
- Store authoritative roles in Firestore user_roles, never profiles or browser storage; browser role display is not authorization.
- Keep localStorage and demo identities exclusively in unconfigured demonstration mode; never copy demo user records into a live Firebase session.
- Deploy everything as one Vercel project (Nitro vercel preset only when VERCEL is set); firebase-admin needs Node, so live saving targets Vercel rather than the Workers preview.
