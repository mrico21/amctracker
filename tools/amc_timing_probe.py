"""
amc_timing_probe.py

Instruments the Playwright fetch sequence to determine when seatingLayout
becomes available relative to the load event and networkidle, and whether
seat data is complete or still streaming at each checkpoint.

Timestamps are recorded at:
  - goto() start
  - goto() complete  (browser load event)
  - first content sample (immediately after goto)
  - seatingLayout first appearance (if not already present at load)
  - intermediate polls (every 500 ms, up to 10 samples)
  - networkidle fired (or 15 s timeout)
  - final content sample

Seat extraction is attempted at every checkpoint and the results are compared.

No production files are read or modified.

Usage:
    py amc_timing_probe.py <LABEL> <AMC_SEAT_URL> [<LABEL2> <URL2> ...]

Example:
    py amc_timing_probe.py ^
        "Odyssey" "https://www.amctheatres.com/showtimes/143822631/seats" ^
        "Scary Movie" "https://www.amctheatres.com/showtimes/144254871/seats"
"""

import re
import sys
import time
import json

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# ---------------------------------------------------------------------------
# Extraction helpers -- verbatim copies from tracker_multiwatch.py
# ---------------------------------------------------------------------------

RESERVABLE_TYPES = {"CanReserve", "LoveSeatLeft", "LoveSeatRight"}


def extract_seating_layout(html: str) -> dict:
    for marker in ('"seatingLayout"', '\\"seatingLayout\\"', "seatingLayout"):
        idx = html.find(marker)
        if idx != -1:
            break
    else:
        raise ValueError("seatingLayout not found in page source")
    colon_pos = html.find(":", idx + len(marker))
    start = html.find("{", colon_pos)
    if start == -1:
        raise ValueError("Could not locate seatingLayout object body")
    depth, end = 0, start
    for i in range(start, len(html)):
        if html[i] == "{":
            depth += 1
        elif html[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    else:
        raise ValueError("seatingLayout brace never closed")
    json_str = html[start : end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(json_str.replace('\\"', '"'))
    except json.JSONDecodeError as exc:
        raise ValueError(f"seatingLayout found but could not be parsed: {exc}") from exc


def collect_seats(data) -> list:
    seats = []
    if isinstance(data, dict):
        if {"available", "type", "name"}.issubset(data.keys()):
            seats.append(data)
        else:
            for v in data.values():
                seats.extend(collect_seats(v))
    elif isinstance(data, list):
        for item in data:
            seats.extend(collect_seats(item))
    return seats


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _seat_sort_key(name: str):
    m = re.match(r"^([A-Za-z]+)(\d+)$", name)
    return (m.group(1).upper(), int(m.group(2))) if m else (name, 0)


def try_extract(html: str) -> dict:
    """
    Attempt full seatingLayout extraction from html.
    Returns a stats dict; never raises.
    """
    if "seatingLayout" not in html:
        return {"present": False, "total_seats": 0, "available": 0, "seat_types": [], "error": None}

    result = {"present": True, "total_seats": 0, "available": 0, "seat_types": [], "error": None}
    try:
        layout = extract_seating_layout(html)
        seats = collect_seats(layout)
        seat_map = {s["name"]: s for s in seats if s.get("name")}
        available = [
            s for s in seat_map.values()
            if s.get("available") is True and s.get("type") in RESERVABLE_TYPES
        ]
        seat_types = sorted({s.get("type", "") for s in seat_map.values() if s.get("type")})
        result["total_seats"] = len(seat_map)
        result["available"] = len(available)
        result["seat_types"] = seat_types
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _rel(t: float, t0: float) -> str:
    """Format elapsed time relative to t0."""
    return f"+{t - t0:.3f}s"


def _stats_line(stats: dict) -> str:
    if not stats["present"]:
        return "seatingLayout not in HTML"
    if stats["error"]:
        return f"parse error: {stats['error']}"
    types = ", ".join(stats["seat_types"]) if stats["seat_types"] else "(none)"
    return (
        f"total={stats['total_seats']}  "
        f"available={stats['available']}  "
        f"types=[{types}]"
    )


def _stats_match(a: dict, b: dict) -> bool:
    return (
        a["present"] == b["present"]
        and a["total_seats"] == b["total_seats"]
        and a["available"] == b["available"]
        and a["seat_types"] == b["seat_types"]
    )


# ---------------------------------------------------------------------------
# Core timing probe
# ---------------------------------------------------------------------------

POLL_INTERVAL_MS = 500
MAX_POLLS = 20        # 10 seconds of polling maximum
STABLE_REQUIRED = 3   # consecutive polls with same counts before declaring stable


def run_timing_probe(url: str, label: str) -> dict:
    """
    Run the full instrumented fetch and return a result dict.
    """
    W = "=" * 72
    print(f"\n{W}")
    print(f"TIMING PROBE: {label}")
    print(f"URL: {url}")
    print(W)

    result = {
        "label": label,
        "url": url,
        "checkpoints": [],
        "networkidle_fired": False,
        "networkidle_timeout": False,
        "total_duration": 0.0,
        "seatinglayout_first_t": None,
        "seatinglayout_stable_t": None,
        "networkidle_t": None,
        "final_t": None,
        "stats_at_first": None,
        "stats_at_networkidle": None,
        "data_changed_after_first": False,
    }

    def checkpoint(name: str, t: float, t0: float, stats: dict = None, note: str = ""):
        entry = {"name": name, "elapsed": t - t0, "stats": stats, "note": note}
        result["checkpoints"].append(entry)
        stats_str = f"  {_stats_line(stats)}" if stats else ""
        note_str = f"  [{note}]" if note else ""
        print(f"  {_rel(t, t0):>10}  {name}{stats_str}{note_str}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        t0 = time.monotonic()
        print(f"\n  {'Elapsed':>10}  Event")
        print(f"  {'-'*10}  {'-'*60}")

        # ------------------------------------------------------------------
        # Phase 1: goto() — waits for the browser "load" event
        # ------------------------------------------------------------------
        checkpoint("goto() start", t0, t0)
        page.goto(url, timeout=120_000)
        t_load = time.monotonic()
        checkpoint("goto() complete (load event)", t_load, t0)

        # Immediately sample page.content() at load event
        html_at_load = page.content()
        t_content_load = time.monotonic()
        stats_at_load = try_extract(html_at_load)
        checkpoint("page.content() at load event", t_content_load, t0, stats_at_load)

        # ------------------------------------------------------------------
        # Phase 2: wait for seatingLayout to appear if not already present
        # ------------------------------------------------------------------
        if stats_at_load["present"]:
            t_first = t_content_load
            html_first = html_at_load
            stats_first = stats_at_load
            checkpoint("seatingLayout present at load event", t_first, t0,
                       note="already in DOM at load; no additional wait needed")
        else:
            checkpoint("seatingLayout absent at load event — waiting...", time.monotonic(), t0)
            try:
                page.wait_for_function(
                    "() => document.documentElement.outerHTML.includes('seatingLayout')",
                    timeout=30_000,
                )
                t_first = time.monotonic()
                html_first = page.content()
                stats_first = try_extract(html_first)
                checkpoint("seatingLayout first appearance", t_first, t0, stats_first)
            except PlaywrightTimeoutError:
                t_first = time.monotonic()
                checkpoint("seatingLayout first appearance TIMEOUT (30s)", t_first, t0,
                           note="FATAL: seatingLayout never appeared")
                browser.close()
                result["total_duration"] = time.monotonic() - t0
                return result

        result["seatinglayout_first_t"] = t_first - t0
        result["stats_at_first"] = stats_first

        # ------------------------------------------------------------------
        # Phase 3: poll every 500 ms until seat count is stable
        # ------------------------------------------------------------------
        print(f"\n  --- Polling every {POLL_INTERVAL_MS}ms for stability ---")
        prev_stats = stats_first
        stable_streak = 0
        t_stable = None
        stats_stable = stats_first

        for poll_num in range(1, MAX_POLLS + 1):
            page.wait_for_timeout(POLL_INTERVAL_MS)
            t_poll = time.monotonic()
            html_poll = page.content()
            stats_poll = try_extract(html_poll)

            if _stats_match(stats_poll, prev_stats):
                stable_streak += 1
                note = f"stable {stable_streak}/{STABLE_REQUIRED}"
            else:
                stable_streak = 0
                note = "CHANGED"

            checkpoint(f"poll {poll_num:02d}", t_poll, t0, stats_poll, note)

            if stable_streak >= STABLE_REQUIRED and t_stable is None:
                t_stable = t_poll
                stats_stable = stats_poll
                checkpoint(f"data declared STABLE (after {STABLE_REQUIRED} unchanged polls)",
                           t_poll, t0)
                break

            prev_stats = stats_poll

        if t_stable is None:
            t_stable = time.monotonic()
            stats_stable = prev_stats
            checkpoint("polling ended (max polls reached, stability not confirmed)", t_stable, t0)

        result["seatinglayout_stable_t"] = t_stable - t0

        # ------------------------------------------------------------------
        # Phase 4: wait for networkidle (mirrors production exactly)
        # ------------------------------------------------------------------
        print(f"\n  --- Waiting for networkidle ---")
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
            t_idle = time.monotonic()
            result["networkidle_fired"] = True
            checkpoint("networkidle fired", t_idle, t0)
        except PlaywrightTimeoutError:
            t_idle = time.monotonic()
            result["networkidle_timeout"] = True
            checkpoint("networkidle TIMEOUT (15s) — fallback wait starting", t_idle, t0)
            page.wait_for_timeout(12_000)
            t_idle = time.monotonic()
            checkpoint("fallback 12s wait complete", t_idle, t0)

        result["networkidle_t"] = t_idle - t0

        # Final content capture — exactly as production does it
        html_final = page.content()
        t_final = time.monotonic()
        stats_final = try_extract(html_final)
        checkpoint("page.content() final (production capture point)", t_final, t0, stats_final)

        result["final_t"] = t_final - t0
        result["stats_at_networkidle"] = stats_final
        result["data_changed_after_first"] = not _stats_match(stats_first, stats_final)

        browser.close()

    result["total_duration"] = time.monotonic() - t0
    return result


# ---------------------------------------------------------------------------
# Per-probe analysis report
# ---------------------------------------------------------------------------

def report_probe(r: dict) -> None:
    W = "=" * 72
    label = r["label"]
    t_first = r["seatinglayout_first_t"]
    t_stable = r["seatinglayout_stable_t"]
    t_idle = r["networkidle_t"]
    t_final = r["final_t"]
    s_first = r["stats_at_first"]
    s_final = r["stats_at_networkidle"]

    print(f"\n{W}")
    print(f"ANALYSIS: {label}")
    print(W)

    if t_first is None:
        print("  seatingLayout never appeared. No analysis possible.")
        return

    gap_stable_to_idle = (t_idle - t_stable) if (t_idle and t_stable) else None
    gap_first_to_idle  = (t_idle - t_first) if (t_idle and t_first) else None

    print(f"\n  Timing summary")
    print(f"  {'Event':<50} {'Elapsed':>10}")
    print(f"  {'-'*50} {'-'*10}")
    print(f"  {'goto() start':<50} {'t=0':>10}")
    print(f"  {'goto() complete (load event)':<50} {'+{:.3f}s'.format(r['checkpoints'][1]['elapsed']):>10}")
    print(f"  {'seatingLayout first available':<50} {'+{:.3f}s'.format(t_first):>10}")
    print(f"  {'seatingLayout stable':<50} {'+{:.3f}s'.format(t_stable):>10}")
    if r["networkidle_fired"]:
        print(f"  {'networkidle fired':<50} {'+{:.3f}s'.format(t_idle):>10}")
    else:
        print(f"  {'networkidle TIMEOUT (fell back to 12s wait)':<50} {'+{:.3f}s'.format(t_idle):>10}")
    print(f"  {'final page.content() (production capture)':<50} {'+{:.3f}s'.format(t_final):>10}")
    print(f"  {'total probe duration':<50} {'+{:.3f}s'.format(r['total_duration']):>10}")

    print(f"\n  Key gaps")
    if gap_first_to_idle is not None:
        print(f"  seatingLayout first available -> networkidle : {gap_first_to_idle:+.3f}s")
    if gap_stable_to_idle is not None:
        print(f"  seatingLayout stable          -> networkidle : {gap_stable_to_idle:+.3f}s")

    print(f"\n  Seat data at first availability")
    if s_first:
        print(f"    Total seats      : {s_first['total_seats']}")
        print(f"    Available seats  : {s_first['available']}")
        print(f"    Seat types       : {', '.join(s_first['seat_types']) if s_first['seat_types'] else '(none)'}")
        if s_first.get("error"):
            print(f"    Parse error      : {s_first['error']}")

    print(f"\n  Seat data after networkidle (production capture point)")
    if s_final:
        print(f"    Total seats      : {s_final['total_seats']}")
        print(f"    Available seats  : {s_final['available']}")
        print(f"    Seat types       : {', '.join(s_final['seat_types']) if s_final['seat_types'] else '(none)'}")
        if s_final.get("error"):
            print(f"    Parse error      : {s_final['error']}")

    print(f"\n  Data stability")
    if r["data_changed_after_first"]:
        delta_total = s_final["total_seats"] - s_first["total_seats"] if s_first and s_final else "?"
        delta_avail = s_final["available"] - s_first["available"] if s_first and s_final else "?"
        print(f"    CHANGED between first availability and networkidle.")
        print(f"    Total seat delta     : {delta_total:+d}")
        print(f"    Available seat delta : {delta_avail:+d}")
        print(f"    networkidle wait IS contributing to data completeness.")
    else:
        print(f"    UNCHANGED between first availability and networkidle.")
        print(f"    Seat counts and types were stable before networkidle fired.")
        if gap_first_to_idle is not None and gap_first_to_idle > 0.5:
            print(f"    networkidle added {gap_first_to_idle:.2f}s of unnecessary delay.")


# ---------------------------------------------------------------------------
# Cross-probe comparison and architectural recommendation
# ---------------------------------------------------------------------------

def report_recommendation(results: list[dict]) -> None:
    W = "=" * 72
    print(f"\n{W}")
    print("ARCHITECTURAL RECOMMENDATION")
    print(W)

    valid = [r for r in results if r["seatinglayout_first_t"] is not None]
    if not valid:
        print("\n  No valid results to analyze.")
        return

    all_unchanged = all(not r["data_changed_after_first"] for r in valid)
    any_changed   = any(r["data_changed_after_first"] for r in valid)

    gaps = [
        (r["networkidle_t"] or 0) - (r["seatinglayout_stable_t"] or 0)
        for r in valid
        if r["networkidle_t"] and r["seatinglayout_stable_t"]
    ]
    avg_gap = sum(gaps) / len(gaps) if gaps else 0
    max_gap = max(gaps) if gaps else 0
    min_gap = min(gaps) if gaps else 0

    print(f"\n  Results across {len(valid)} probe(s):")
    for r in valid:
        changed = "CHANGED" if r["data_changed_after_first"] else "stable"
        first_t = r["seatinglayout_first_t"]
        idle_t  = r["networkidle_t"]
        gap     = (idle_t - (r["seatinglayout_stable_t"] or first_t)) if idle_t else None
        gap_str = f"{gap:.2f}s wasted" if gap is not None else "?"
        print(f"    {r['label']:<30}  data={changed}  gap after stable={gap_str}")

    print()

    if all_unchanged:
        if avg_gap >= 2.0:
            print("  RECOMMENDATION: Replace networkidle with earlier readiness check")
            print()
            print("  Seat data was stable and complete before networkidle fired in all")
            print("  tested showtimes. The networkidle wait is serving only as a proxy")
            print("  for 'HTML is fully received' — but since the seat data is already")
            print("  stable at that point, networkidle is adding dead time waiting for")
            print(f"  analytics and third-party traffic to settle ({avg_gap:.2f}s average,")
            print(f"  {max_gap:.2f}s maximum across these probes).")
            print()
            print("  Candidate replacement strategies (for future implementation):")
            print()
            print("  Option A — wait_for_function with stable seat count")
            print("    Poll page.content() via JavaScript every ~250ms.")
            print("    Declare ready when two consecutive samples return the same")
            print("    non-zero seat count. This exits as soon as the RSC stream")
            print("    stabilises, ignoring analytics traffic entirely.")
            print()
            print("  Option B — DOM-level seatingLayout detection")
            print("    Use page.wait_for_function() with a JS predicate that checks")
            print("    for seatingLayout in outerHTML, then immediately read content.")
            print("    Faster than networkidle if the payload arrives before analytics")
            print("    traffic settles, but has no stability check (could race the")
            print("    end of the HTML stream on a slow connection).")
            print()
            print("  Option C — response event on main document")
            print("    Use Playwright's page.on('response') to intercept the main HTML")
            print("    response, read it directly, and skip page.content() entirely.")
            print("    Fastest possible, but requires re-verifying the queue.it and")
            print("    Turnstile flow are complete before the response body is usable.")
            print()
            print("  Lowest-risk option: Option A (poll with stability check).")
            print("  It mirrors the semantics of networkidle (waiting for the page to")
            print("  'stop changing') without waiting for unrelated third-party traffic.")

        elif avg_gap >= 0.5:
            print("  RECOMMENDATION: Replace networkidle with earlier readiness check")
            print()
            print("  Seat data was stable before networkidle across all probes.")
            print(f"  Average unnecessary delay: {avg_gap:.2f}s (max {max_gap:.2f}s).")
            print("  The saving is modest but real, especially if multiple URLs are")
            print("  fetched per run or if the tracker runs on Pi hardware.")

        else:
            print("  RECOMMENDATION: Keep networkidle")
            print()
            print("  Seat data was stable before networkidle, but the gap is very small")
            print(f"  ({avg_gap:.2f}s average). The overhead of implementing and maintaining")
            print("  an alternative readiness check is not justified by the marginal saving.")

    elif any_changed:
        print("  RECOMMENDATION: Keep networkidle")
        print()
        print("  Seat data was NOT stable before networkidle in at least one probe.")
        print("  This means the RSC payload is still streaming during the networkidle")
        print("  window, and networkidle is correctly serving as the completion signal.")
        print("  Replacing it with an earlier check risks capturing a partial seat map")
        print("  — exactly the regression that the networkidle fix in v1.0.3 resolved.")
        print()
        print("  If both probes show different behavior (one stable, one not), the")
        print("  variance is likely load-dependent. Keep networkidle for reliability.")

    else:
        print("  RECOMMENDATION: More investigation required")
        print()
        print("  Results were inconclusive. Re-run on different days or times to")
        print("  collect a larger sample before drawing conclusions.")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2 or len(args) % 2 != 0:
        print("Usage: py amc_timing_probe.py LABEL URL [LABEL2 URL2 ...]")
        print()
        print("Example:")
        print('  py amc_timing_probe.py ^')
        print('      "Odyssey" "https://www.amctheatres.com/showtimes/143822631/seats" ^')
        print('      "Scary Movie" "https://www.amctheatres.com/showtimes/144254871/seats"')
        sys.exit(1)

    pairs = [(args[i], args[i + 1]) for i in range(0, len(args), 2)]

    print("AMC Timing Probe")
    print(f"Probing {len(pairs)} URL(s) — allow ~60s per URL")

    results = []
    for label, url in pairs:
        r = run_timing_probe(url, label)
        report_probe(r)
        results.append(r)

    report_recommendation(results)


if __name__ == "__main__":
    main()
