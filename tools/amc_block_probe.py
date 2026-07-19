"""
amc_block_probe.py

Captures successful and blocked AMC page responses for direct comparison.
Launches browsers in rapid succession to trigger Cloudflare/queue.it blocking.

For each run reports:
  - final URL (after all redirects)
  - page title
  - HTML size
  - first 500 characters of body text
  - seatingLayout presence

Saves first successful and first blocked HTML to disk for offline inspection.

Usage:
    py amc_block_probe.py URL [max_runs]

Example:
    py amc_block_probe.py "https://www.amctheatres.com/showtimes/143822631/seats" 7
"""

import sys
import time
import re

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


NETWORKIDLE_TIMEOUT = 15_000
NETWORKIDLE_FALLBACK = 12_000


def body_text(html: str) -> str:
    """Strip tags, collapse whitespace, return first 500 printable chars."""
    stripped = re.sub(r"<[^>]+>", " ", html)
    collapsed = re.sub(r"\s+", " ", stripped).strip()
    return collapsed[:500]


def single_fetch(url: str, run_num: int) -> dict:
    result = {
        "run": run_num,
        "error": None,
        "goto_duration": None,
        "networkidle_fired": False,
        "final_url": None,
        "title": None,
        "html_size": 0,
        "first_500_body": "",
        "first_500_raw": "",
        "seating_layout_present": False,
        "html": "",
    }
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            t0 = time.monotonic()
            page.goto(url, timeout=120_000)
            result["goto_duration"] = time.monotonic() - t0

            try:
                page.wait_for_load_state("networkidle", timeout=NETWORKIDLE_TIMEOUT)
                result["networkidle_fired"] = True
            except PlaywrightTimeoutError:
                page.wait_for_timeout(NETWORKIDLE_FALLBACK)

            html = page.content()
            result["final_url"] = page.url
            result["title"] = page.title()
            result["html_size"] = len(html)
            result["first_500_raw"] = html[:500]
            result["first_500_body"] = body_text(html)
            result["seating_layout_present"] = "seatingLayout" in html
            result["html"] = html
            browser.close()
    except Exception as exc:
        result["error"] = str(exc)
    return result


def classify(r: dict) -> str:
    if r["error"]:
        return "PLAYWRIGHT_ERROR"
    if r["seating_layout_present"]:
        return "SUCCESS"
    return "NO_SEATING_LAYOUT"


def save_html(html: str, path: str) -> None:
    with open(path, "w", encoding="utf-8", errors="replace") as f:
        f.write(html)
    print(f"  [saved] {path} ({len(html):,} chars)")


def main():
    if len(sys.argv) < 2:
        print("Usage: py amc_block_probe.py URL [max_runs]")
        sys.exit(1)

    url = sys.argv[1]
    max_runs = int(sys.argv[2]) if len(sys.argv) > 2 else 7

    print("=" * 72)
    print("AMC BLOCK PROBE")
    print(f"URL      : {url}")
    print(f"Max runs : {max_runs}")
    print("=" * 72)
    print()

    results = []
    saved_success = False
    saved_blocked = False

    for i in range(1, max_runs + 1):
        print(f"--- Run {i}/{max_runs} ---")
        r = single_fetch(url, i)
        results.append(r)
        cat = classify(r)

        if r["error"]:
            print(f"  PLAYWRIGHT_ERROR: {r['error'][:120]}")
            print()
            continue

        print(f"  goto_duration          : {r['goto_duration']:.2f}s")
        print(f"  networkidle_fired      : {r['networkidle_fired']}")
        print(f"  final_url              : {r['final_url']}")
        print(f"  page_title             : {r['title']!r}")
        print(f"  html_size              : {r['html_size']:,} chars")
        print(f"  seatingLayout_present  : {r['seating_layout_present']}")
        print(f"  classification         : {cat}")
        print()
        print(f"  First 500 chars (raw HTML):")
        print(f"    {r['first_500_raw']!r}")
        print()
        print(f"  First 500 chars (body text, tags stripped):")
        print(f"    {r['first_500_body']!r}")
        print()

        if cat == "SUCCESS" and not saved_success:
            save_html(r["html"], "amc_block_probe_success.html")
            saved_success = True

        if cat == "NO_SEATING_LAYOUT" and not saved_blocked:
            save_html(r["html"], "amc_block_probe_blocked.html")
            saved_blocked = True

        if saved_success and saved_blocked:
            print("  [both page types captured -- stopping early]")
            print()
            break

    # -----------------------------------------------------------------------
    # Comparison summary
    # -----------------------------------------------------------------------
    print("=" * 72)
    print("COMPARISON SUMMARY")
    print("=" * 72)

    successes = [r for r in results if classify(r) == "SUCCESS"]
    blocked = [r for r in results if classify(r) == "NO_SEATING_LAYOUT"]
    errors = [r for r in results if classify(r) == "PLAYWRIGHT_ERROR"]

    print(f"Runs completed : {len(results)}")
    print(f"  SUCCESS      : {len(successes)}")
    print(f"  BLOCKED      : {len(blocked)}")
    print(f"  PW_ERROR     : {len(errors)}")
    print()

    if successes:
        s = successes[0]
        print(f"First SUCCESS (run {s['run']}):")
        print(f"  goto_duration : {s['goto_duration']:.2f}s")
        print(f"  html_size     : {s['html_size']:,} chars  ({s['html_size']/1024:.1f} KB)")
        print(f"  final_url     : {s['final_url']}")
        print(f"  title         : {s['title']!r}")
        print()

    if blocked:
        b = blocked[0]
        print(f"First BLOCKED (run {b['run']}):")
        print(f"  goto_duration : {b['goto_duration']:.2f}s")
        print(f"  html_size     : {b['html_size']:,} chars  ({b['html_size']/1024:.1f} KB)")
        print(f"  final_url     : {b['final_url']}")
        print(f"  title         : {b['title']!r}")
        print()

    if successes and blocked:
        ratio = successes[0]["html_size"] / max(blocked[0]["html_size"], 1)
        print(f"Size ratio (success / blocked) : {ratio:.0f}x")
        print()

        # Threshold recommendation: halfway between blocked and success in log space
        import math
        low = blocked[0]["html_size"]
        high = successes[0]["html_size"]
        geometric_mid = int(math.sqrt(low * high))
        # Round down to nearest 50KB
        threshold = max(50_000, (geometric_mid // 50_000) * 50_000)
        print(f"Observed blocked size  : {low:,} chars")
        print(f"Observed success size  : {high:,} chars")
        print(f"Geometric midpoint     : {geometric_mid:,} chars")
        print(f"Recommended threshold  : {threshold:,} chars  ({threshold//1000}KB)")
        print()

    if not blocked:
        print("Block condition was NOT triggered within the run limit.")
        print("Increase max_runs or run again immediately after a previous probe.")
        print()


if __name__ == "__main__":
    main()
