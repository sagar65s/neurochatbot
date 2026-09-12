"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged,
  updateProfile,
  User,
} from "firebase/auth";
import { doc, setDoc, serverTimestamp } from "firebase/firestore";
import { auth, db } from "@/lib/firebase";
import { AppUser, AuthContextValue } from "@/types/auth";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function toAppUser(user: User): AppUser {
  return {
    uid: user.uid,
    email: user.email,
    displayName: user.displayName,
  };
}

/**
 * Writes/merges the users/{uid} Firestore profile doc. This is a
 * best-effort convenience mirror of the auth account — it is NOT
 * required for the app to function (conversations are scoped by uid
 * regardless of whether this doc exists). Deliberately never thrown from
 * signUp/logIn/logInWithGoogle: if this write fails (a transient
 * Firestore hiccup, a rules propagation delay right after account
 * creation, etc.), the user should still be signed in and land on
 * /chat — not see "Something went wrong" for a secondary write that has
 * nothing to do with whether their account/login actually succeeded.
 */
async function ensureUserDoc(user: User) {
  try {
    const ref = doc(db, "users", user.uid);
    await setDoc(
      ref,
      {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName ?? null,
        createdAt: serverTimestamp(),
      },
      { merge: true }
    );
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("Non-fatal: failed to write user profile doc to Firestore.", err);
  }
}

/**
 * Sets the Firebase Auth display name. Same non-fatal reasoning as
 * ensureUserDoc above — a failure here should never block sign-up.
 */
async function tryUpdateDisplayName(user: User, displayName: string) {
  try {
    await updateProfile(user, { displayName });
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("Non-fatal: failed to set display name.", err);
  }
}

function friendlyAuthError(code: string): string {
  const map: Record<string, string> = {
    "auth/email-already-in-use": "That email is already registered. Try logging in.",
    "auth/invalid-email": "Please enter a valid email address.",
    "auth/weak-password": "Password should be at least 6 characters.",
    "auth/user-not-found": "No account found with that email.",
    "auth/wrong-password": "Incorrect password.",
    "auth/invalid-credential": "Incorrect email or password.",
    "auth/popup-closed-by-user": "Google sign-in was cancelled.",
    "auth/popup-blocked": "Your browser blocked the sign-in popup. Please allow popups for this site and try again.",
    "auth/too-many-requests": "Too many attempts. Please wait and try again.",
    // Almost always a Firebase Console setup issue, not a code bug —
    // surfacing the real cause here saves a lot of guessing.
    "auth/operation-not-allowed":
      "Google sign-in isn't enabled for this project yet. In Firebase Console, go to Authentication > Sign-in method > Google, and enable it.",
    "auth/unauthorized-domain":
      "This domain isn't authorized for sign-in. In Firebase Console, go to Authentication > Settings > Authorized domains and add this domain (localhost should already be listed for local dev).",
  };
  return map[code] ?? "Something went wrong. Please try again.";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser ? toAppUser(firebaseUser) : null);
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  async function signUp(email: string, password: string, displayName?: string) {
    setError(null);
    let cred;
    try {
      // Only the actual account-creation call can fail this signup —
      // everything after this point (display name, Firestore profile
      // doc) is best-effort and non-fatal, so a secondary hiccup there
      // never surfaces as "Something went wrong" for a signup that
      // actually succeeded.
      cred = await createUserWithEmailAndPassword(auth, email, password);
    } catch (err: any) {
      const msg = friendlyAuthError(err?.code ?? "");
      setError(msg);
      throw new Error(msg);
    }

    if (displayName) {
      await tryUpdateDisplayName(cred.user, displayName);
    }
    await ensureUserDoc(cred.user);

    // Set user state immediately rather than waiting for the
    // onAuthStateChanged listener to fire. Without this, there's a race:
    // router.push("/chat") right after signUp() can navigate before the
    // context's `user` updates, so ProtectedRoute sees user=null for a
    // moment and bounces back to /login.
    setUser(toAppUser(cred.user));
  }

  async function logIn(email: string, password: string) {
    setError(null);
    try {
      const cred = await signInWithEmailAndPassword(auth, email, password);
      setUser(toAppUser(cred.user)); // see note in signUp() above
    } catch (err: any) {
      const msg = friendlyAuthError(err?.code ?? "");
      setError(msg);
      throw new Error(msg);
    }
  }

  async function logInWithGoogle() {
    setError(null);
    let cred;
    try {
      const provider = new GoogleAuthProvider();
      cred = await signInWithPopup(auth, provider);
    } catch (err: any) {
      const msg = friendlyAuthError(err?.code ?? "");
      setError(msg);
      throw new Error(msg);
    }

    // Same reasoning as signUp() above — the popup sign-in itself
    // succeeded, so a Firestore profile-write hiccup must not block it.
    await ensureUserDoc(cred.user);
    setUser(toAppUser(cred.user));
  }

  async function logOut() {
    setError(null);
    await signOut(auth);
  }

  async function getIdToken(): Promise<string | null> {
    if (!auth.currentUser) return null;
    return auth.currentUser.getIdToken();
  }

  const value: AuthContextValue = {
    user,
    loading,
    error,
    signUp,
    logIn,
    logInWithGoogle,
    logOut,
    getIdToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
