"""
amc_stress_probe.py

Stress-tests the AMC fetch pipeline to determine whether extracting
seatingLayout immediately after the goto() load event is reliable, or
whether the historical partial-seat-map failure mode can still occur.

For each URL, performs N independent Playwright fetches.  Each fetch:
  1. Calls page.goto() and waits for the browser load event.
  2. Immediately calls page.content() and attempts seat extraction.
  3. Waits for networkidle (mirrors production behaviour exactly).
  4. Calls page.content() again and attempts seat extraction.

Results are compared across all N runs and classified.

No production files are read or modified.

Usage:
    py amc_stress_probe.py [--runs N] LABEL URL [LABEL2 URL2 ...]

Example:
    py amc_stress_probe.py --runs 25 ^
        "Odyssey" "https://www.amctheatres.com/showtimes/143822631/seats" ^
        "Scary Movie" "https://www.amctheatres.com/showtimes/144254871/seats"

Default: 25 runs per URL.
"""

import json
import re
import sys
import time

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
# Stats extraction
# ---------------------------------------------------------------------------

def try_extract(html: str) -> dict:
    """
    Attempt full seatingLayout extraction.
    Returns a stats dict; never raises.
    Keys: present, total_seats, available, seat_types, error
    """
    if "seatingLayout" not in html:
        return {
            "present": False,
            "total_seats": 0,
            "available": 0,
            "seat_types": [],
            "error": None,
        }
    result = {
        "present": True,
        "total_seats": 0,
        "available": 0,
        "seat_types": [],
        "error": None,
    }
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


def stats_equal(a: dict, b: dict) -> bool:
    return (
        a["present"] == b["present"]
        and a["total_seats"] == b["total_seats"]
        and a["available"] == b["available"]
        and a["seat_types"] == b["seat_types"]
    )


def stats_str(s: dict) -> str:
    if not s["present"]:
        return "seatingLayout absent"
    if s["error"]:
        return f"parse-error"
    types = ",".join(s["seat_types"]) if s["seat_types"] else "(none)"
    return f"seats={s['total_seats']} avail={s['available']} types=[{types}]"


# ---------------------------------------------------------------------------
# Single fetch
# ---------------------------------------------------------------------------

def single_fetch(url: str) -> dict:
    """
    One complete Playwright fetch.  Returns a result dict with load-event
    and networkidle stats.  Never raises -- errors are captured in the dict.
    """
    result = {
        "success": False,
        "error": None,
        "goto_duration": None,
        "networkidle_fired": False,
        "networkidle_fallback": False,
        "load": None,
        "idle": None,
        "html_size_load": 0,
        "html_size_idle": 0,
    }
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            t0 = time.monotonic()
            page.goto(url, timeout=120_000)
            result["goto_duration"] = time.monotonic() - t0

            # Checkpoint 1: immediately after load event
            html_load = page.content()
            result["html_size_load"] = len(html_load)
            result["load"] = try_extract(html_load)

            # Checkpoint 2: after networkidle -- mirrors production exactly
            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
                result["networkidle_fired"] = True
            except PlaywrightTimeoutError:
                page.wait_for_timeout(12_000)
                result["networkidle_fallback"] = True

            html_idle = page.content()
            result["html_size_idle"] = len(html_idle)
            result["idle"] = try_extract(html_idle)

            result["success"] = True
            browser.close()

    except Exception as exc:
        result["error"] = str(exc)

    return result


# ---------------------------------------------------------------------------
# Per-URL stress run
# ---------------------------------------------------------------------------

def run_stress(label: str, url: str, n_runs: int) -> dict:
    W = "=" * 76
    print(f"\n{W}")
    print(f"STRESS PROBE: {label}  ({n_runs} runs)")
    print(f"URL: {url}")
    print(W)
    print(f"  WARNING: {n_runs} browser launches -- estimated {n_runs * 10 // 60}m {n_runs * 10 % 60}s")
    print()
    print(f"  {'Run':>6}  {'goto':>6}  {'Load event result':<42}  {'Idle result':<42}  Match")
    print(f"  {'-'*6}  {'-'*6}  {'-'*42}  {'-'*42}  -----")

    runs = []
    failed_runs = []

    for i in range(1, n_runs + 1):
        r = single_fetch(url)

        if not r["success"]:
            print(f"  {i:>3}/{n_runs:<3}  [FETCH FAILED: {r['error'][:60]}]")
            failed_runs.append(i)
            runs.append(r)
            continue

        goto_str = f"{r['goto_duration']:.1f}s"
        load_str = stats_str(r["load"])
        idle_str = stats_str(r["idle"])
        match = stats_equal(r["load"], r["idle"])
        match_str = "OK " if match else "DIFF"

        print(f"  {i:>3}/{n_runs:<3}  {goto_str:>6}  {load_str:<42}  {idle_str:<42}  {match_str}")
        runs.append(r)

    return {
        "label": label,
        "url": url,
        "n_runs": n_runs,
        "runs": runs,
        "failed_runs": failed_runs,
    }


# ---------------------------------------------------------------------------
# Analysis and reporting
# ---------------------------------------------------------------------------

def analyse(probe: dict) -> dict:
    """Compute summary statistics across all successful runs."""
    runs = [r for r in probe["runs"] if r["success"]]
    n = len(runs)

    if n == 0:
        return {"n_successful": 0}

    # --- Seat counts at load event ---
    load_totals    = [r["load"]["total_seats"] for r in runs]
    load_availables = [r["load"]["available"]   for r in runs]

    # --- Seat counts at networkidle ---
    idle_totals    = [r["idle"]["total_seats"] for r in runs]
    idle_availables = [r["idle"]["available"]   for r in runs]

    # --- Change detection ---
    seats_changed  = sum(1 for r in runs if r["load"]["total_seats"] != r["idle"]["total_seats"])
    avail_changed  = sum(1 for r in runs if r["load"]["available"]   != r["idle"]["available"])
    types_changed  = sum(1 for r in runs if r["load"]["seat_types"]  != r["idle"]["seat_types"])
    any_changed    = sum(1 for r in runs if not stats_equal(r["load"], r["idle"]))

    # --- Runs with absent seatingLayout at load event ---
    absent_at_load = sum(1 for r in runs if not r["load"]["present"])
    parse_errors   = sum(1 for r in runs if r["load"]["error"])

    return {
        "n_successful": n,
        "n_failed": len(probe["failed_runs"]),

        # Load-event seat counts
        "load_seats_min": min(load_totals),
        "load_seats_max": max(load_totals),
        "load_avail_min": min(load_availables),
        "load_avail_max": max(load_availables),

        # Networkidle seat counts
        "idle_seats_min": min(idle_totals),
        "idle_seats_max": max(idle_totals),
        "idle_avail_min": min(idle_availables),
        "idle_avail_max": max(idle_availables),

        # Change rates
        "seats_changed":  seats_changed,
        "avail_changed":  avail_changed,
        "types_changed":  types_changed,
        "any_changed":    any_changed,

        # Edge cases
        "absent_at_load": absent_at_load,
        "parse_errors":   parse_errors,

        # goto() durations
        "goto_min": min(r["goto_duration"] for r in runs),
        "goto_max": max(r["goto_duration"] for r in runs),
        "goto_avg": sum(r["goto_duration"] for r in runs) / n,
    }


def report_analysis(probe: dict, stats: dict) -> None:
    W = "=" * 76
    label = probe["label"]
    n = stats["n_successful"]
    total = probe["n_runs"]

    print(f"\n{W}")
    print(f"ANALYSIS: {label}")
    print(W)

    if n == 0:
        print("  No successful runs to analyse.")
        return

    print(f"\n  Runs: {n} successful / {total} attempted"
          + (f"  ({stats['n_failed']} failed)" if stats["n_failed"] else ""))

    print(f"\n  goto() duration")
    print(f"    min={stats['goto_min']:.2f}s  max={stats['goto_max']:.2f}s  avg={stats['goto_avg']:.2f}s")

    print(f"\n  Seat counts -- at load event (immediately after goto())")
    print(f"    Total seats  : min={stats['load_seats_min']}  max={stats['load_seats_max']}")
    print(f"    Avail seats  : min={stats['load_avail_min']}  max={stats['load_avail_max']}")

    print(f"\n  Seat counts -- after networkidle (production capture point)")
    print(f"    Total seats  : min={stats['idle_seats_min']}  max={stats['idle_seats_max']}")
    print(f"    Avail seats  : min={stats['idle_avail_min']}  max={stats['idle_avail_max']}")

    print(f"\n  Change detection across {n} runs")
    print(f"    Seat count changed  (load -> idle) : {stats['seats_changed']:>3} / {n}")
    print(f"    Avail count changed (load -> idle) : {stats['avail_changed']:>3} / {n}")
    print(f"    Seat types changed  (load -> idle) : {stats['types_changed']:>3} / {n}")
    print(f"    Any field changed   (load -> idle) : {stats['any_changed']:>3} / {n}")

    if stats["absent_at_load"] > 0:
        print(f"\n    [!] seatingLayout absent at load event : {stats['absent_at_load']} / {n}")
    if stats["parse_errors"] > 0:
        print(f"\n    [!] Parse errors at load event        : {stats['parse_errors']} / {n}")

    # Print exact before/after for every differing run
    differing_runs = [
        (i + 1, r)
        for i, r in enumerate(probe["runs"])
        if r["success"] and not stats_equal(r["load"], r["idle"])
    ]
    if differing_runs:
        print(f"\n  Differing runs (load event vs networkidle):")
        for run_num, r in differing_runs:
            print(f"\n    Run {run_num:>2}:")
            print(f"      Load event : {stats_str(r['load'])}")
            print(f"      Networkidle: {stats_str(r['idle'])}")
            # Identify what changed
            if r["load"]["total_seats"] != r["idle"]["total_seats"]:
                delta = r["idle"]["total_seats"] - r["load"]["total_seats"]
                print(f"      Seat delta : {delta:+d} seats")
            if r["load"]["available"] != r["idle"]["available"]:
                delta = r["idle"]["available"] - r["load"]["available"]
                print(f"      Avail delta: {delta:+d} available")
            if r["load"]["seat_types"] != r["idle"]["seat_types"]:
                print(f"      Types changed from {r['load']['seat_types']} to {r['idle']['seat_types']}")
            if not r["load"]["present"]:
                print(f"      [!] seatingLayout was ABSENT at load event")
            if r["load"]["error"]:
                print(f"      [!] Parse error at load: {r['load']['error']}")
    else:
        print(f"\n  No differing runs. Load event and networkidle produced identical results")
        print(f"  in all {n} runs.")


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify(all_probes: list[dict], all_stats: list[dict]) -> None:
    W = "=" * 76
    print(f"\n{W}")
    print("CLASSIFICATION")
    print(W)

    total_successful = sum(s["n_successful"] for s in all_stats)
    total_any_changed = sum(s["any_changed"] for s in all_stats)
    total_absent = sum(s["absent_at_load"] for s in all_stats)

    if total_successful == 0:
        print("\n  No successful runs across any probe. Cannot classify.")
        return

    # Per-probe summary
    print(f"\n  Per-URL summary:")
    for probe, stats in zip(all_probes, all_stats):
        n = stats["n_successful"]
        changed = stats["any_changed"]
        absent = stats["absent_at_load"]
        seats_stable = stats["load_seats_min"] == stats["load_seats_max"] == stats["idle_seats_max"]
        avail_stable = stats["load_avail_min"] == stats["load_avail_max"] == stats["idle_avail_max"]
        consistency = "consistent" if seats_stable and avail_stable else "VARIABLE"
        print(f"    {probe['label']:<30}  changed={changed}/{n}  absent={absent}/{n}  counts={consistency}")

    print()

    # Evidence classification
    any_ever_absent  = total_absent > 0
    any_ever_changed = total_any_changed > 0
    change_rate      = total_any_changed / total_successful if total_successful else 0

    # Seat count variance at the load event itself (across runs, independent of idle comparison)
    any_load_variance = any(
        s["load_seats_min"] != s["load_seats_max"]
        for s in all_stats if s["n_successful"] > 0
    )
    any_avail_variance = any(
        s["load_avail_min"] != s["load_avail_max"]
        for s in all_stats if s["n_successful"] > 0
    )

    if not any_ever_changed and not any_ever_absent and not any_load_variance:
        print("  CLASSIFICATION: Load event always complete")
        print()
        print(f"  Across all {total_successful} successful run(s), every load-event capture")
        print(f"  produced seat counts and types identical to the subsequent networkidle")
        print(f"  capture. No run showed a partial or absent seat map at the load event.")
        print()
        print("  This is strong evidence that goto() reliably delivers a complete")
        print("  seatingLayout before the load event fires, at least under current")
        print("  network and server conditions.")
        print()
        print("  Implication for networkidle:")
        print("    The networkidle wait is not contributing to data completeness in")
        print("    any observed run. It is adding 1.7-2.4 seconds of delay (from the")
        print("    timing probe) while waiting for analytics traffic to settle.")
        print()
        print("  Caveat:")
        print("    This stress test ran under current conditions only. The historical")
        print("    partial-seat-map failure (4 available vs 63 after fix) may have been")
        print("    caused by slower network conditions, a larger seat map, or AMC server")
        print("    behaviour that varies by load or time of day. A definitive conclusion")
        print("    requires testing across multiple days, network conditions, and ideally")
        print("    a showtime with a larger seat map than those tested here.")

    elif any_ever_absent or (any_ever_changed and change_rate >= 0.04):  # 1+ in 25
        print("  CLASSIFICATION: Networkidle still required")
        print()
        print(f"  {total_any_changed} of {total_successful} run(s) showed a difference between the load-event")
        print(f"  capture and the networkidle capture.")
        if any_ever_absent:
            print(f"  {total_absent} run(s) found seatingLayout absent at the load event entirely.")
        print()
        print("  The historical partial-seat-map failure mode is reproducible under")
        print("  current conditions. Removing the networkidle wait would risk producing")
        print("  incomplete or absent seat data.")
        print()
        print("  networkidle is correctly serving as the completion signal for the RSC")
        print("  payload stream. Do not replace it without a more targeted readiness")
        print("  check that specifically waits for seatingLayout to be non-empty.")

    else:
        # Some changes but infrequent
        print("  CLASSIFICATION: Load event usually complete but exceptions observed")
        print()
        print(f"  {total_any_changed} of {total_successful} run(s) showed a difference between the load-event")
        print(f"  capture and the networkidle capture.")
        print()
        print("  The load event delivers a complete seat map in the vast majority of")
        print("  runs, but occasional exceptions suggest the RSC stream can sometimes")
        print("  still be in flight when the load event fires.")
        print()
        print("  Implication: a simple 'call content() immediately after goto()' would")
        print("  be unreliable. A targeted readiness check (e.g., poll until seat count")
        print("  is non-zero and stable for two consecutive samples) would be safer than")
        print("  the raw load event but could still exit earlier than networkidle on")
        print("  the majority of runs where the data is already complete.")

    # Variance note
    if any_load_variance or any_avail_variance:
        print()
        print("  [!] Seat count variance observed across runs at the load-event checkpoint.")
        print("      This indicates the page is sometimes delivering different amounts of")
        print("      data before the load event fires -- not just before networkidle.")
        print("      This is significant: it means the AMC document stream itself is")
        print("      non-deterministic at load time and networkidle (or a stability poll)")
        print("      is required for correctness, not just as a conservative safety margin.")

    print()


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> tuple[int, list[tuple[str, str]]]:
    n_runs = 25
    args = argv[1:]

    if args and args[0] == "--runs":
        if len(args) < 2:
            print("ERROR: --runs requires a value")
            sys.exit(1)
        try:
            n_runs = int(args[1])
            if n_runs < 1:
                raise ValueError()
        except ValueError:
            print("ERROR: --runs value must be a positive integer")
            sys.exit(1)
        args = args[2:]

    if len(args) < 2 or len(args) % 2 != 0:
        print("Usage: py amc_stress_probe.py [--runs N] LABEL URL [LABEL2 URL2 ...]")
        print()
        print("Example:")
        print('  py amc_stress_probe.py --runs 25 ^')
        print('      "Odyssey" "https://www.amctheatres.com/showtimes/143822631/seats" ^')
        print('      "Scary Movie" "https://www.amctheatres.com/showtimes/144254871/seats"')
        sys.exit(1)

    pairs = [(args[i], args[i + 1]) for i in range(0, len(args), 2)]
    return n_runs, pairs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    n_runs, pairs = parse_args(sys.argv)

    total_fetches = n_runs * len(pairs)
    est_min = total_fetches * 10 // 60
    est_sec = total_fetches * 10 % 60

    print("AMC Stress Probe")
    print(f"URLs   : {len(pairs)}")
    print(f"Runs   : {n_runs} per URL  ({total_fetches} total browser launches)")
    print(f"Est.   : ~{est_min}m {est_sec}s  (10s per launch estimate)")

    all_probes = []
    all_stats  = []

    for label, url in pairs:
        probe = run_stress(label, url, n_runs)
        stats = analyse(probe)
        all_probes.append(probe)
        all_stats.append(stats)
        report_analysis(probe, stats)

    classify(all_probes, all_stats)


if __name__ == "__main__":
    main()
