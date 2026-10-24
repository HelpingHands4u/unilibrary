// Firebase client (browser-safe, publishable config only).
// Set these in Vercel → Project → Environment Variables (and a local .env):
// VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, VITE_FIREBASE_PROJECT_ID, VITE_FIREBASE_APP_ID
import { initializeApp, getApps, type FirebaseApp } from "firebase/app";

const cfg = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY as string | undefined,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN as string | undefined,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID as string | undefined,
  appId: import.meta.env.VITE_FIREBASE_APP_ID as string | undefined,
};

export const firebaseConfigured = Boolean(cfg.apiKey && cfg.projectId && cfg.authDomain);

export function getFirebaseApp(): FirebaseApp | null {
  if (!firebaseConfigured || typeof window === "undefined") return null;
  return getApps()[0] ?? initializeApp(cfg);
}

/** Sign in with Firebase Auth, then read the role from Firestore users/{uid} (written only by admins / backend). */
export async function firebaseSignIn(email: string, password: string, register?: { name: string }) {
  const app = getFirebaseApp();
  if (!app) throw new Error("Firebase is not configured");
  const { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, updateProfile } = await import("firebase/auth");
  const { getFirestore, doc, getDoc, setDoc } = await import("firebase/firestore");
  const auth = getAuth(app);
  const db = getFirestore(app);
  const cred = register
    ? await createUserWithEmailAndPassword(auth, email, password)
    : await signInWithEmailAndPassword(auth, email, password);
  if (register) {
    await updateProfile(cred.user, { displayName: register.name });
    // Security rules must only allow role == "student" on self-create.
    await setDoc(doc(db, "users", cred.user.uid), { name: register.name, email, role: "student", maxBorrowLimit: 4, active: true });
  }
  const snap = await getDoc(doc(db, "users", cred.user.uid));
  const role = (snap.data()?.role as "student" | "librarian" | "admin" | "faculty") ?? "student";
  return { uid: cred.user.uid, email, name: cred.user.displayName ?? email, role };
}
