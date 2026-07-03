import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getVideo } from "../api/client";
import NotesEditor from "../components/NotesEditor";
import Practice from "../components/Practice";
import ChatPanel from "../components/ChatPanel";

export default function VideoDetail() {
  const { id = "" } = useParams();
  const [practicing, setPracticing] = useState(false);

  const { data: video, isLoading, isError } = useQuery({
    queryKey: ["video", id],
    queryFn: () => getVideo(id),
  });

  if (isLoading) {
    return (
      <div className="row">
        <div className="spinner" />
      </div>
    );
  }

  if (isError || !video) {
    return (
      <div>
        <p className="error">Could not load this video.</p>
        <Link to="/library">Back to library</Link>
      </div>
    );
  }

  if (practicing) {
    return (
      <Practice questions={video.questions} onExit={() => setPracticing(false)} />
    );
  }

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>{video.title}</h1>
      </div>
      <p className="muted">
        {video.channel} ·{" "}
        <a href={video.url} target="_blank" rel="noreferrer">
          Watch on YouTube
        </a>
      </p>

      <div className="row" style={{ marginTop: 12 }}>
        <button
          className="btn"
          onClick={() => setPracticing(true)}
          disabled={video.questions.length === 0}
        >
          Practice ({video.questions.length} questions)
        </button>
        <Link to="/library" className="btn btn-ghost">
          Back to library
        </Link>
      </div>

      <section className="section">
        <h2>Summary</h2>
        <div className="card">
          {video.summary.split(/\n{2,}/).map((para, i) => (
            <p key={i} style={{ marginTop: i === 0 ? 0 : undefined }}>
              {para}
            </p>
          ))}
        </div>
      </section>

      {video.key_points.length > 0 && (
        <section className="section">
          <h2>Key points</h2>
          <div className="card">
            <ul className="key-points">
              {video.key_points.map((point, i) => (
                <li key={i}>{point}</li>
              ))}
            </ul>
          </div>
        </section>
      )}

      <section className="section">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2 style={{ marginBottom: 8 }}>Chat</h2>
          <span className="pill">Gemini</span>
        </div>
        <div className="card">
          <ChatPanel video={video} />
        </div>
      </section>

      <section className="section">
        <div className="card">
          <NotesEditor videoId={video.id} initialNotes={video.notes} />
        </div>
      </section>
    </div>
  );
}
