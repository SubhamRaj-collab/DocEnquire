import type { Citation } from './api';

export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  citations?: Citation[];
  model?: string;
  usage?: { prompt_tokens: number; completion_tokens: number };
  timestamp: Date;
  isStreaming?: boolean;
}

export type AnswerSegment =
  | { type: 'text'; value: string }
  | { type: 'citation'; label: string; index: number };
