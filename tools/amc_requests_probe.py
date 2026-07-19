"""
amc_requests_probe.py

Investigates whether Playwright is required to obtain AMC seatingLayout data.
Fetches the same URL twice -- once with requests.get() and once with Playwright --
then compares seat extraction results and prints a recommendation.

No production files are read or modified.

Usage:
    py amc_requests_probe.py <AMC_SEAT_URL>

Example:
    py amc_requests_probe.py "https://www.amctheatres.com/showtimes/143822631/seats"
"""

import json
import re
import sys

import requests


# Copied verbatim from tracker_multiwatch.py so the comparison is fair.
RESERVABLE_TYPES = {"CanReserve", "LoveSeatLeft", "LoveSeatRight"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


# ---------------------------------------------------------------------------
# Extraction logic -- copied verbatim from tracker_multiwatch.py
# ---------------------------------------------------------------------------

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
# Probe helpers
# ---------------------------------------------------------------------------

def _seat_sort_key(name: str):
    m = re.match(r"^([A-Za-z]+)(\d+)$", name)
    return (m.group(1).upper(), int(m.group(2))) if m else (name, 0)


def count_occurrences(html: str) -> int:
    return html.count("seatingLayout")


def _available_seats(seat_map: dict) -> list:
    return [
        s for s in seat_map.values()
        if s.get("available") is True and s.get("type") in RESERVABLE_TYPES
    ]


def _seats_by_row(seats: list) -> dict:
    by_row: dict[str, list[str]] = {}
    for s in seats:
        m = re.match(r"^([A-Za-z]+)", s["name"])
        row = m.group(1).upper() if m else "?"
        by_row.setdefault(row, []).append(s["name"])
    return by_row


def analyze_html(html: str, label: str, html_save_path: str = None) -> dict:
    """Analyze HTML for seatingLayout data; print results; return summary dict."""
    occurrences = count_occurrences(html)

    result = {
        "size": len(html),
        "occurrences": occurrences,
        "extract_error": None,
        "total_seats": 0,
        "available_seats": 0,
        "all_seat_names": set(),
        "seat_types": [],
        "first_10_names": [],
    }

    print(f"\n--- {label} ---")
    print(f"  Response size (chars)       : {result['size']:,}")
    print(f"  'seatingLayout' present     : {'YES' if occurrences > 0 else 'NO'}")
    print(f"  'seatingLayout' occurrences : {occurrences}")

    if html_save_path:
        with open(html_save_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  Raw HTML saved to           : {html_save_path}")

    if occurrences == 0:
        print("  [!] seatingLayout absent -- extraction skipped")
        return result

    try:
        layout = extract_seating_layout(html)
        seats = collect_seats(layout)
        seat_map = {s["name"]: s for s in seats if s.get("name")}
        available = _available_seats(seat_map)

        all_names_sorted = sorted(seat_map.keys(), key=_seat_sort_key)
        seat_types = sorted({s.get("type", "") for s in seat_map.values() if s.get("type")})
        first_10 = all_names_sorted[:10]

        result["total_seats"] = len(seat_map)
        result["available_seats"] = len(available)
        result["all_seat_names"] = set(seat_map.keys())
        result["seat_types"] = seat_types
        result["first_10_names"] = first_10

        print(f"  Total seats collected       : {result['total_seats']}")
        print(f"  Available (reservable)      : {result['available_seats']}")
        print(f"  Seat types                  : {', '.join(seat_types) if seat_types else '(none)'}")
        print(f"  First seats                 : {', '.join(first_10) if first_10 else '(none)'}")

        if available:
            available_sorted = sorted(available, key=lambda s: _seat_sort_key(s["name"]))
            by_row = _seats_by_row(available_sorted)
            print(f"  Available by row:")
            for row in sorted(by_row):
                row_seats = sorted(
                    by_row[row],
                    key=lambda x: int(re.search(r"\d+", x).group()) if re.search(r"\d+", x) else 0,
                )
                print(f"    Row {row}: {' '.join(row_seats)}")
        else:
            print("  Available by row            : (none)")

    except Exception as exc:
        result["extract_error"] = str(exc)
        print(f"  [!] Extraction error: {exc}")

    return result


# ---------------------------------------------------------------------------
# Playwright fetch
# ---------------------------------------------------------------------------

def fetch_with_playwright(url: str) -> str:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

    print("  Launching headless Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=120_000)
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except PlaywrightTimeoutError:
            page.wait_for_timeout(12_000)
        html = page.content()
        browser.close()
    return html


# ---------------------------------------------------------------------------
# Comparison, overlap, and recommendation
# ---------------------------------------------------------------------------

def print_comparison(req: dict, pw: dict) -> None:
    print("\n" + "=" * 66)
    print("COMPARISON")
    print("=" * 66)
    print(f"  {'Metric':<35} {'requests':>12}  {'Playwright':>12}")
    print(f"  {'-'*35} {'-'*12}  {'-'*12}")
    print(f"  {'Response size (chars)':<35} {req['size']:>12,}  {pw['size']:>12,}")
    print(f"  {'seatingLayout occurrences':<35} {req['occurrences']:>12}  {pw['occurrences']:>12}")
    print(f"  {'Total seats collected':<35} {req['total_seats']:>12}  {pw['total_seats']:>12}")
    print(f"  {'Available reservable seats':<35} {req['available_seats']:>12}  {pw['available_seats']:>12}")


def print_overlap(req: dict, pw: dict) -> None:
    req_names = req.get("all_seat_names", set())
    pw_names  = pw.get("all_seat_names", set())

    if not req_names and not pw_names:
        return
    if not req_names or not pw_names:
        print("\n" + "=" * 66)
        print("SEAT-NAME OVERLAP")
        print("=" * 66)
        print("  [!] One phase returned no seats -- overlap cannot be computed")
        return

    common    = req_names & pw_names
    req_only  = req_names - pw_names
    pw_only   = pw_names - req_names
    denom     = max(len(req_names), len(pw_names))
    overlap_pct = len(common) / denom * 100

    print("\n" + "=" * 66)
    print("SEAT-NAME OVERLAP")
    print("=" * 66)
    print(f"  Requests seats      : {len(req_names)}")
    print(f"  Playwright seats    : {len(pw_names)}")
    print(f"  Common seat names   : {len(common)}")
    print(f"  Seat overlap        : {overlap_pct:.1f}%")

    if req_only:
        sample = sorted(req_only, key=_seat_sort_key)[:10]
        suffix = f"  (and {len(req_only) - 10} more)" if len(req_only) > 10 else ""
        print(f"  In requests only    : {', '.join(sample)}{suffix}")

    if pw_only:
        sample = sorted(pw_only, key=_seat_sort_key)[:10]
        suffix = f"  (and {len(pw_only) - 10} more)" if len(pw_only) > 10 else ""
        print(f"  In Playwright only  : {', '.join(sample)}{suffix}")

    if not req_only and not pw_only:
        print("  Seat maps are identical.")


def recommend(req: dict, pw: dict) -> None:
    print("\n" + "=" * 66)
    print("RECOMMENDATION")
    print("=" * 66)

    req_occ   = req["occurrences"]
    req_seats = req["total_seats"]
    req_avail = req["available_seats"]
    req_err   = req["extract_error"]
    pw_seats  = pw["total_seats"]
    pw_avail  = pw["available_seats"]

    req_names = req.get("all_seat_names", set())
    pw_names  = pw.get("all_seat_names", set())
    if req_names and pw_names:
        common = req_names & pw_names
        overlap_pct = len(common) / max(len(req_names), len(pw_names)) * 100
    else:
        overlap_pct = None

    # Case 1: seatingLayout absent in static response
    if req_occ == 0:
        print("  VERDICT: Playwright required")
        print()
        print("  requests.get() returned no seatingLayout data whatsoever.")
        print("  The AMC page requires JavaScript execution to stream RSC seat")
        print("  data into the DOM. Playwright cannot be removed.")
        return

    # Case 2: payload present but unparseable
    if req_err:
        print("  VERDICT: More investigation required")
        print()
        print(f"  seatingLayout appeared {req_occ} time(s) but could not be parsed.")
        print(f"  Error: {req_err}")
        print("  The static response may contain an escaped or truncated payload.")
        print("  Inspect the saved requests HTML file to examine the raw structure.")
        return

    # Case 3: payload parsed but no seats extracted while Playwright found some
    if req_seats == 0 and pw_seats > 0:
        print("  VERDICT: Playwright required")
        print()
        print(f"  seatingLayout was present ({req_occ} occurrence(s)) and parsed,")
        print(f"  but collect_seats() found 0 seat objects.")
        print(f"  Playwright collected {pw_seats} seat object(s).")
        print("  The static payload is a shell stub; real seat data is streamed")
        print("  by JavaScript after page load.")
        return

    # Case 4: seats found by both
    if req_seats > 0 and pw_seats > 0:
        if pw_avail == 0 and req_avail == 0:
            print("  VERDICT: More investigation required")
            print()
            print("  Both methods report 0 available seats.")
            if overlap_pct is not None and overlap_pct >= 95:
                print(f"  Seat maps are in strong agreement ({overlap_pct:.1f}% overlap,")
                print(f"  {req_seats} seats each). This may be an accurate sold-out result.")
            print("  Re-run against a URL with known available inventory to get a")
            print("  meaningful availability comparison.")
            return

        if pw_avail > 0:
            avail_pct = req_avail / pw_avail * 100
        else:
            avail_pct = 100.0 if req_avail == 0 else 0.0

        # Seat-map completeness is the more reliable signal when available counts
        # are low or the showtime has few open seats.
        seat_match = overlap_pct if overlap_pct is not None else avail_pct

        if seat_match >= 95 and avail_pct >= 90:
            print("  VERDICT: Playwright likely removable")
            print()
            print(f"  requests.get() found {req_seats} seat(s) total, {req_avail} available.")
            print(f"  Playwright found     {pw_seats} seat(s) total, {pw_avail} available.")
            if overlap_pct is not None:
                print(f"  Seat-name overlap: {overlap_pct:.1f}%  |  Available agreement: {avail_pct:.0f}%")
            else:
                print(f"  Available agreement: {avail_pct:.0f}%")
            print()
            print("  The static HTTP response appears to contain the complete seat map.")
            print("  Replacing Playwright with requests.get() is likely viable.")
            print()
            print("  Recommended next steps before removing Playwright:")
            print("    1. Run this probe against 3-5 different showtimes.")
            print("    2. Test both sold-out and partially-available showtimes.")
            print("    3. Consider a requests Session with cookies for long-term reliability.")

        elif seat_match >= 80 or avail_pct >= 70:
            print("  VERDICT: More investigation required")
            print()
            print(f"  requests.get() found {req_seats} seat(s) total, {req_avail} available.")
            print(f"  Playwright found     {pw_seats} seat(s) total, {pw_avail} available.")
            if overlap_pct is not None:
                print(f"  Seat-name overlap: {overlap_pct:.1f}%  |  Available agreement: {avail_pct:.0f}%")
            print()
            print("  Partial seat data is returned without JavaScript, but agreement")
            print("  is not strong enough to declare Playwright removable.")
            print("  Check the 'In Playwright only' list above to understand the gap.")

        else:
            print("  VERDICT: Playwright required")
            print()
            print(f"  requests.get() found {req_seats} seat(s) total, {req_avail} available.")
            print(f"  Playwright found     {pw_seats} seat(s) total, {pw_avail} available.")
            if overlap_pct is not None:
                print(f"  Seat-name overlap: {overlap_pct:.1f}%  |  Available agreement: {avail_pct:.0f}%")
            print()
            print("  The static response is severely incomplete. JavaScript execution")
            print("  is needed to fully hydrate the seat map before extraction.")
        return

    # Fallback
    print("  VERDICT: More investigation required")
    print()
    print("  Unexpected result combination:")
    print(f"    requests   -- seats={req_seats}, available={req_avail}")
    print(f"    Playwright -- seats={pw_seats}, available={pw_avail}")
    print("  Review the detailed output above for clues.")


# ---------------------------------------------------------------------------
# Single-URL probe
# ---------------------------------------------------------------------------

def run_probe(url: str, label: str, req_html_path: str) -> tuple[dict, dict]:
    """Run both phases for one URL; return (requests_result, playwright_result)."""
    W = "=" * 66
    print(f"\n{W}")
    print(f"PROBE: {label}")
    print(f"URL  : {url}")
    print(W)

    # Phase 1: requests.get()
    print("\nPhase 1: requests.get()")
    print(f"  User-Agent : {HEADERS['User-Agent']}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    except requests.RequestException as exc:
        print(f"  [!] Request failed: {exc}")
        return {}, {}

    print(f"  HTTP status : {resp.status_code}")
    if resp.history:
        print(f"  Redirects   : {len(resp.history)} ({resp.history[0].status_code} -> {resp.status_code})")
    if resp.status_code != 200:
        print("  [!] Non-200 response -- extraction may be unreliable")

    req_result = analyze_html(resp.text, "requests.get() extraction", html_save_path=req_html_path)

    # Phase 2: Playwright
    print("\nPhase 2: Playwright")
    try:
        playwright_html = fetch_with_playwright(url)
    except Exception as exc:
        print(f"  [!] Playwright fetch failed: {exc}")
        print("  Cannot produce a full comparison without Playwright results.")
        return req_result, {}

    pw_result = analyze_html(playwright_html, "Playwright extraction")

    print_comparison(req_result, pw_result)
    print_overlap(req_result, pw_result)
    recommend(req_result, pw_result)

    return req_result, pw_result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: py amc_requests_probe.py <AMC_SEAT_URL>")
        print()
        print("Example:")
        print('  py amc_requests_probe.py "https://www.amctheatres.com/showtimes/143822631/seats"')
        sys.exit(1)

    url = sys.argv[1].strip()

    print("AMC Requests Probe")
    print(f"URL: {url}")

    run_probe(url, label="Single URL", req_html_path="amc_seats_requests.html")
    print()


if __name__ == "__main__":
    main()
