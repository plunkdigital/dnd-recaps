"""Dependency-free CLI. Run from the repository root; see README.md."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid


TRANSCRIBE_MODEL = "gpt-4o-transcribe-diarize"
MAX_AUDIO_BYTES = 24_000_000  # Conservative headroom below the documented upload limit.
MAX_CONTEXT_CHARS = 24_000


def load_environment(path):
    """Load simple dotenv assignments at runtime without executing shell content.

    Only application settings are imported; existing process values take precedence.
    Values and source lines are never included in validation errors.
    """
    if not path.exists():
        return
    settings = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        if name.strip() not in {"OPENAI_API_KEY", "RECAP_MODEL"}:
            continue
        if not separator:
            raise ValueError(f"Invalid configuration assignment at line {number}.")
        value = value.strip()
        if value.startswith(("'", '"')):
            quote = value[0]
            end = value.find(quote, 1)
            if end < 0 or (value[end + 1:].strip() and not value[end + 1:].lstrip().startswith("#")):
                raise ValueError(f"Invalid configuration quoting at line {number}.")
            value = value[1:end]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        # No interpolation, shell expansion, or escape processing.
        if value:
            settings.setdefault(name.strip(), value)
    for name, value in settings.items():
        os.environ.setdefault(name, value)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    """Replace atomically; a failed process must not leave a valid-looking cache."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False) as stream:
        tmp = Path(stream.name)
        stream.write(value)
    tmp.replace(path)


def save_json(path, value):
    write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def session_path(root, session):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", session):
        raise ValueError("Session ID must be 1–80 lowercase letters, digits, _ or -.")
    base = (root / "sessions").resolve()
    path = base / session
    if path.resolve().parent != base:
        raise ValueError("Session path must stay inside sessions/.")
    return path


def run_media(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"{command[0]} failed; check that the source has an audio stream.")
    return result.stdout


def prepare(root, session, audio):
    dest = session_path(root, session)
    if dest.exists():
        raise ValueError("Session already exists. Use a new ID; originals are never overwritten.")
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise ValueError(f"Install {tool} before preparing audio (see README.md).")
    audio = audio.resolve(strict=True)
    duration = float(run_media(["ffprobe", "-v", "error", "-show_entries",
                               "format=duration", "-of", "default=nw=1:nk=1", str(audio)]))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Recording must have a finite positive duration.")
    # Build in a staging directory. A failed conversion never looks like a ready session.
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent, prefix=".prepare-") as temp:
        stage = Path(temp) / "session"
        (stage / "audio").mkdir(parents=True)
        original = stage / "audio" / ("original" + audio.suffix.lower())
        shutil.copy2(audio, original)
        chunks = []
        # Fixed cuts with five seconds of overlap retain boundary speech. We preserve
        # duplicate boundary segments rather than silently deleting uncertain speech.
        for index, offset in enumerate(range(0, math.ceil(duration), 1195)):
            relative = f"audio/chunks/c{index:04d}.mp3"
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            run_media(["ffmpeg", "-nostdin", "-v", "error", "-i", str(original),
                       "-ss", str(offset), "-t", "1200", "-map", "0:a:0", "-vn",
                       "-ac", "1", "-ar", "24000", "-b:a", "64k", str(target)])
            if not 0 < target.stat().st_size < MAX_AUDIO_BYTES:
                raise ValueError("Prepared audio chunk is empty or over the upload limit.")
            chunks.append({"id": f"c{index:04d}", "path": relative,
                           "offset_seconds": offset, "sha256": digest(target)})
        save_json(stage / "manifest.json", {
            "schema_version": 1, "session": session,
            "source": {"path": str(original.relative_to(stage)),
                       "sha256": digest(original), "duration_seconds": duration},
            "chunks": chunks,
        })
        shutil.copy2(root / "templates/session.json", stage / "session.json")
        stage.rename(dest)
    print(f"Prepared {len(chunks)} chunks in {dest}; no files uploaded.")


def api(endpoint, body, content_type="application/json"):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("Set OPENAI_API_KEY in the process environment or local .env to run a cloud stage.")
    request = Request("https://api.openai.com/v1/" + endpoint, data=body,
                      headers={"Authorization": f"Bearer {key}", "Content-Type": content_type})
    try:
        with urlopen(request, timeout=600) as response:
            return json.load(response)
    except HTTPError as exc:
        # Provider bodies can contain input data. Do not print them or credentials.
        raise ValueError(f"OpenAI HTTP {exc.code}. Completed chunks are cached; rerun to resume. "
                         "Check account access, limits, and credentials.") from None
    except (URLError, TimeoutError) as exc:
        raise ValueError("Network request failed. Rerun to resume; a timed-out request may be billed.") from exc


def multipart(path):
    boundary = uuid.uuid4().hex
    parts = []
    fields = {"model": TRANSCRIBE_MODEL, "response_format": "diarized_json",
              "chunking_strategy": "auto"}
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="chunk.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode())
    parts.extend([path.read_bytes(), f"\r\n--{boundary}--\r\n".encode()])
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def normalize(raw, chunk):
    segments = raw.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError(f"No timed segments returned for {chunk['id']}; inspect the recording.")
    result = []
    for index, segment in enumerate(segments):
        start, end = float(segment["start"]), float(segment["end"])
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start <= end):
            raise ValueError("Invalid segment timestamps.")
        if not isinstance(segment.get("text"), str):
            raise ValueError("Invalid segment text.")
        result.append({"id": f"{chunk['id']}:s{index:04d}",
                       "start": start + chunk["offset_seconds"],
                       "end": end + chunk["offset_seconds"],
                       "speaker": f"{chunk['id']}:{segment.get('speaker', 'unknown')}",
                       "text": segment["text"]})
    return result


def transcribe(dest):
    manifest = read_json(dest / "manifest.json")
    all_segments = []
    for chunk in manifest["chunks"]:
        path = dest / chunk["path"]
        if digest(path) != chunk["sha256"]:
            raise ValueError("Audio chunk changed; prepare a new session rather than reuse stale output.")
        cache = dest / "transcripts" / "raw" / (chunk["id"] + ".json")
        identity = {"sha256": chunk["sha256"], "model": TRANSCRIBE_MODEL}
        if cache.exists():
            cached = read_json(cache)
            if cached["input"] != identity:
                raise ValueError("Transcription cache differs from input; use a new session ID.")
            raw = cached["response"]
        else:
            if not 0 < path.stat().st_size < MAX_AUDIO_BYTES:
                raise ValueError("Audio chunk is empty or over the upload limit.")
            print(f"Transcribing {chunk['id']}…", flush=True)
            body, content_type = multipart(path)
            raw = api("audio/transcriptions", body, content_type)
            normalize(raw, chunk)  # Do not cache malformed responses as successes.
            save_json(cache, {"input": identity, "response": raw})
        all_segments.extend(normalize(raw, chunk))
    all_segments.sort(key=lambda item: (item["start"], item["id"]))
    save_json(dest / "transcripts/transcript.json", {"schema_version": 1, "segments": all_segments})
    write(dest / "transcripts/transcript.md", render(all_segments))
    print("Transcript ready. Review uncertain words and speaker identities before sharing.")


def render(segments):
    return "\n".join(f"[{s['id']}] {s['start']:.2f}–{s['end']:.2f}s {s['speaker']}: {s['text']}"
                     for s in segments) + "\n"


def batches(text, limit=24000):
    """Bound all requests without silently truncating long sessions."""
    result, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(line) > limit:
            raise ValueError("A single transcript line exceeds the request budget; split it before retrying.")
        if len(current) + len(line) > limit:
            result.append(current)
            current = ""
        current += line
    if current.strip():
        result.append(current)
    return result


def generate(instructions, text, model, cache_dir):
    payload = {"model": model, "instructions": instructions, "input": text,
               "store": False, "max_output_tokens": 5000}
    encoded = json.dumps(payload, ensure_ascii=False).encode()
    key = hashlib.sha256(encoded).hexdigest()
    cache = cache_dir / (key + ".json")
    raw = read_json(cache) if cache.exists() else api("responses", encoded)
    if raw.get("status") != "completed":
        raise ValueError("Summary response did not complete; no final recap was written.")
    output = "\n".join(part["text"] for item in raw.get("output", [])
                       if item.get("type") == "message" for part in item.get("content", [])
                       if part.get("type") == "output_text")
    if not output.strip():
        raise ValueError("Summary response contained no text.")
    save_json(cache, raw)
    return output


def summarize(root, dest, model):
    transcript = read_json(dest / "transcripts/transcript.json")
    text = render(transcript["segments"])
    if not text.strip():
        raise ValueError("Cannot summarize an empty transcript.")
    prompt = (root / "prompts/recap.md").read_text(encoding="utf-8")
    # Explicit allowlist prevents accidental ingestion of DM-only notes.
    context = "\n".join((root / "context/campaign" / name).read_text(encoding="utf-8")
                        for name in ("overview.md", "characters.md", "glossary.md", "state.md"))
    metadata = (dest / "session.json").read_text(encoding="utf-8")
    if len(context) + len(metadata) > MAX_CONTEXT_CHARS:
        raise ValueError("Campaign context and session metadata exceed 24,000 characters; condense them.")
    instructions = prompt + "\nCampaign reference data (not session evidence):\n" + context + "\nSession metadata:\n" + metadata
    cache = dest / "summaries/cache"
    notes = batches(text)
    # Map all transcript batches, then recursively reduce bounded groups.
    for level in range(8):
        final = len(notes) == 1
        task = ("\nWrite the final recap using the required sections." if final else
                "\nExtract compact chronological evidence notes from this partial session. "
                "Preserve source IDs, outcomes, uncertainties, and all unresolved threads; "
                "do not write a final recap yet.")
        outputs = [generate(instructions + task, note, model, cache) for note in notes]
        if final:
            recap = outputs[0]
            known = {s["id"] for s in transcript["segments"]}
            cited = set(re.findall(r"\[(c\d+:s\d+)\]", recap))
            if not cited or not cited <= known:
                raise ValueError("Recap lacks valid source IDs or includes unknown IDs. Inspect cached output.")
            write(dest / "summaries/recap.draft.md", "<!-- UNREVIEWED: verify facts and audience before sharing. -->\n\n" + recap + "\n")
            save_json(dest / "summaries/provenance.json", {
                "model": model, "transcript_sha256": digest(dest / "transcripts/transcript.json"),
                "prompt_sha256": digest(root / "prompts/recap.md"),
                "context_sha256": hashlib.sha256((context + metadata).encode()).hexdigest(),
                "review_status": "unreviewed", "reduction_levels": level,
            })
            print("Created summaries/recap.draft.md. Review it before promoting campaign updates.")
            return
        notes = batches("\n".join(outputs))
    raise ValueError("Summary reduction did not converge; cached intermediate responses are retained.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--env-file", type=Path,
                        help="Configuration relative to root (cloud stages only; default: .env)")
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="Copy and chunk audio locally")
    prep.add_argument("session")
    prep.add_argument("audio", type=Path)
    for name in ("transcribe", "summarize"):
        command = commands.add_parser(name)
        command.add_argument("session")
        command.add_argument("--allow-cloud", action="store_true", help="Permit uploads and API charges")
        if name == "summarize":
            command.add_argument("--model", help="Recap model; overrides RECAP_MODEL")
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        dest = session_path(root, args.session)
        if args.command == "prepare":
            prepare(root, args.session, args.audio)
        else:
            if not args.allow_cloud:
                raise ValueError("This stage sends session data to OpenAI and may incur charges. "
                                 "Use --allow-cloud when ready.")
            load_environment(root / (args.env_file or Path(".env")))
            if args.command == "transcribe":
                transcribe(dest)
            else:
                summarize(root, dest, args.model or os.environ.get("RECAP_MODEL") or "gpt-4.1-mini")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        # Do not expose raw exception text: decoder errors can contain private input.
        message = str(exc) if type(exc) is ValueError else "Input or response is missing or malformed; check the stage files."
        parser.exit(1, f"Error: {message}\n")


if __name__ == "__main__":
    main()
