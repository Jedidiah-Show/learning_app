#!/usr/bin/env python3
"""Generate lesson extras through the temporary production AI hook.

The public text endpoint allows one request every 30 seconds, which is too slow
for 201 lessons. The deployed app already has a working AI provider, so this
maintenance client sends the same prompts to the token-protected admin hook and
saves the validated results locally. The hook is removed after generation.

Usage:
    python scripts/generate_lesson_extras_remote.py --verify --workers 6
    python scripts/generate_lesson_extras_remote.py --lesson 2.01 --force
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_lesson_extras as base
from app.curriculum import all_lessons

DEFAULT_BASE = os.environ.get(
    "LESSON_EXTRAS_BASE", "https://learning-mwaihroip-ruach-team1.vercel.app"
)
TOKEN_FILE = Path("/tmp/opencode/extras_token")
COOKIE_FILE = Path("/tmp/opencode/cookies2.txt")
LOGIN_FILE = Path("/tmp/opencode/login2.html")
SAVE_LOCK = threading.Lock()
PRINT_LOCK = threading.Lock()


def log(message):
    with PRINT_LOCK:
        print(message, flush=True)


def read_token():
    token = os.environ.get("LESSON_EXTRAS_TOKEN")
    if token:
        return token.strip()
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    raise SystemExit("Set LESSON_EXTRAS_TOKEN or create /tmp/opencode/extras_token")


def read_csrf():
    if not LOGIN_FILE.exists():
        raise SystemExit(f"missing {LOGIN_FILE}; log in with vercel curl first")
    html = LOGIN_FILE.read_text()
    marker = 'name="csrf-token" content="'
    if marker not in html:
        raise SystemExit("could not find the CSRF token in the login page")
    return html.split(marker, 1)[1].split('"', 1)[0]


def post_prompt(base_url, prompt, token, csrf, timeout=90):
    """Send one prompt through the production hook. Returns the parsed result."""
    body = json.dumps({"prompt": prompt, "tier": "flash"}).encode("utf-8")
    with tempfile.NamedTemporaryFile(
        prefix="lesson-prompt-", suffix=".json", delete=False
    ) as handle:
        handle.write(body)
        body_path = handle.name
    output_path = body_path + ".out"
    command = [
        "vercel", "curl", f"{base_url}/api/admin/ai/json",
        "-s", "-X", "POST",
        "-b", str(COOKIE_FILE),
        "-H", "Content-Type: application/json",
        "-H", f"X-CSRF-Token: {csrf}",
        "-H", f"X-Admin-Token: {token}",
        "--data-binary", f"@{body_path}",
        "-o", output_path,
        "-w", "%{http_code}",
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        status = (completed.stdout or "").strip().splitlines()
        status = status[-1] if status else ""
        payload = {}
        if Path(output_path).exists():
            try:
                payload = json.loads(Path(output_path).read_text())
            except ValueError:
                payload = {}
        if status == "200" and isinstance(payload.get("result"), dict):
            return payload["result"]
        message = payload.get("error") or completed.stderr.strip()[-200:]
        raise RuntimeError(f"HTTP {status or '?'}: {message}")
    finally:
        for path in (body_path, output_path):
            try:
                os.unlink(path)
            except OSError:
                pass


def generate_lesson(lesson, args, token, csrf):
    draft = post_prompt(
        args.base, base.build_prompt(lesson), token, csrf
    )
    result = base.normalise(lesson, draft)
    if args.verify:
        corrected = post_prompt(
            args.base,
            base.build_critique_prompt(lesson, result),
            token,
            csrf,
        )
        result = base.normalise(lesson, corrected)
    return result


def with_retries(lesson, args, token, csrf, attempts=4):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return generate_lesson(lesson, args, token, csrf)
        except Exception as error:
            last_error = error
            wait = min(30, 3 * attempt)
            log(
                f"  {lesson['id']} attempt {attempt}/{attempts} failed "
                f"({error}); retrying in {wait}s"
            )
            time.sleep(wait)
    raise RuntimeError(f"{lesson['id']} failed: {last_error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--lesson", help="single lesson id")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    token, csrf = read_token(), read_csrf()
    lessons = all_lessons()
    if args.lesson:
        lessons = [item for item in lessons if item["id"] == args.lesson]
        if not lessons:
            raise SystemExit(f"unknown lesson id: {args.lesson}")

    existing = base.load_output()
    pending = [
        item for item in lessons
        if args.force or not base.is_complete(existing.get(item["id"]), item)
    ]
    if args.limit:
        pending = pending[: args.limit]
    total = len(pending)
    log(
        f"{total} lesson(s) to generate with {args.workers} worker(s); "
        f"{len(existing)} already present"
    )

    completed = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(with_retries, lesson, args, token, csrf): lesson
            for lesson in pending
        }
        for future in as_completed(futures):
            lesson = futures[future]
            completed += 1
            try:
                entry = future.result()
            except Exception as error:
                log(f"[{completed}/{total}] {lesson['id']} FAILED: {error}")
                continue
            with SAVE_LOCK:
                current = base.load_output()
                current[lesson["id"]] = entry
                base.save_output(current)
            log(
                f"[{completed}/{total}] {lesson['id']} {lesson['title']} "
                f"saved ({len(entry['answers'])} answers)"
            )

    log(f"done: {len(base.load_output())} lesson entries")


if __name__ == "__main__":
    main()
