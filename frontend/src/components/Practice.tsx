import { useMemo, useState } from "react";
import type { Question } from "../types";

interface PracticeProps {
  questions: Question[];
  onExit: () => void;
}

export default function Practice({ questions, onExit }: PracticeProps) {
  const [index, setIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [finished, setFinished] = useState(false);

  const total = questions.length;
  const question = questions[index];

  const shuffledOptions = useMemo(() => {
    if (question?.type !== "mcq" || !question.options) return [];
    return [...question.options].sort(() => Math.random() - 0.5);
    // Re-shuffle only when the question id changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question?.id]);

  if (total === 0) {
    return (
      <div className="practice card">
        <p className="muted">No practice questions available for this video.</p>
        <button className="btn btn-ghost" onClick={onExit}>
          Back
        </button>
      </div>
    );
  }

  const goNext = () => {
    if (index + 1 >= total) {
      setFinished(true);
      return;
    }
    setIndex((i) => i + 1);
    setAnswered(false);
    setSelected(null);
    setRevealed(false);
  };

  const grade = (correct: boolean) => {
    if (correct) setScore((s) => s + 1);
    setAnswered(true);
  };

  if (finished) {
    const pct = Math.round((score / total) * 100);
    return (
      <div className="practice card" style={{ textAlign: "center" }}>
        <h2>Session complete</h2>
        <p style={{ fontSize: 40, fontWeight: 800, margin: "12px 0" }}>
          {score} / {total}
        </p>
        <p className="muted">You scored {pct}%.</p>
        <div className="grade-row">
          <button
            className="btn"
            onClick={() => {
              setIndex(0);
              setScore(0);
              setAnswered(false);
              setSelected(null);
              setRevealed(false);
              setFinished(false);
            }}
          >
            Practice again
          </button>
          <button className="btn btn-ghost" onClick={onExit}>
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="practice">
      <div className="progress">
        <div style={{ width: `${(index / total) * 100}%` }} />
      </div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <span className="pill">{question.type}</span>
        <span className="muted">
          {index + 1} / {total} · Score {score}
        </span>
      </div>

      {question.type === "flashcard" && (
        <>
          <div
            className="card flashcard"
            onClick={() => setRevealed((r) => !r)}
          >
            {revealed ? question.answer : question.prompt}
          </div>
          {!revealed && (
            <p className="muted" style={{ textAlign: "center" }}>
              Click the card to reveal the answer.
            </p>
          )}
          {revealed && !answered && (
            <div className="grade-row">
              <button className="btn btn-danger" onClick={() => grade(false)}>
                Got it wrong
              </button>
              <button className="btn" onClick={() => grade(true)}>
                Got it right
              </button>
            </div>
          )}
        </>
      )}

      {question.type === "mcq" && (
        <div className="card">
          <p style={{ fontWeight: 600, marginTop: 0 }}>{question.prompt}</p>
          {shuffledOptions.map((opt) => {
            const isAnswer = opt === question.answer;
            const isSelected = opt === selected;
            let cls = "option";
            if (answered && isAnswer) cls += " correct";
            else if (answered && isSelected && !isAnswer) cls += " wrong";
            return (
              <button
                key={opt}
                className={cls}
                disabled={answered}
                onClick={() => {
                  setSelected(opt);
                  grade(isAnswer);
                }}
              >
                {opt}
              </button>
            );
          })}
          {answered && question.explanation && (
            <div className="reveal">{question.explanation}</div>
          )}
        </div>
      )}

      {question.type === "open" && (
        <div className="card">
          <p style={{ fontWeight: 600, marginTop: 0 }}>{question.prompt}</p>
          <p className="muted">
            Recall the answer in your head (or jot it down), then reveal the
            model answer and grade yourself.
          </p>
          {!revealed ? (
            <button className="btn" onClick={() => setRevealed(true)}>
              Reveal answer
            </button>
          ) : (
            <>
              <div className="reveal">
                <strong>Model answer:</strong> {question.answer}
                {question.explanation && (
                  <p className="muted" style={{ marginBottom: 0 }}>
                    {question.explanation}
                  </p>
                )}
              </div>
              {!answered && (
                <div className="grade-row">
                  <button
                    className="btn btn-danger"
                    onClick={() => grade(false)}
                  >
                    Missed it
                  </button>
                  <button className="btn" onClick={() => grade(true)}>
                    I knew it
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {answered && (
        <div className="grade-row">
          <button className="btn" onClick={goNext}>
            {index + 1 >= total ? "See results" : "Next question"}
          </button>
        </div>
      )}

      <div style={{ textAlign: "center", marginTop: 20 }}>
        <button className="btn btn-ghost" onClick={onExit}>
          Exit practice
        </button>
      </div>
    </div>
  );
}
