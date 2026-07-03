import json
import uuid

from google import genai
from google.genai import types

from config import get_settings
from models import Question


_SYSTEM_PROMPT = """You are an expert learning coach. Given the transcript of a YouTube \
video, produce study material that helps a learner retain and actively recall the content.

Return ONLY valid JSON matching this schema:
{
  "summary": string,            // 2-4 paragraph summary of the video
  "key_points": string[],       // 4-8 concise bullet takeaways
  "questions": [                // 6-10 active-recall questions
    {
      "type": "mcq",
      "prompt": string,
      "answer": string,          // the correct/model answer
      "options": string[],       // 3-4 options that MUST include the exact answer
      "explanation": string | null // short explanation of why the answer is correct
    }
  ]
}

Rules:
- Every question MUST be a multiple-choice question with "type": "mcq".
- For each question, "options" MUST contain the exact "answer" text as one of the entries.
- Keep prompts self-contained (do not reference "the video" or "the speaker").
- Do not include any markdown or text outside the JSON object.
"""

_CHAT_SYSTEM_PROMPT = """You are a friendly, knowledgeable study assistant embedded in a \
YouTube learning app. You are helping a learner with ONE specific video. You are given the \
current study material for that video (summary, key points, practice questions), the learner's \
private notes, and — when available — the video transcript, plus the running conversation.

You can do two things:
1. Answer questions and discuss the video's content.
2. Customize the stored study material when the learner asks (e.g. "make the questions harder", \
"add more multiple-choice questions", "rewrite the summary as bullet points", "focus on topic X", \
"explain like I'm five", "give me 15 questions").

Return ONLY valid JSON matching this schema:
{
  "reply": string,             // your short, friendly conversational reply (ALWAYS required)
  "apply_changes": boolean,    // true only when you are updating the stored study material
  "summary": string | null,       // full replacement summary, or null to leave unchanged
  "key_points": string[] | null,  // full replacement list, or null to leave unchanged
  "questions": [                   // full replacement question set, or null to leave unchanged
    {
      "type": "flashcard" | "mcq" | "open",
      "prompt": string,
      "answer": string,
      "options": string[] | null,   // REQUIRED for mcq (3-4 options incl. the exact answer), else null
      "explanation": string | null
    }
  ] | null
}

Rules:
- ALWAYS fill "reply" with a concise response: answer the question, or describe the change you made.
- Set apply_changes=false and leave summary/key_points/questions null for ordinary questions or chit-chat.
- Set apply_changes=true ONLY when the learner clearly wants the stored material changed. Then \
include the COMPLETE new version of whatever you changed (not a diff), and leave untouched fields null.
- When updating questions, return 4-15 questions. Default every question to "type": "mcq" unless \
the learner explicitly asks for flashcards or open-ended questions. For "mcq" the "options" MUST \
include the exact "answer" text.
- Keep question prompts self-contained (don't reference "the video" or "the speaker").
- Ground everything in the provided material/transcript; do not invent facts it does not support.
- Output no markdown or text outside the JSON object.
"""

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["mcq"]},
                    "prompt": {"type": "string"},
                    "answer": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "explanation": {"type": "string"},
                },
                "required": ["type", "prompt", "answer", "options"],
            },
        },
    },
    "required": ["summary", "key_points", "questions"],
}


class GeminiError(Exception):
    """Raised when Gemini fails to produce usable study material."""


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = get_settings().gemini_api_key
        if not api_key:
            raise GeminiError("GEMINI_API_KEY is not configured")
        _client = genai.Client(api_key=api_key)
    return _client


# Transcripts can be long; cap to keep within a reasonable token budget.
# Kept tighter than the model's limit because latency scales with input size
# and a ~24k-char (~6k token) window captures more than enough for a study
# summary of even a long video.
_MAX_TRANSCRIPT_CHARS = 24000

# Chat also passes the transcript for grounding, but leaves room for history.
_MAX_CHAT_TRANSCRIPT_CHARS = 24000


def _parse_payload(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def _build_questions(items: list[dict]) -> list[Question]:
    questions: list[Question] = []
    for item in items:
        q_type = item.get("type")
        if q_type not in {"flashcard", "mcq", "open"}:
            continue
        options = item.get("options")
        if q_type == "mcq":
            if not options:
                continue
            if item.get("answer") not in options:
                options = [*options, item["answer"]]
        else:
            options = None
        questions.append(
            Question(
                id=str(uuid.uuid4()),
                type=q_type,
                prompt=item.get("prompt", ""),
                answer=item.get("answer", ""),
                options=options,
                explanation=item.get("explanation"),
            )
        )
    return questions


def generate_study_material(transcript: str, title: str) -> dict:
    """Call Gemini and return {summary, key_points, questions}. Retries JSON parse once."""
    transcript = transcript[:_MAX_TRANSCRIPT_CHARS]
    contents = f"Video title: {title}\n\nTranscript:\n{transcript}"
    return _run(contents)


def generate_study_material_from_url(youtube_url: str, title: str) -> dict:
    """Fallback: let Gemini watch the YouTube video directly (no transcript needed)."""
    contents = types.Content(
        parts=[
            types.Part(file_data=types.FileData(file_uri=youtube_url)),
            types.Part(
                text=(
                    f"Video title: {title}\n\n"
                    "Watch this video and produce the study material."
                )
            ),
        ]
    )
    return _run(contents)


def _run(contents) -> dict:
    client = _get_client()
    settings = get_settings()
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=_RESPONSE_SCHEMA,
        temperature=0.4,
        max_output_tokens=settings.gemini_max_output_tokens,
    )

    model = settings.gemini_model
    last_error: Exception | None = None
    for _ in range(2):
        try:
            response = client.models.generate_content(
                model=model, contents=contents, config=config
            )
            payload = _parse_payload(response.text or "")
            return {
                "summary": payload.get("summary", ""),
                "key_points": [str(p) for p in payload.get("key_points", [])],
                "questions": _build_questions(payload.get("questions", [])),
            }
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            last_error = exc
            continue
        except Exception as exc:  # noqa: BLE001
            raise GeminiError(f"Gemini request failed: {exc}") from exc

    raise GeminiError(f"Could not parse study material from Gemini: {last_error}")


def _build_material_context(
    *,
    title: str,
    summary: str,
    key_points: list[str],
    questions: list[Question],
    notes: str,
    transcript: str | None,
) -> str:
    lines = [f"Video title: {title}", ""]

    lines.append("Current summary:")
    lines.append(summary or "(none yet)")
    lines.append("")

    lines.append("Current key points:")
    if key_points:
        lines.extend(f"- {p}" for p in key_points)
    else:
        lines.append("(none yet)")
    lines.append("")

    lines.append("Current practice questions:")
    if questions:
        for i, q in enumerate(questions, 1):
            lines.append(f"{i}. [{q.type}] {q.prompt}")
            lines.append(f"   answer: {q.answer}")
            if q.options:
                lines.append(f"   options: {q.options}")
    else:
        lines.append("(none yet)")
    lines.append("")

    if notes and notes.strip():
        lines.append("Learner's private notes:")
        lines.append(notes.strip())
        lines.append("")

    if transcript and transcript.strip():
        lines.append("Video transcript (may be truncated):")
        lines.append(transcript[:_MAX_CHAT_TRANSCRIPT_CHARS])

    return "\n".join(lines)


def chat_about_video(
    *,
    title: str,
    summary: str,
    key_points: list[str],
    questions: list[Question],
    notes: str,
    transcript: str | None,
    history: list[dict],
    message: str,
) -> dict:
    """Multi-turn chat about a video. May return customized study material.

    Returns {reply, apply_changes, summary?, key_points?, questions?}. The
    summary/key_points/questions keys are only present when the model chose to
    update them.
    """
    client = _get_client()

    context = _build_material_context(
        title=title,
        summary=summary,
        key_points=key_points,
        questions=questions,
        notes=notes,
        transcript=transcript,
    )
    system_instruction = f"{_CHAT_SYSTEM_PROMPT}\n\n---\n{context}"

    contents = []
    for msg in history:
        role = "model" if msg.get("role") == "assistant" else "user"
        text = str(msg.get("content", ""))
        if not text:
            continue
        contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        temperature=0.6,
    )

    model = get_settings().gemini_model
    last_error: Exception | None = None
    for _ in range(2):
        try:
            response = client.models.generate_content(
                model=model, contents=contents, config=config
            )
            payload = _parse_payload(response.text or "")
            reply = str(payload.get("reply", "")).strip()
            if not reply:
                raise ValueError("Gemini returned an empty reply.")

            result: dict = {
                "reply": reply,
                "apply_changes": bool(payload.get("apply_changes")),
            }
            if result["apply_changes"]:
                if payload.get("summary") is not None:
                    result["summary"] = str(payload["summary"])
                if payload.get("key_points") is not None:
                    result["key_points"] = [
                        str(p) for p in payload.get("key_points") or []
                    ]
                if payload.get("questions") is not None:
                    result["questions"] = _build_questions(
                        payload.get("questions") or []
                    )
            return result
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            last_error = exc
            continue
        except Exception as exc:  # noqa: BLE001
            raise GeminiError(f"Gemini request failed: {exc}") from exc

    raise GeminiError(f"Could not parse chat response from Gemini: {last_error}")
