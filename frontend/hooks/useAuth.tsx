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

async function ensureUserDoc(user: User) {
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
    // These two are almost always a Firebase Console setup issue, not a
    // code bug — surfacing the real cause here saves a lot of guessing.
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
    try {
      const cred = await createUserWithEmailAndPassword(auth, email, password);
      if (displayName) {
        await updateProfile(cred.user, { displayName });
      }
      await ensureUserDoc(cred.user);
      // Set user state immediately rather than waiting for the
      // onAuthStateChanged listener to fire. Without this, there's a
      // race: router.push("/chat") right after signUp() can navigate
      // before the context's `user` updates, so ProtectedRoute sees
      // user=null for a moment and bounces back to /login — which looks
      // like "signup needs two clicks" even though the account was
      // created successfully on the first click.
      setUser(toAppUser(cred.user));
    } catch (err: any) {
      const msg = friendlyAuthError(err?.code ?? "");
      setError(msg);
      throw new Error(msg);
    }
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
    try {
      const provider = new GoogleAuthProvider();
      const cred = await signInWithPopup(auth, provider);
      await ensureUserDoc(cred.user);
      setUser(toAppUser(cred.user)); // see note in signUp() above
    } catch (err: any) {
      const msg = friendlyAuthError(err?.code ?? "");
      setError(msg);
      throw new Error(msg);
    }
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
