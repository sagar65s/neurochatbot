export type MessageRole = "user" | "assistant" | "system";

export type ProviderName = "gemini" | "openrouter" | "groq" | "stub";

export interface Citation {
  title: string;
  url: string;
}

export interface ChatMessageItem {
  id: string;
  role: MessageRole;
  content: string;
  modelUsed?: string;
  providerUsed?: ProviderName;
  citations?: Citation[];
  createdAt: number;
  pending?: boolean;
  error?: boolean;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updatedAt: number;
}
