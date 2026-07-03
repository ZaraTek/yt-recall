import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { updateNotes } from "../api/client";

type SaveState = "idle" | "saving" | "saved" | "error";

export default function NotesEditor({
  videoId,
  initialNotes,
}: {
  videoId: string;
  initialNotes: string;
}) {
  const [notes, setNotes] = useState(initialNotes);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const mutation = useMutation({
    mutationFn: (value: string) => updateNotes(videoId, value),
    onSuccess: () => setSaveState("saved"),
    onError: () => setSaveState("error"),
  });

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  const onChange = (value: string) => {
    setNotes(value);
    setSaveState("saving");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => mutation.mutate(value), 800);
  };

  const label: Record<SaveState, string> = {
    idle: "",
    saving: "Saving...",
    saved: "Saved",
    error: "Failed to save",
  };

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>Notes</h2>
        <span
          className="muted"
          style={{ color: saveState === "error" ? "var(--bad)" : undefined }}
        >
          {label[saveState]}
        </span>
      </div>
      <textarea
        className="notes"
        value={notes}
        placeholder="Jot down your own takeaways..."
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
