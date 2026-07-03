export type QuestionType = "flashcard" | "mcq" | "open";

export interface Question {
  id: string;
  type: QuestionType;
  prompt: string;
  answer: string;
  options?: string[] | null;
  explanation?: string | null;
}

export interface VideoSummary {
  id: string;
  youtube_id: string;
  url: string;
  title: string;
  channel?: string | null;
  thumbnail?: string | null;
  created_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface Video extends VideoSummary {
  summary: string;
  key_points: string[];
  questions: Question[];
  notes: string;
  transcript_lang?: string | null;
  chat: ChatMessage[];
  updated_at?: string | null;
}

export interface ChatResponse {
  reply: string;
  updated: boolean;
  video: Video;
}

export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string | null;
}
