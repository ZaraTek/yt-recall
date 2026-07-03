import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, sendChatMessage } from "../api/client";
import type { ChatMessage, Video } from "../types";

const SUGGESTIONS = [
  "Make the questions harder",
  "Add 5 more multiple-choice questions",
  "Rewrite the summary as bullet points",
  "Explain the main idea like I'm five",
];

export default function ChatPanel({ video }: { video: Video }) {
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const messages: ChatMessage[] = video.chat ?? [];

  const mutation = useMutation({
    mutationFn: (message: string) => sendChatMessage(video.id, message),
    onSuccess: (resp) => {
      queryClient.setQueryData(["video", video.id], resp.video);
      queryClient.invalidateQueries({ queryKey: ["videos"] });
    },
    onError: (err) => {
      setError(
        err instanceof ApiError ? err.message : "Something went wrong. Try again."
      );
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.length, mutation.isPending]);

  const send = (text: string) => {
    const message = text.trim();
    if (!message || mutation.isPending) return;
    setError(null);
    setInput("");
    mutation.mutate(message);
  };

  return (
    <div className="chat">
      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 && !mutation.isPending && (
          <div className="chat-empty">
            <p className="muted" style={{ marginTop: 0 }}>
              Ask about this video, or tell me how to customize your summary,
              key points, or practice questions.
            </p>
            <div className="chat-suggestions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="chat-suggestion"
                  onClick={() => send(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`chat-msg chat-msg-${m.role}`}>
            <div className="chat-bubble">{m.content}</div>
          </div>
        ))}

        {mutation.isPending && (
          <div className="chat-msg chat-msg-assistant">
            <div className="chat-bubble chat-typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      <form
        className="chat-input-row"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          type="text"
          className="chat-input"
          placeholder="Ask a question or request a change..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={mutation.isPending}
        />
        <button
          type="submit"
          className="btn"
          disabled={mutation.isPending || !input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}
