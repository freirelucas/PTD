#!/usr/bin/env python3
"""Headless driver for the PTD dashboard (static index.html + output/data.js).

The dashboard is a single static HTML file — no server needed; we load it
straight off disk via a file:// URL. Chart.js (pulled from a CDN) builds each
tab's charts lazily, so to screenshot a *non-default* tab we click its real
sidebar link, which fires the page's own showSection() and paints that tab.

Examples:
    python driver.py                               # overview @ 1440,1024,390
    python driver.py --section risks               # risks tab @ 1440,1024,390
    python driver.py --section organs --width 1280
    python driver.py --width 1440,390 --out /tmp/shots

Sections: overview ptd-method deliveries risks organs compare insights
          visualizations review methodology

Screenshots land at <out>/ptd_<section>_<width>.png  (default out=/tmp/ptd-shots).
Exit code is 1 if the page raised an uncaught JS error (e.g. Chart.js CDN
blocked, or output/data.js missing), else 0.
"""
import argparse
import pathlib
import sys

from playwright.sync_api import sync_playwright

# driver.py lives at <repo>/.claude/skills/run-ptd/driver.py → repo is parents[3]
REPO = pathlib.Path(__file__).resolve().parents[3]
INDEX = (REPO / "index.html").as_uri()


def main() -> None:
    ap = argparse.ArgumentParser(description="Screenshot/drive the PTD dashboard.")
    ap.add_argument("--section", default="overview", help="tab id to open before shooting")
    ap.add_argument("--width", default="1440,1024,390", help="comma-separated viewport widths")
    ap.add_argument("--out", default="/tmp/ptd-shots", help="output directory for PNGs")
    args = ap.parse_args()

    widths = [int(w) for w in args.width.split(",") if w.strip()]
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if not (REPO / "output" / "data.js").exists():
        print("WARN: output/data.js missing — dashboard will render empty "
              "(run the pipeline first).", file=sys.stderr)

    rc = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w in widths:
            # ignore_https_errors: some sandboxes route egress through a proxy
            # whose TLS cert Chromium won't trust (ERR_CERT_AUTHORITY_INVALID),
            # which would silently break the Chart.js CDN and web fonts.
            ctx = browser.new_context(viewport={"width": w, "height": 900},
                                      ignore_https_errors=True)
            page = ctx.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            try:
                page.goto(INDEX, wait_until="networkidle", timeout=15000)
            except Exception:
                pass  # networkidle can stall on the CDN socket; carry on
            if args.section != "overview":
                link = page.locator(f".sidebar nav a[onclick*=\"'{args.section}'\"]").first
                if link.count():
                    link.click()
                else:  # fall back to the global switcher if the link is gone
                    page.evaluate("(s) => window.showSection && window.showSection(s)", args.section)
            page.wait_for_timeout(1200)  # let Chart.js paint
            shot = out / f"ptd_{args.section}_{w}.png"
            page.screenshot(path=str(shot))
            line = f"{shot}  ({w}px)"
            if errors:
                line += "\n  WARN page JS error: " + " | ".join(errors)
                rc = 1
            print(line)
            ctx.close()
        browser.close()
    sys.exit(rc)


if __name__ == "__main__":
    main()
