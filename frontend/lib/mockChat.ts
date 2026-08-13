/**
 * makeId() is used throughout the chat UI to create temporary local IDs
 * for optimistic UI updates (user messages, pending assistant bubbles)
 * before/while the real backend response arrives.
 */
export function makeId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
