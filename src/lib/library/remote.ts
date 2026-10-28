import { getFirebaseApp } from '@/lib/firebase';
import type { LibraryState, User } from './types';

export const apiConfigured = Boolean(import.meta.env['VITE_LIBRARY_API_URL']);
export async function libraryCommand(command: string, args: unknown[]) {
  const app = getFirebaseApp();
  if (!app) throw new Error('Firebase is not configured');
  const { getAuth } = await import('firebase/auth');
  const user = getAuth(app).currentUser;
  if (!user) throw new Error('Please sign in first');
  const url = import.meta.env['VITE_LIBRARY_API_URL'];
  if (!url) throw new Error('The library service is not connected yet');
  const response = await fetch(`${url.replace(/\/$/, '')}/commands`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${await user.getIdToken()}` },
    body: JSON.stringify({ command, args }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Unable to save this change');
  return result.result;
}

export async function connectFirestore(update: (key: keyof LibraryState, rows: unknown) => void, session: (user: User | null) => void, error: (message: string) => void) {
  const app = getFirebaseApp();
  if (!app) return () => {};
  const { getAuth, onAuthStateChanged } = await import('firebase/auth');
  const { getFirestore, collection, doc, getDoc, onSnapshot, query, where } = await import('firebase/firestore');
  const db = getFirestore(app);
  let privateStops: (() => void)[] = [];
  const mapping = { books: 'books', copies: 'book_copies', reviews: 'reviews' } as const;
  const stops = Object.entries(mapping).map(([key, path]) => onSnapshot(collection(db, path), s => update(key as keyof LibraryState, s.docs.map(d => ({ ...d.data(), id: d.id }))), () => error('Catalog connection failed. Check Firestore rules.')));
  stops.push(onSnapshot(doc(db, 'settings', 'library'), s => { if (s.exists()) update('settings', s.data()); }, () => error('Library settings could not be loaded.')));
  const privateMap = { users: 'users', loans: 'loans', reservations: 'reservations', fines: 'fines', wishlists: 'wishlists', notifications: 'notifications', recent: 'recent', audit: 'audit' } as const;
  const authStop = onAuthStateChanged(getAuth(app), async authUser => {
    privateStops.forEach(stop => stop()); privateStops = [];
    for (const key of Object.keys(privateMap)) update(key as keyof LibraryState, []);
    session(null);
    try {
      let user: User | null = null;
      if (authUser) {
        const [profile, role] = await Promise.all([getDoc(doc(db, 'users', authUser.uid)), getDoc(doc(db, 'user_roles', authUser.uid))]);
        if (profile.exists()) user = { ...profile.data(), id: authUser.uid, role: role.data()?.['role'] ?? 'student' } as User;
      }
      session(user);
      const staff = user?.role === 'admin' || user?.role === 'librarian';
      if (user) {
        for (const [key, path] of Object.entries(privateMap)) {
          if (key === 'audit' && !staff) continue;
          const source = staff ? collection(db, path) : query(collection(db, path), where(key === 'users' ? 'id' : 'userId', '==', user.id));
          privateStops.push(onSnapshot(source, s => update(key as keyof LibraryState, s.docs.map(d => ({ ...d.data(), id: d.id }))), () => error('Account records could not be loaded.')));
        }
      }
      // Owner read path includes pending faculty submissions; public reads include approved only.
      privateStops.push(onSnapshot(user?.role === 'admin' ? collection(db, 'resources') : query(collection(db, 'resources'), where('approved', '==', true)), s => update('resources', s.docs.map(d => ({ ...d.data(), id: d.id }))), () => error('Resources could not be loaded.')));
      if (user && user.role !== 'admin') privateStops.push(onSnapshot(query(collection(db, 'resources'), where('submittedBy', '==', user.id)), s => update('resources', { ownerRows: s.docs.map(d => ({ ...d.data(), id: d.id })) }), () => error('Your submissions could not be loaded.')));
    } catch { error('Your library profile could not be loaded.'); }
  });
  return () => { authStop(); stops.forEach(s => s()); privateStops.forEach(s => s()); };
}
