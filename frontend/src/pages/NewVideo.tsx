import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createVideo, ApiError } from "../api/client";

export default function NewVideo() {
  const [url, setUrl] = useState("");
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (u: string) => createVideo(u),
    onSuccess: (video) => {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      navigate(`/videos/${video.id}`);
    },
  });

  const errorMessage =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? "Something went wrong. Please try again."
        : null;

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (trimmed) mutation.mutate(trimmed);
  };

  return (
    <div>
      <h1>Learn from a video</h1>
      <p className="muted">
        Paste a YouTube link and we'll generate a summary and active-recall
        questions so the content actually sticks.
      </p>

      <form className="hero-input" onSubmit={onSubmit}>
        <input
          type="url"
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={mutation.isPending}
          autoFocus
        />
        <button className="btn" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Working..." : "Generate"}
        </button>
      </form>

      {mutation.isPending && (
        <div className="row" style={{ marginTop: 20 }}>
          <div className="spinner" />
          <span className="muted">
            Fetching transcript and generating study material. This can take up
            to a minute.
          </span>
        </div>
      )}

      {errorMessage && <p className="error">{errorMessage}</p>}
    </div>
  );
}
