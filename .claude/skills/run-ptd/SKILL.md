---
name: run-ptd
description: Build, run, screenshot, and drive the PTD dashboard (the static index.html data dashboard served on GitHub Pages). Use when asked to run/launch/preview the PTD site, screenshot the dashboard or one of its tabs, verify a layout/CSS change, or check that a chart renders.
---

The PTD "app" is a single static dashboard — `index.html` + the generated
`output/data.js`, with Chart.js pulled from a CDN. There is **no server and no
build step**: it loads straight off disk over a `file://` URL. Drive it with the
headless-Chromium screenshotter at `.claude/skills/run-ptd/driver.py` (Python +
Playwright). All paths below are relative to the repo root.

## Prerequisites

Python 3.11+ and Playwright's Chromium. This is all that was needed in a clean
container (Playwright's Chromium build ships its own libs; nothing from
`apt-get` was required here):

```bash
pip install playwright
python -m playwright install chromium
```

On a bare machine missing system libraries, add the OS deps (needs sudo):
`python -m playwright install-deps chromium`.

## Setup

None beyond the prerequisites. The dashboard reads `output/data.js`, which is
**committed** — so a fresh clone renders with real data immediately. (To
regenerate that data you run the scraper pipeline in `ptd_scraper.ipynb`; that
is out of scope for running the dashboard.)

## Build

No build step for the dashboard — it is static. (`make build` only rebuilds the
Jupyter notebook from `notebook_cells/`; it does not touch `index.html`.)

## Run (agent path)

Drive the dashboard with `driver.py`. It launches headless Chromium, optionally
opens a tab by clicking its real sidebar link (so that tab's charts initialise),
and writes a PNG per viewport width.

```bash
# Overview tab at three widths (1440 desktop, 1024 laptop, 390 mobile):
python .claude/skills/run-ptd/driver.py

# A specific tab at one width:
python .claude/skills/run-ptd/driver.py --section risks --width 1280

# Several widths, custom output dir:
python .claude/skills/run-ptd/driver.py --width 1440,390 --out /tmp/shots
```

Screenshots land at `/tmp/ptd-shots/ptd_<section>_<width>.png` (override with
`--out`). Exit code is `1` if the page threw an uncaught JS error (e.g. the
Chart.js CDN was blocked), `0` otherwise.

| flag | default | meaning |
|---|---|---|
| `--section` | `overview` | tab to open before the shot |
| `--width` | `1440,1024,390` | comma-separated viewport widths |
| `--out` | `/tmp/ptd-shots` | screenshot output directory |

Valid sections (the sidebar tabs): `overview`, `ptd-method`, `deliveries`,
`risks`, `organs`, `compare`, `insights`, `visualizations`, `review`,
`methodology`.

## Run (human path)

It's a static file — open `index.html` in any browser, or serve the repo and
visit it:

```bash
python -m http.server 8000   # then open http://localhost:8000/  (Ctrl-C to stop)
```

## Test

```bash
python -m pytest tests/       # 50 passed
```

## Gotchas

- **Charts need the Chart.js CDN, and the sandbox proxy's TLS cert is
  untrusted** — without a workaround Chromium fails the CDN request with
  `net::ERR_CERT_AUTHORITY_INVALID`, charts stay blank, and the page logs
  `Chart is not defined`. `driver.py` handles this with
  `ignore_https_errors=True`. If you drive Chromium yourself, pass
  `--ignore-certificate-errors` (Playwright: `new_context(ignore_https_errors=True)`).
- **Charts are built lazily per tab.** Just toggling a section's `.active` class
  leaves its `<canvas>` blank — you must trigger the page's own
  `showSection()`. `driver.py` does this by clicking the sidebar link
  (`a[onclick*="'<section>'"]`); the overview tab is the only one painted on load.
- **`output/data.js` defines top-level `const`s, not globals.** `PTD_STATS`,
  `PTD_DELIVERIES`, etc. are reachable by bare name but **not** as
  `window.PTD_STATS` — check `typeof PTD_STATS`, not `window.PTD_STATS`, or
  you'll think the data failed to load when it didn't.
- **No server required.** `file://` loading works; the relative `output/data.js`
  path resolves against the repo. A dev server is only needed if you want a real
  `http://` origin.
- **Responsive breakpoint is 768px.** At/below it the sidebar collapses to a
  60px icon rail and the content/banner/footer shift their left margin to match;
  shoot `--width 390` to check the mobile layout.
- **`networkidle` can stall on the CDN socket.** `driver.py` wraps `goto()` in a
  try/except plus a fixed paint wait so a slow/again-blocked CDN never hangs the
  run.

## Troubleshooting

- **`Chart is not defined` / blank charts**: the Chart.js CDN didn't load — TLS
  cert rejected (see Gotchas; ensure `ignore_https_errors`) or jsdelivr
  unreachable. The layout still renders; only charts are affected.
- **Page renders but KPIs are empty / `PTD_STATS is not defined`**:
  `output/data.js` is missing. It's committed; restore it (or run the pipeline).
  `driver.py` prints a `WARN` if the file is absent.
- **`playwright._impl._errors.Error: Executable doesn't exist`**: run
  `python -m playwright install chromium`.
