import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteVideo, listVideos } from "../api/client";
import type { VideoSummary } from "../types";

export default function Library() {
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["videos"],
    queryFn: listVideos,
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => deleteVideo(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["videos"] }),
  });

  const videos: VideoSummary[] = (data ?? []).filter((v) =>
    v.title.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Your library</h1>
        <input
          placeholder="Search titles..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            border: "1px solid var(--border)",
            background: "var(--surface-2)",
            color: "var(--text)",
          }}
        />
      </div>

      {isLoading && (
        <div className="row" style={{ marginTop: 20 }}>
          <div className="spinner" />
        </div>
      )}
      {isError && <p className="error">Failed to load your library.</p>}

      {!isLoading && videos.length === 0 && (
        <p className="muted" style={{ marginTop: 20 }}>
          No videos yet. Head to <Link to="/">New</Link> to add your first one.
        </p>
      )}

      <div className="grid">
        {videos.map((video) => (
          <div className="video-card" key={video.id}>
            <Link to={`/videos/${video.id}`}>
              <img
                className="thumb"
                src={video.thumbnail ?? ""}
                alt={video.title}
                loading="lazy"
              />
            </Link>
            <div className="body">
              <Link to={`/videos/${video.id}`} className="title" style={{ color: "var(--text)" }}>
                {video.title}
              </Link>
              <span className="meta">{video.channel ?? "Unknown channel"}</span>
            </div>
            <div className="actions">
              <span className="meta">
                {new Date(video.created_at).toLocaleDateString()}
              </span>
              <button
                className="btn btn-danger"
                onClick={() => {
                  if (confirm("Remove this video from your library?")) {
                    removeMutation.mutate(video.id);
                  }
                }}
                disabled={removeMutation.isPending}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
