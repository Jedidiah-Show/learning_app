# Running Piston for interactive Python practice

The app's interactive practice runs (lesson "Run checks" and the specialization
pathway workspaces) can execute learner code on a **self-hosted
[Piston](https://github.com/engineer-man/piston)** engine instead of only in the
sandboxed browser frame or the Docker judge. Piston is free, open source, and
runs Python inside an Isolate sandbox in a privileged Docker container.

> The public `emkc.org` API is **not** an option: it stopped serving anonymous
> traffic in February 2026, and learner code must never leave your
> infrastructure. Self-hosting is the only supported mode.

## 1. Where it can run

Piston needs a host with:

- Docker (the container runs with `--privileged`, which Piston requires),
- cgroup v2 (cgroup v1 must be disabled), and
- a private network path from the web app, or an authenticated reverse proxy in
  front of it. **Piston's API has no authentication.** Never publish port 2000
  to the internet; bind it to localhost or a private subnet and let the app
  reach it over that network.

Vercel and Render's free web service cannot host it (no privileged Docker).
Use a small dedicated VM, a container host with privileged mode allowed, or
your existing judge worker's infrastructure. If Piston lives on the same
machine as the judge worker, nothing in this repo changes except the new env
vars below.

## 2. Install (on the Piston host)

```bash
mkdir -p ~/piston-data
docker run --privileged -v "$PWD/piston-data:/piston" -dit \
  -p 127.0.0.1:2000:2000 \
  -e PISTON_RUN_MEMORY_LIMIT=268435456 \
  --name piston_api ghcr.io/engineer-man/piston
```

If you bind `0.0.0.0:2000` instead, firewall it to the app's IPs, or put an
authenticated proxy (nginx, Caddy, Cloudflare Access) in front with a shared
secret header — no application-level auth exists inside Piston.

No language runtimes are installed in the base image. Install Python with the
Piston CLI (needs Node ≥ 15 on the host):

```bash
git clone https://github.com/engineer-man/piston ~/piston
cd ~/piston/cli && npm install
node piston install python 3.12.0   # match what your exercises expect
```

Verify:

```bash
node piston runtimes                 # shows python 3.12.0 installed
curl -s -X POST http://127.0.0.1:2000/api/v2/execute \
  -H 'Content-Type: application/json' \
  -d '{"language":"python","version":"3.12.0","files":[{"name":"t.py","content":"print(6*7)"}]}'
# → {"language":"python","version":"3.12.0","run":{"stdout":"42\n",...}}
```

Isolation comes from Isolate (namespaces + chroot + per-run uid + cgroups).
Piston should still run on a host dedicated to code execution — treat it as
untrusted-code infrastructure, like the judge worker.

## 3. App configuration

Set these on the web service (Render dashboard / `render.yaml` / `.env`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `PISTON_URL` | *(unset = disabled)* | Base URL of Piston, e.g. `http://10.0.0.8:2000` |
| `PISTON_PYTHON_VERSION` | *(auto)* | Exact runtime version, e.g. `3.12.0`. Empty = auto-discovered from `/api/v2/runtimes` |
| `PISTON_RUN_TIMEOUT_MS` | `10000` | Per-run wall clock |
| `PISTON_RUN_MEMORY_LIMIT_MB` | `256` | Per-run memory ceiling |

When `PISTON_URL` is set, interactive runs (the practice workspace "Run
checks" button) go to Piston first. If Piston is unreachable or errors, the
endpoint returns 503 and the learner's browser transparently falls back to the
Pyodide runtime, so practice keeps working either way. When `PISTON_URL` is
unset, behavior is unchanged (Docker judge if `JUDGE_SUBMISSIONS_ENABLED=true`,
otherwise Pyodide fallback).

`JUDGE_SUBMISSIONS_ENABLED` still governs only the **authoritative Arena
submit path**; Piston is for the formative run path and needs no such gate —
but like the judge, deploy it before relying on it in production and verify
your own exercises pass through it after any runtime upgrade.

## 4. Scope notes

- The submission always ships as two files (`driver.py` + `submission.py`);
  the driver exec's the learner code with top-level-`await` support, so the
  async checks (`python-bounded-async-map`, `python-taskgroup-deadline`) behave
  exactly as they do in Pyodide and the Docker sandbox.
- Verdicts map onto the existing vocabulary: `COMPLETED`,
  `CHECKS_FAILED` (assertion), `RUNTIME_ERROR`, `TIME_LIMIT_EXCEEDED`,
  `MEMORY_LIMIT_EXCEEDED`.
- Piston reports no memory usage; `memory_kb` is `0` for Piston runs.
- Authoritative grading for the Practice Arena is unchanged — keep using
  the Docker judge for `ACCEPTED` verdicts.
- Network isolation: the base Piston image has network access inside its
  container but learner code cannot reach your app's database credentials
  unless you give the subnet route to them; keep Piston on an isolated
  subnet without routes to private data stores.

## 5. Updating the runtime

Reinstalling Python upgrades may change program output subtly (e.g. formatting
of `repr`s); re-run the exercise self-checks after any `node piston install
python` upgrade:

```bash
.venv/bin/python -m pytest tests/test_content_integrity.py tests/test_pathway_practice.py -q
```
