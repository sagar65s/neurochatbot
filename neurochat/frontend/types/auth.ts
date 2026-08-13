export interface AppUser {
  uid: string;
  email: string | null;
  displayName: string | null;
}

export interface AuthContextValue {
  user: AppUser | null;
  loading: boolean;
  error: string | null;
  signUp: (email: string, password: string, displayName?: string) => Promise<void>;
  logIn: (email: string, password: string) => Promise<void>;
  logInWithGoogle: () => Promise<void>;
  logOut: () => Promise<void>;
  getIdToken: () => Promise<string | null>;
}
