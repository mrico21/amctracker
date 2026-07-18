import argparse
import json
import logging
import os
import re
import shutil
import sys
import socket
import traceback
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from pathlib import Path

import requests

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


WATCHLIST = Path(__file__).parent / "watchlist.json"
STATE_FILE = Path(__file__).parent / "state.json"
LOG_FILE = Path(__file__).parent / "tracker.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
RESERVABLE_TYPES = {"CanReserve", "LoveSeatLeft", "LoveSeatRight"}
_SMALL_PAGE_THRESHOLD = 200_000  # chars; real AMC pages are ~944KB+; Cloudflare block pages are ~7KB
TRACKER_VERSION = "1.0.5"

# Set to a watchlist name to enable adjacent-seat debug output for row G.
# Example: DEBUG_ADJACENT_WATCHLIST = "The Odyssey - Wed Jul 22"
DEBUG_ADJACENT_WATCHLIST = None


@dataclass
class WatchlistResult:
    name: str
    enabled: bool
    showtime_url: str
    watch_seats: list
    watch_any: list
    watch_adjacent: list
    status: str
    seats_available: int
    adjacent_windows_available: int
    notification_sent: bool
    failure_type: str | None
    error_message: str | None


def _compute_run_status(processed: int, failed: int) -> str:
    if failed == 0:
        return "success"
    if processed > 0:
        return "partial_failure"
    return "failed"


def _wl_result_to_dict(r: WatchlistResult) -> dict:
    monitoring = {}
    if r.watch_seats:
        monitoring["watch_seats"] = r.watch_seats
    if r.watch_any:
        monitoring["watch_any"] = r.watch_any
    if r.watch_adjacent:
        monitoring["watch_adjacent"] = [
            {"rows": adj.get("rows", []), "count": adj.get("count", 2)}
            for adj in r.watch_adjacent
        ]
    return {
        "name": r.name,
        "enabled": r.enabled,
        "showtime_url": r.showtime_url,
        "monitoring": monitoring,
        "status": r.status,
        "seats_available": r.seats_available,
        "adjacent_windows_available": r.adjacent_windows_available,
        "notification_sent": r.notification_sent,
        "failure_type": r.failure_type.lower() if r.failure_type else None,
        "error_message": r.error_message,
    }


def build_run_result(
    run_id, started_at, completed_at, duration_seconds,
    processed, skipped, failed,
    failed_challenge, failed_expired, failed_parse, failed_playwright,
    notifications_sent, cache_hits, cache_misses, wl_results,
) -> dict:
    return {
        "schema_version": 1,
        "generated_by": "AMCTracker",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": round(duration_seconds, 3),
        "tracker_version": TRACKER_VERSION,
        "hostname": socket.gethostname(),
        "run_status": _compute_run_status(processed, failed),
        "summary": {
            "total_watchlists": processed + skipped + failed,
            "succeeded": processed,
            "disabled": skipped,
            "failed": failed,
            "notifications_sent": notifications_sent,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
        },
        "failure_breakdown": {
            "challenge_pages": failed_challenge,
            "expired_urls": failed_expired,
            "parse_errors": failed_parse,
            "playwright_errors": failed_playwright,
        },
        "watchlists": [_wl_result_to_dict(r) for r in wl_results],
    }


def write_json_output(path: str, result: dict) -> None:
    try:
        Path(path).write_text(json.dumps(result, indent=2), encoding="utf-8")
        logging.info("JSON output written to %s", path)
    except Exception as exc:
        logging.warning("Failed to write JSON output to %s: %s", path, exc)


def rotate_log() -> None:
    if not LOG_FILE.exists() or LOG_FILE.stat().st_size < LOG_MAX_BYTES:
        return
    print("Log rotation triggered")
    log1 = Path(str(LOG_FILE) + ".1")
    log2 = Path(str(LOG_FILE) + ".2")
    log3 = Path(str(LOG_FILE) + ".3")
    if log3.exists():
        log3.unlink()
    if log2.exists():
        log2.rename(log3)
        print("  tracker.log.2 -> tracker.log.3")
    if log1.exists():
        log1.rename(log2)
        print("  tracker.log.1 -> tracker.log.2")
    LOG_FILE.rename(log1)
    print("  tracker.log   -> tracker.log.1")


def load_watchlists():
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("watchlists", [])
    if not entries:
        print("ERROR: watchlist.json has no 'watchlists' entries")
        sys.exit(1)
    for wl in entries:
        if not wl.get("showtime_url", "").strip():
            print(f"ERROR: watchlist '{wl.get('name', '?')}' missing showtime_url")
            sys.exit(1)
        if not wl.get("watch_seats") and not wl.get("watch_any") and not wl.get("watch_adjacent"):
            print(f"ERROR: watchlist '{wl.get('name', '?')}' needs watch_seats, watch_any, or watch_adjacent")
            sys.exit(1)
    return entries


def fetch_html(url: str) -> str:
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


def scan_seating_layouts(html: str) -> list:
    seen_starts = {}  # start_pos -> layout (preserves order, deduplicates)
    for marker in ('"seatingLayout"', '\\"seatingLayout\\"', "seatingLayout"):
        search_from = 0
        while True:
            idx = html.find(marker, search_from)
            if idx == -1:
                break
            search_from = idx + 1
            colon_pos = html.find(":", idx + len(marker))
            if colon_pos == -1:
                continue
            start = html.find("{", colon_pos)
            if start == -1 or start in seen_starts:
                continue
            depth, end = 0, -1
            for i in range(start, len(html)):
                if html[i] == "{":
                    depth += 1
                elif html[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end == -1:
                continue
            json_str = html[start:end + 1]
            try:
                layout = json.loads(json_str)
            except json.JSONDecodeError:
                try:
                    layout = json.loads(json_str.replace('\\"', '"'))
                except json.JSONDecodeError:
                    seen_starts[start] = None
                    continue
            seen_starts[start] = layout
    return [v for _, v in sorted(seen_starts.items()) if v is not None]


def classify_page_failure(html: str, exc: Exception) -> str:
    """Return a failure category label for a watchlist fetch exception.

    PLAYWRIGHT_ERROR  -- exception came from fetch_html() or Playwright infrastructure
    CHALLENGE_PAGE   -- page loaded but is too small to be a real AMC seat page
                        (Cloudflare rate-limit block, bot-protection interception, etc.)
    EXPIRED_URL      -- full-sized page loaded but contains no seatingLayout
                        (showtime may be expired or the URL is invalid)
    PARSE_ERROR      -- seatingLayout found in a full page but JSON parsing failed
                        (indicates an AMC page structure change requiring investigation)
    """
    if not isinstance(exc, ValueError):
        return "PLAYWRIGHT_ERROR"
    if len(html) < _SMALL_PAGE_THRESHOLD:
        return "CHALLENGE_PAGE"
    if "seatingLayout" not in html:
        return "EXPIRED_URL"
    return "PARSE_ERROR"


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    tmp = STATE_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    tmp.replace(STATE_FILE)


def send_notification(showtime_url: str, seat_name: str, old: str, new: str, wl_name: str) -> bool:
    user_key = os.environ.get("PUSHOVER_USER_KEY")
    api_token = os.environ.get("PUSHOVER_API_TOKEN")
    if not user_key or not api_token:
        return False
    try:
        requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": api_token,
                "user": user_key,
                "title": f"AMC Seat Alert — {wl_name}",
                "message": f"{seat_name}: {old} -> {new}\n{showtime_url}",
            },
            timeout=10,
        )
        logging.info("notification sent  %s  %s  %s -> %s", wl_name, seat_name, old, new)
    except requests.RequestException:
        pass
    return True


def send_any_notification(showtime_url: str, wl_name: str, newly_available: list[str]) -> bool:
    user_key = os.environ.get("PUSHOVER_USER_KEY")
    api_token = os.environ.get("PUSHOVER_API_TOKEN")
    if not user_key or not api_token:
        return False
    try:
        requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": api_token,
                "user": user_key,
                "title": f"AMC Seat Alert — {wl_name}",
                "message": "Available seats:\n" + "\n".join(newly_available) + f"\n{showtime_url}",
            },
            timeout=10,
        )
        logging.info("any-notification sent  %s  %s", wl_name, ", ".join(newly_available))
    except requests.RequestException:
        pass
    return True


def send_adjacent_notification(showtime_url: str, wl_name: str, windows: list[str], count: int) -> bool:
    logging.info("[DEBUG] send_adjacent_notification entered  wl=%s  windows=%s", wl_name, windows)
    print(f"[DEBUG] send_adjacent_notification entered  wl={wl_name}  windows={windows}")
    user_key = os.environ.get("PUSHOVER_USER_KEY")
    api_token = os.environ.get("PUSHOVER_API_TOKEN")
    logging.info("[DEBUG] credentials  user_key_set=%s  api_token_set=%s", bool(user_key), bool(api_token))
    print(f"[DEBUG] credentials  user_key_set={bool(user_key)}  api_token_set={bool(api_token)}")
    if not user_key or not api_token:
        logging.info("[DEBUG] send_adjacent_notification returning False (missing credentials)")
        print("[DEBUG] send_adjacent_notification returning False (missing credentials)")
        return False
    try:
        logging.info("[DEBUG] attempting Pushover HTTP request")
        print("[DEBUG] attempting Pushover HTTP request")
        resp = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": api_token,
                "user": user_key,
                "title": f"AMC Seat Alert — {wl_name}",
                "message": "Adjacent seats available:\n\n" + "\n".join(windows) + f"\n{showtime_url}",
            },
            timeout=10,
        )
        logging.info("[DEBUG] Pushover HTTP response  status=%d  body=%s", resp.status_code, resp.text[:200])
        print(f"[DEBUG] Pushover HTTP response  status={resp.status_code}  body={resp.text[:200]}")
        logging.info("adjacent-notification sent  %s  count=%d  %s", wl_name, count, ", ".join(windows))
    except requests.RequestException as e:
        logging.info("[DEBUG] Pushover request raised RequestException: %s", e)
        print(f"[DEBUG] Pushover request raised RequestException: {e}")
    logging.info("[DEBUG] send_adjacent_notification returning True")
    print("[DEBUG] send_adjacent_notification returning True")
    return True


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def expand_seat_input(raw: str) -> list[str] | None:
    result = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        m = re.match(r'^([A-Za-z]+)(\d+)-([A-Za-z]+)(\d+)$', token)
        if m:
            row1, n1, row2, n2 = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
            if row1.upper() != row2.upper():
                print(f"ERROR: range '{token}' spans different rows ({row1} vs {row2}).")
                return None
            if n1 > n2:
                print(f"ERROR: range '{token}': start {n1} > end {n2}.")
                return None
            result.extend(f"{row1}{n}" for n in range(n1, n2 + 1))
        elif re.match(r'^[A-Za-z]+\d+$', token):
            result.append(token)
        else:
            print(f"ERROR: '{token}' is not a valid seat or range (e.g. J15 or J1-J5).")
            return None
    return result


def expand_row_input(raw: str) -> list[str] | None:
    result = []
    for token in raw.split(","):
        token = token.strip().upper()
        if not token:
            continue
        m = re.match(r'^([A-Z])-([A-Z])$', token)
        if m:
            r1, r2 = m.group(1), m.group(2)
            if r1 > r2:
                print(f"ERROR: range '{token}' is descending ({r1} > {r2}).")
                return None
            result.extend(chr(c) for c in range(ord(r1), ord(r2) + 1))
        elif re.match(r'^[A-Z]$', token):
            result.append(token)
        else:
            print(f"ERROR: '{token}' is not a valid row letter or range (e.g. J or H-K).")
            return None
    return result if result else None


def add_watchlist() -> None:
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    existing_names = {w.get("name", "").lower() for w in data.get("watchlists", [])}

    while True:
        name = input("Watchlist name: ").strip()
        if not name:
            print("Name cannot be blank.")
        elif name.lower() in existing_names:
            print(f"'{name}' already exists. Enter a different name.")
        else:
            break
    while True:
        url = input("Showtime URL: ").strip()
        if url:
            break
        print("URL cannot be blank.")

    print("Monitor mode:")
    print("  1. watch_seats")
    print("  2. watch_any")
    print("  3. watch_adjacent")
    while True:
        val = input("Selection [1]: ").strip()
        if not val:
            mode = 1
            break
        if val in ("1", "2", "3"):
            mode = int(val)
            break
        print("Enter 1, 2, or 3.")

    if mode in (1, 2):
        while True:
            raw_seats = input("Seats (comma-sep, ranges ok e.g. J1-J5,K10): ")
            seats = expand_seat_input(raw_seats)
            if seats is None:
                continue
            if seats:
                break
            print("At least one seat is required.")
    else:
        while True:
            raw = input("Rows (range G-L, comma-sep G,H,I, or single J): ").strip()
            if not raw:
                print("At least one row is required.")
                continue
            rows = expand_row_input(raw)
            if rows is not None:
                break
        while True:
            val = input("Adjacent seat count [2]: ").strip()
            if not val:
                adj_count = 2
                break
            try:
                n = int(val)
                if n >= 2:
                    adj_count = n
                    break
                else:
                    print("ERROR: count must be 2 or greater.")
            except ValueError:
                print("ERROR: count must be a positive integer.")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = WATCHLIST.with_suffix(f".json.bak.{ts}")
    shutil.copy2(WATCHLIST, backup)
    print(f"Backup saved to {backup.name}")

    if mode == 1:
        data["watchlists"].append({"name": name, "showtime_url": url, "watch_seats": seats})
    elif mode == 2:
        data["watchlists"].append({"name": name, "showtime_url": url, "watch_any": seats})
    else:
        data["watchlists"].append({"name": name, "showtime_url": url, "watch_adjacent": [{"rows": rows, "count": adj_count}]})
    with open(WATCHLIST, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    total = len(data["watchlists"])
    if mode == 1:
        print(f"Added '{name}' (watch_seats, {len(seats)} seats). watchlist.json now has {total} entr{'y' if total == 1 else 'ies'}.")
    elif mode == 2:
        print(f"Added '{name}' (watch_any, {len(seats)} seats). watchlist.json now has {total} entr{'y' if total == 1 else 'ies'}.")
    else:
        print(f"Added '{name}' (watch_adjacent, rows {','.join(rows)}, count={adj_count}). watchlist.json now has {total} entr{'y' if total == 1 else 'ies'}.")


def _write_watchlist_json(data: dict) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = WATCHLIST.with_suffix(f".json.bak.{ts}")
    shutil.copy2(WATCHLIST, backup)
    print(f"Backup saved to {backup.name}")
    with open(WATCHLIST, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def enable_watchlist(index: int) -> None:
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("watchlists", [])
    if index < 1 or index > len(entries):
        print(f"ERROR: index {index} out of range (1-{len(entries)})")
        sys.exit(1)
    entries[index - 1]["enabled"] = True
    _write_watchlist_json(data)
    print(f"Enabled: {entries[index - 1]['name']}")


def disable_watchlist(index: int) -> None:
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("watchlists", [])
    if index < 1 or index > len(entries):
        print(f"ERROR: index {index} out of range (1-{len(entries)})")
        sys.exit(1)
    entries[index - 1]["enabled"] = False
    _write_watchlist_json(data)
    print(f"Disabled: {entries[index - 1]['name']}")


def remove_watchlist(index: int) -> None:
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("watchlists", [])
    if index < 1 or index > len(entries):
        print(f"ERROR: index {index} out of range (1-{len(entries)})")
        sys.exit(1)
    entry = entries[index - 1]
    confirm = input(f"Remove '{entry['name']}'? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        return
    entries.pop(index - 1)
    _write_watchlist_json(data)
    count = len(entries)
    print(f"Removed: {entry['name']} ({count} entr{'y' if count == 1 else 'ies'} remaining)")


def clone_watchlist(index: int) -> None:
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("watchlists", [])
    if index < 1 or index > len(entries):
        print(f"ERROR: index {index} out of range (1-{len(entries)})")
        sys.exit(1)

    source = entries[index - 1]
    print(f"\nCloning: {source['name']}")
    if source.get("watch_seats"):
        print(f"  watch_seats : {', '.join(source['watch_seats'])}")
    if source.get("watch_any"):
        print(f"  watch_any   : {', '.join(source['watch_any'])}")
    if source.get("watch_adjacent"):
        for adj in source["watch_adjacent"]:
            print(f"  watch_adjacent:")
            print(f"    Rows  : {', '.join(adj.get('rows', []))}")
            print(f"    Count : {adj.get('count', 2)}")
    print()

    existing_names = {w.get("name", "").lower() for w in entries}
    while True:
        name = input("New name (required): ").strip()
        if not name:
            print("Name cannot be blank.")
        elif name.lower() in existing_names:
            print(f"'{name}' already exists. Enter a different name.")
        else:
            break

    url_input = input("New URL (Enter to keep original): ").strip()
    new_url = url_input if url_input else source.get("showtime_url", "")

    existing_urls = [w.get("showtime_url", "").strip() for w in entries if w is not source]
    if new_url.strip() in existing_urls:
        confirm = input("Warning: another watchlist already uses this URL. Continue anyway? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return

    clone = deepcopy(source)
    clone["name"] = name
    clone["showtime_url"] = new_url
    clone["enabled"] = True

    entries.append(clone)
    _write_watchlist_json(data)

    print(f"\nClone created successfully")
    print(f"Source : {source['name']}")
    print(f"New    : {clone['name']}")
    print(f"URL    : {clone['showtime_url']}")
    if clone.get("watch_seats"):
        print(f"\nwatch_seats:")
        print(f"{', '.join(clone['watch_seats'])}")
    if clone.get("watch_any"):
        print(f"\nwatch_any:")
        print(f"{', '.join(clone['watch_any'])}")
    if clone.get("watch_adjacent"):
        for adj in clone["watch_adjacent"]:
            print(f"\nwatch_adjacent:")
            print(f"Rows  : {', '.join(adj.get('rows', []))}")
            print(f"Count : {adj.get('count', 2)}")


def edit_watchlist(index: int) -> None:
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("watchlists", [])
    if index < 1 or index > len(entries):
        print(f"ERROR: index {index} out of range (1-{len(entries)})")
        sys.exit(1)
    wl = entries[index - 1]

    print(f"\nEditing: {wl['name']}")
    print("Press Enter to keep current value.\n")

    other_names = {w.get("name", "").lower() for i, w in enumerate(entries) if i != index - 1}
    while True:
        val = input(f"Name        [{wl.get('name', '')}]: ").strip()
        if not val:
            break
        if val.lower() in other_names:
            print(f"'{val}' already exists. Enter a different name or press Enter to keep current.")
        else:
            wl["name"] = val
            break

    val = input(f"URL         [{wl.get('showtime_url', '')}]: ").strip()
    if val:
        wl["showtime_url"] = val

    cur_seats = ", ".join(wl["watch_seats"]) if wl.get("watch_seats") else "(none)"
    while True:
        val = input(f"watch_seats [{cur_seats}] (comma-sep, ranges ok, '-' to remove): ").strip()
        if not val or val == "-":
            break
        expanded = expand_seat_input(val)
        if expanded is not None:
            wl["watch_seats"] = expanded
            break
    if val == "-":
        wl.pop("watch_seats", None)

    cur_any = ", ".join(wl["watch_any"]) if wl.get("watch_any") else "(none)"
    while True:
        val = input(f"watch_any   [{cur_any}] (comma-sep, ranges ok, '-' to remove): ").strip()
        if not val or val == "-":
            break
        expanded = expand_seat_input(val)
        if expanded is not None:
            wl["watch_any"] = expanded
            break
    if val == "-":
        wl.pop("watch_any", None)

    adj_configs = wl.get("watch_adjacent", [])
    if adj_configs:
        total = len(adj_configs)
        for i, adj in enumerate(adj_configs):
            label = f" {i + 1} of {total}" if total > 1 else ""
            cur_rows = ",".join(adj.get("rows", []))
            while True:
                val = input(f"Adjacent rows{label} [{cur_rows}]: ").strip()
                if not val:
                    break
                expanded = expand_row_input(val)
                if expanded is not None:
                    adj["rows"] = expanded
                    break
            cur_count = adj.get("count", 2)
            while True:
                val = input(f"Adjacent count{label} [{cur_count}]: ").strip()
                if not val:
                    break
                try:
                    n = int(val)
                    if n >= 2:
                        adj["count"] = n
                        break
                    else:
                        print("ERROR: count must be 2 or greater.")
                except ValueError:
                    print("ERROR: count must be a positive integer.")

    if not wl.get("watch_seats") and not wl.get("watch_any") and not wl.get("watch_adjacent"):
        print("ERROR: watchlist must have watch_seats, watch_any, or watch_adjacent.")
        sys.exit(1)

    cur_enabled = "Yes" if wl.get("enabled", True) else "No"
    val = input(f"Enabled     [{cur_enabled}] (y/n): ").strip().lower()
    if val == "y":
        wl["enabled"] = True
    elif val == "n":
        wl["enabled"] = False

    _write_watchlist_json(data)
    print(f"Saved: {wl['name']}")


def show_health() -> None:
    issues = []
    warnings = []
    wl_data = None

    if not WATCHLIST.exists():
        print("[FAIL] watchlist.json not found")
        issues.append("watchlist.json missing")
    else:
        try:
            with open(WATCHLIST, encoding="utf-8") as f:
                wl_data = json.load(f)
            print("[OK]   watchlist.json valid")
        except json.JSONDecodeError as e:
            print(f"[FAIL] watchlist.json invalid JSON: {e}")
            issues.append("watchlist.json invalid")

    if not STATE_FILE.exists():
        print("[WARN] state.json not found (no runs yet?)")
        warnings.append("state.json missing")
    else:
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                json.load(f)
            print("[OK]   state.json valid")
        except json.JSONDecodeError as e:
            print(f"[FAIL] state.json invalid JSON: {e}")
            issues.append("state.json invalid")

    try:
        with open(LOG_FILE, "a", encoding="utf-8"):
            pass
        print("[OK]   tracker.log writable")
    except OSError as e:
        print(f"[FAIL] tracker.log not writable: {e}")
        issues.append("tracker.log not writable")

    try:
        import playwright  # noqa: F401
        print("[OK]   Playwright installed")
    except ImportError:
        print("[FAIL] Playwright not installed")
        issues.append("Playwright not installed")

    try:
        import requests as _r  # noqa: F401
        print("[OK]   requests installed")
    except ImportError:
        print("[FAIL] requests not installed")
        issues.append("requests not installed")

    user_key = os.environ.get("PUSHOVER_USER_KEY")
    api_token = os.environ.get("PUSHOVER_API_TOKEN")
    if user_key and api_token:
        print("[OK]   Pushover configured")
    else:
        missing = [k for k, v in [("PUSHOVER_USER_KEY", user_key), ("PUSHOVER_API_TOKEN", api_token)] if not v]
        print(f"[WARN] Pushover not configured ({', '.join(missing)} missing)")
        warnings.append("Pushover env vars missing")

    print()
    if wl_data is not None:
        entries = wl_data.get("watchlists", [])
        enabled_count = sum(1 for w in entries if w.get("enabled", True))
        disabled_count = len(entries) - enabled_count
        print(f"Enabled watchlists  : {enabled_count}")
        print(f"Disabled watchlists : {disabled_count}")

    print()
    if issues:
        print(f"Overall status: UNHEALTHY ({len(issues)} issue(s))")
    elif warnings:
        print(f"Overall status: HEALTHY ({len(warnings)} warning(s))")
    else:
        print("Overall status: HEALTHY")


def show_stats() -> None:
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("watchlists", [])

    total = len(entries)
    enabled = sum(1 for w in entries if w.get("enabled", True))
    disabled = total - enabled
    unique_urls = len({w.get("showtime_url", "").strip() for w in entries})
    total_watch_seats = sum(len(w.get("watch_seats", [])) for w in entries)
    total_watch_any = sum(len(w.get("watch_any", [])) for w in entries)

    def file_size(path: Path) -> str:
        return f"{path.stat().st_size:,} bytes" if path.exists() else "(not found)"

    print("Watchlists")
    print(f"  Total       : {total}")
    print(f"  Enabled     : {enabled}")
    print(f"  Disabled    : {disabled}")
    print(f"  Unique URLs : {unique_urls}")
    print()
    print("Seats")
    print(f"  watch_seats entries : {total_watch_seats}")
    print(f"  watch_any entries   : {total_watch_any}")
    print()
    print("Files")
    print(f"  watchlist.json : {file_size(WATCHLIST)}")
    print(f"  state.json     : {file_size(STATE_FILE)}")
    print(f"  tracker.log    : {file_size(LOG_FILE)}")


def show_watchlists() -> None:
    watchlists = load_watchlists()
    for i, wl in enumerate(watchlists):
        enabled = "Yes" if wl.get("enabled", True) else "No"
        print(f"\n[{i + 1}] {wl['name']}")
        print(f"  Enabled     : {enabled}")
        print(f"  URL         : {wl['showtime_url'].strip()}")
        if wl.get("watch_seats"):
            print(f"  watch_seats : {', '.join(wl['watch_seats'])}")
        if wl.get("watch_any"):
            print(f"  watch_any   : {', '.join(wl['watch_any'])}")
        if wl.get("watch_adjacent"):
            for adj in wl["watch_adjacent"]:
                print(f"  watch_adjacent:")
                print(f"    Rows  : {', '.join(adj.get('rows', []))}")
                print(f"    Count : {adj.get('count', 2)}")


def inspect_watchlist(index: int) -> None:
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("watchlists", [])
    if index < 1 or index > len(entries):
        print(f"ERROR: index {index} out of range (1-{len(entries)})")
        sys.exit(1)
    wl = entries[index - 1]
    url = wl["showtime_url"].strip()
    wl_name = wl["name"]

    print(f"Inspecting [{index}]: {wl_name}")
    print(f"URL: {url}")
    print()
    print("Fetching page...")

    html = fetch_html(url)
    layout = extract_seating_layout(html)
    all_seats_list = collect_seats(layout)
    seat_map = {s["name"]: s for s in all_seats_list if s.get("name")}

    def seat_sort_key(name):
        m = re.match(r'^([A-Za-z]+)(\d+)$', name)
        return (m.group(1).upper(), int(m.group(2))) if m else (name, 0)

    available_seats = sorted(
        [s for s in all_seats_list
         if s.get("available") is True and s.get("type") in RESERVABLE_TYPES and s.get("name")],
        key=lambda s: seat_sort_key(s["name"]),
    )

    print()
    print("Seat map")
    print(f"  Total seats     : {len(seat_map)}")
    print(f"  Available seats : {len(available_seats)}")
    print()

    print("All available seats:")
    if available_seats:
        for s in available_seats:
            print(f"  {s['name']:<6}  type={s.get('type', '?')}")
    else:
        print("  (none)")
    print()

    # Section A: adjacent windows across all rows in seat map
    watch_adjacent_configs = wl.get("watch_adjacent", [])
    adj_count = watch_adjacent_configs[0].get("count", 2) if watch_adjacent_configs else 2

    all_rows: dict[str, list[tuple[int, str]]] = {}
    for sn in seat_map:
        m = re.match(r'^([A-Za-z]+)(\d+)$', sn)
        if m:
            all_rows.setdefault(m.group(1).upper(), []).append((int(m.group(2)), sn))

    all_available_windows = []
    for row in sorted(all_rows):
        seat_names = [s[1] for s in sorted(all_rows[row])]
        for i in range(len(seat_names) - adj_count + 1):
            window = seat_names[i:i + adj_count]
            if all(
                seat_map.get(sn, {}).get("available") is True
                and seat_map.get(sn, {}).get("type") in RESERVABLE_TYPES
                for sn in window
            ):
                all_available_windows.append("-".join(window))

    print(f"Adjacent windows available (all rows, {adj_count}-seat):")
    if all_available_windows:
        for w in all_available_windows:
            print(f"  {w}")
    else:
        print("  (none)")
    print()

    # Section B: matching watchlist criteria
    print("Matching watchlist criteria:")
    matching_windows_total = 0

    if watch_adjacent_configs:
        for adj_config in watch_adjacent_configs:
            rows = adj_config.get("rows", [])
            count = adj_config.get("count", 2)
            config_available = []
            for row in rows:
                seat_names = [s[1] for s in sorted(all_rows.get(row.upper(), []))]
                for i in range(len(seat_names) - count + 1):
                    window = seat_names[i:i + count]
                    if all(
                        seat_map.get(sn, {}).get("available") is True
                        and seat_map.get(sn, {}).get("type") in RESERVABLE_TYPES
                        for sn in window
                    ):
                        config_available.append("-".join(window))
            matching_windows_total += len(config_available)
            rows_str = ",".join(rows)
            print(f"  watch_adjacent  rows {rows_str}  count={count}  ->  {len(config_available)} window(s) available")
            for w in config_available:
                print(f"    {w}")

    if wl.get("watch_seats"):
        ws_available = [
            sn for sn in wl["watch_seats"]
            if seat_map.get(sn, {}).get("available") is True
            and seat_map.get(sn, {}).get("type") in RESERVABLE_TYPES
        ]
        print(f"  watch_seats  ->  {len(ws_available)} of {len(wl['watch_seats'])} available")
        for sn in ws_available:
            print(f"    {sn}")

    if wl.get("watch_any"):
        wa_available = [
            sn for sn in wl["watch_any"]
            if seat_map.get(sn, {}).get("available") is True
            and seat_map.get(sn, {}).get("type") in RESERVABLE_TYPES
        ]
        print(f"  watch_any    ->  {len(wa_available)} of {len(wl['watch_any'])} available")
        for sn in wa_available:
            print(f"    {sn}")

    if not watch_adjacent_configs and not wl.get("watch_seats") and not wl.get("watch_any"):
        print("  (no monitoring criteria configured)")

    print()
    print("Summary:")
    print(f"  Available seats discovered   : {len(available_seats)}")
    print(f"  Adjacent windows available   : {len(all_available_windows)}")
    print(f"  Matching watchlist windows   : {matching_windows_total}")


def diagnose_layout(index: int) -> None:
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("watchlists", [])
    if index < 1 or index > len(entries):
        print(f"ERROR: index {index} out of range (1-{len(entries)})")
        sys.exit(1)
    wl = entries[index - 1]
    url = wl["showtime_url"].strip()

    print(f"Diagnosing [{index}]: {wl['name']}")
    print(f"URL: {url}")
    print()
    print("Fetching page...")

    html = fetch_html(url)
    layouts = scan_seating_layouts(html)

    print()
    print(f"seatingLayout occurrences found: {len(layouts)}")
    print()

    for i, layout in enumerate(layouts, 1):
        seats = collect_seats(layout)
        seat_map = {s["name"]: s for s in seats if s.get("name")}
        available = sum(
            1 for s in seat_map.values()
            if s.get("available") is True and s.get("type") in RESERVABLE_TYPES
        )
        print(f"Occurrence {i}:")
        print(f"  total seats    : {len(seat_map)}")
        print(f"  available seats: {available}")
        print()


def diagnose_seat_types(index: int) -> None:
    from collections import Counter
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("watchlists", [])
    if index < 1 or index > len(entries):
        print(f"ERROR: index {index} out of range (1-{len(entries)})")
        sys.exit(1)
    wl = entries[index - 1]
    url = wl["showtime_url"].strip()
    print(f"Diagnosing seat types [{index}]: {wl['name']}")
    print(f"URL: {url}")
    print()
    print("Fetching page...")
    html = fetch_html(url)
    layout = extract_seating_layout(html)
    seats = collect_seats(layout)
    seat_map = {s["name"]: s for s in seats if s.get("name")}
    all_seats = list(seat_map.values())
    print()
    print(f"Total seat objects collected: {len(all_seats)}")
    print()
    print("First 20 seat objects:")
    for s in all_seats[:20]:
        print(f"  name={str(s.get('name')):<10}  available={str(s.get('available')):<6}  type={s.get('type')}")
    print()
    print("Counts by (type, available):")
    counts = Counter((s.get("type"), s.get("available")) for s in all_seats)
    for (t, a), n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {str(t):<25} / {str(a):<5} : {n}")
    print()
    count_is_true    = sum(1 for s in all_seats if s.get("available") is True)
    count_eq_true    = sum(1 for s in all_seats if s.get("available") == True)
    count_canreserve = sum(1 for s in all_seats if s.get("type") == "CanReserve")
    count_strict     = sum(1 for s in all_seats if s.get("available") is True and s.get("type") in RESERVABLE_TYPES)
    print(f"available is True              : {count_is_true}")
    print(f"available == True              : {count_eq_true}")
    print(f"type == CanReserve             : {count_canreserve}")
    print(f"production filter (RESERVABLE) : {count_strict}")


def generate_block() -> None:
    while True:
        row = input("Row (e.g. J): ").strip().upper()
        if row:
            break
        print("Row cannot be blank.")

    while True:
        try:
            center = int(input("Center seat number (e.g. 16): ").strip())
            break
        except ValueError:
            print("Must be an integer.")

    while True:
        try:
            radius = int(input("Radius (e.g. 3): ").strip())
            if radius >= 0:
                break
            print("Radius must be 0 or greater.")
        except ValueError:
            print("Must be an integer.")

    seats = [f"{row}{center + i}" for i in range(-radius, radius + 1)]

    print()
    for seat in seats:
        print(seat)

    print()
    print("[")
    for i, seat in enumerate(seats):
        comma = "," if i < len(seats) - 1 else ""
        print(f'  "{seat}"{comma}')
    print("]")


def list_seats(wl_name: str) -> None:
    watchlists = load_watchlists()
    wl = next((w for w in watchlists if w["name"] == wl_name), None)
    if wl is None:
        print(f"ERROR: no watchlist named '{wl_name}'")
        print("Available:")
        for w in watchlists:
            print(f"  {w['name']}")
        sys.exit(1)

    print(f"Fetching: {wl['showtime_url'].strip()}")
    print("Loading page...")
    html = fetch_html(wl["showtime_url"].strip())
    layout = extract_seating_layout(html)
    all_seats = collect_seats(layout)

    available = [
        s["name"] for s in all_seats
        if s.get("available") is True
        and s.get("type") in RESERVABLE_TYPES
        and s.get("name")
    ]

    if not available:
        print("No available seats found.")
        return

    rows: dict[str, list[str]] = {}
    for name in available:
        m = re.match(r"^([A-Za-z]+)", name)
        row = m.group(1).upper() if m else "?"
        rows.setdefault(row, []).append(name)

    for row in sorted(rows):
        seats = sorted(rows[row], key=lambda s: int(re.search(r"\d+", s).group()) if re.search(r"\d+", s) else 0)
        print(f"\nRow {row}:")
        print(" ".join(seats))


def main():
    parser = argparse.ArgumentParser(description="AMC seat tracker (multi-watchlist)")
    parser.add_argument("--health", action="store_true", help="Verify tracker environment without contacting AMC")
    parser.add_argument("--stats", action="store_true", help="Show watchlist and file statistics")
    parser.add_argument("--show-watchlists", action="store_true", help="Print all configured watchlists")
    parser.add_argument("--clone",   metavar="INDEX", type=int, help="Clone watchlist by index")
    parser.add_argument("--edit",    metavar="INDEX", type=int, help="Edit watchlist by index")
    parser.add_argument("--enable",  metavar="INDEX", type=int, help="Enable watchlist by index")
    parser.add_argument("--disable", metavar="INDEX", type=int, help="Disable watchlist by index")
    parser.add_argument("--remove",  metavar="INDEX", type=int, help="Remove watchlist by index (requires confirmation)")
    parser.add_argument("--add", action="store_true", help="Interactively add a new watchlist entry")
    parser.add_argument("--inspect",  metavar="INDEX", type=int, help="Diagnose seat detection for a watchlist by index (read-only)")
    parser.add_argument("--diagnose-layout", metavar="INDEX", type=int, help="Count all seatingLayout occurrences in the fetched HTML and report seat totals per occurrence (diagnostic only)")
    parser.add_argument("--diagnose-seat-types", metavar="INDEX", type=int, help="Inspect raw seat object types and availability values (diagnostic only)")
    parser.add_argument("--generate-block", action="store_true", help="Generate a seat block from row, center, and radius")
    parser.add_argument("--list-seats", metavar="NAME", help="List all available CanReserve seats for the named watchlist")
    parser.add_argument("--debug", action="store_true", help="Save raw HTML to disk")
    parser.add_argument("--simulate-available", metavar="SEAT", action="append", default=[], help="Override seat to AVAILABLE (testing only)")
    parser.add_argument("--test-notification", action="store_true", help="Send a test Pushover message and exit")
    parser.add_argument("--json-output", metavar="PATH", help="Write a JSON run summary to PATH after each tracking run")
    args = parser.parse_args()

    rotate_log()

    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info("--- run started ---")

    if args.health:
        show_health()
        return

    if args.stats:
        show_stats()
        return

    if args.show_watchlists:
        show_watchlists()
        return

    if args.clone is not None:
        clone_watchlist(args.clone)
        return

    if args.edit is not None:
        edit_watchlist(args.edit)
        return

    if args.enable is not None:
        enable_watchlist(args.enable)
        return

    if args.disable is not None:
        disable_watchlist(args.disable)
        return

    if args.remove is not None:
        remove_watchlist(args.remove)
        return

    if args.add:
        add_watchlist()
        return

    if args.inspect is not None:
        inspect_watchlist(args.inspect)
        return

    if args.diagnose_layout is not None:
        diagnose_layout(args.diagnose_layout)
        return

    if args.diagnose_seat_types is not None:
        diagnose_seat_types(args.diagnose_seat_types)
        return

    if args.generate_block:
        generate_block()
        return

    if args.list_seats:
        list_seats(args.list_seats)
        return

    if args.test_notification:
        user_key = os.environ.get("PUSHOVER_USER_KEY")
        api_token = os.environ.get("PUSHOVER_API_TOKEN")
        if not user_key or not api_token:
            print("ERROR: PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN must be set")
            sys.exit(1)
        wl_name, wl_url = "TEST", ""
        try:
            with open(WATCHLIST, encoding="utf-8") as f:
                data = json.load(f)
            first = data.get("watchlists", [{}])[0]
            wl_name = first.get("name", "TEST")
            wl_url = first.get("showtime_url", "")
        except Exception:
            pass
        send_notification(wl_url, "TEST", "UNAVAILABLE", "AVAILABLE", wl_name)
        print("Test notification sent.")
        return

    watchlists = load_watchlists()

    state = load_state()
    html_cache = {}
    start_time = time.monotonic()
    processed = 0
    skipped = 0
    failed = 0
    failed_challenge = 0
    failed_expired = 0
    failed_parse = 0
    failed_playwright = 0
    cache_hits = 0
    cache_misses = 0
    notifications_sent = 0
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    wl_results = []

    for wl in watchlists:
        wl_name = wl["name"]

        if not wl.get("enabled", True):
            print(f"\n=== {wl_name} [DISABLED] ===")
            logging.info("[%s] disabled — skipped", wl_name)
            skipped += 1
            wl_results.append(WatchlistResult(
                name=wl_name,
                enabled=False,
                showtime_url=wl.get("showtime_url", ""),
                watch_seats=wl.get("watch_seats", []),
                watch_any=wl.get("watch_any", []),
                watch_adjacent=wl.get("watch_adjacent", []),
                status="skipped",
                seats_available=0,
                adjacent_windows_available=0,
                notification_sent=False,
                failure_type=None,
                error_message=None,
            ))
            continue

        html = ""
        try:
            url = wl["showtime_url"].strip()
            watch_seats = wl.get("watch_seats", [])
            watch_any_seats = wl.get("watch_any", [])
            watch_adjacent_configs = wl.get("watch_adjacent", [])
            wl_notif_sent = False

            print(f"\n=== {wl_name} ===")
            print(f"Showtime : {url}")
            if watch_seats:
                print(f"Watching : {', '.join(watch_seats)}")
            if watch_any_seats:
                print(f"Watch-any: {', '.join(watch_any_seats)}")
            if watch_adjacent_configs:
                for adj in watch_adjacent_configs:
                    print(f"Watch-adj: rows {','.join(adj.get('rows', []))}, {adj.get('count', 2)}-seat windows")
            print("Loading page...")

            if url in html_cache:
                logging.info("[%s] CACHE HIT  %s", wl_name, url)
                print("(cache hit -- reusing fetched HTML)")
                html = html_cache[url]
                cache_hits += 1
            else:
                logging.info("[%s] CACHE MISS  %s", wl_name, url)
                html = fetch_html(url)
                html_cache[url] = html
                cache_misses += 1

            if args.debug:
                debug_file = f"amc_seats_{_slug(wl_name)}.html"
                Path(debug_file).write_text(html, encoding="utf-8")
                print(f"[debug] HTML saved to {debug_file} ({len(html):,} chars)")

            layout = extract_seating_layout(html)
            all_seats = collect_seats(layout)
            seat_map = {s["name"]: s for s in all_seats if s.get("name")}

            previous = state.get(wl_name, {})
            current = {}

            if watch_seats:
                print(f"\n{'Seat':<6}  {'Status':<12}  {'Type':<12}  Tier")
                print("-" * 44)
                for seat_name in watch_seats:
                    seat = seat_map.get(seat_name)
                    if seat is None:
                        print(f"{seat_name:<6}  {'NOT FOUND':<12}")
                        current[seat_name] = "NOT FOUND"
                        logging.info("[%s] seat %-6s  NOT FOUND", wl_name, seat_name)
                        continue
                    available = seat.get("available") is True
                    stype = seat.get("type", "")
                    tier = seat.get("seatTier", "")
                    status = "AVAILABLE" if available and stype in RESERVABLE_TYPES else "UNAVAILABLE"
                    if seat_name in args.simulate_available:
                        status = "AVAILABLE"
                    current[seat_name] = status
                    logging.info("[%s] seat %-6s  %s", wl_name, seat_name, status)
                    print(f"{seat_name:<6}  {status:<12}  {stype:<12}  {tier}")

                changes = [
                    (seat_name, previous[seat_name], current[seat_name])
                    for seat_name in watch_seats
                    if seat_name in previous and previous[seat_name] != current.get(seat_name)
                ]
                if changes:
                    print("\nCHANGE DETECTED")
                    for seat_name, old, new in changes:
                        print(f"  {seat_name}: {old} -> {new}")
                        logging.info("CHANGE  [%s]  %s  %s -> %s", wl_name, seat_name, old, new)
                        if send_notification(url, seat_name, old, new, wl_name):
                            notifications_sent += 1
                            wl_notif_sent = True

            if watch_any_seats:
                newly_available = []
                available_now = []
                for seat_name in watch_any_seats:
                    seat = seat_map.get(seat_name)
                    if seat is None:
                        current[seat_name] = "NOT FOUND"
                        logging.info("[%s] watch_any %-6s  NOT FOUND", wl_name, seat_name)
                        continue
                    available = seat.get("available") is True
                    stype = seat.get("type", "")
                    status = "AVAILABLE" if available and stype in RESERVABLE_TYPES else "UNAVAILABLE"
                    if seat_name in args.simulate_available:
                        status = "AVAILABLE"
                    current[seat_name] = status
                    logging.info("[%s] watch_any %-6s  %s", wl_name, seat_name, status)
                    if status == "AVAILABLE":
                        available_now.append(seat_name)
                        if previous.get(seat_name) != "AVAILABLE":
                            newly_available.append(seat_name)

                if available_now:
                    print(f"\nwatch_any available: {' '.join(available_now)}")
                else:
                    print(f"\nwatch_any: 0 of {len(watch_any_seats)} seats available")

                if newly_available:
                    print(f"NEWLY AVAILABLE: {', '.join(newly_available)}")
                    logging.info("ANY-AVAILABLE  [%s]  %s", wl_name, ", ".join(newly_available))
                    if send_any_notification(url, wl_name, newly_available):
                        notifications_sent += 1
                        wl_notif_sent = True

            for adj_config in watch_adjacent_configs:
                rows = adj_config.get("rows", [])
                count = adj_config.get("count", 2)
                config_newly_available = []
                config_fully_available = []
                total_windows = 0

                for row in rows:
                    row_seats = []
                    for sn in seat_map:
                        m = re.match(r'^([A-Za-z]+)(\d+)$', sn)
                        if m and m.group(1).upper() == row.upper():
                            row_seats.append((int(m.group(2)), sn))
                    row_seats.sort()
                    seat_names = [s[1] for s in row_seats]

                    # TEMP DEBUG
                    debug_adj = (
                        DEBUG_ADJACENT_WATCHLIST is not None
                        and wl_name == DEBUG_ADJACENT_WATCHLIST
                        and row.upper() == "G"
                    )
                    if debug_adj:
                        print(f"\n[DEBUG] Row G: {len(seat_names)} seat(s) discovered")
                        for sn in seat_names:
                            s = seat_map.get(sn)
                            if s:
                                print(f"  {sn}  type={s.get('type', '?')}  available={s.get('available')}")
                            else:
                                print(f"  {sn}  NOT IN seat_map")
                        print(f"[DEBUG] Seat order: {', '.join(seat_names)}")

                    for i in range(len(seat_names) - count + 1):
                        window = seat_names[i:i + count]
                        state_key = "adj:" + "-".join(window)
                        display = "-".join(window)
                        total_windows += 1

                        all_avail = True
                        for sn in window:
                            seat = seat_map.get(sn)
                            if seat is None:
                                all_avail = False
                                break
                            avail = seat.get("available") is True and seat.get("type") in RESERVABLE_TYPES
                            if sn in args.simulate_available:
                                avail = True
                            if not avail:
                                all_avail = False
                                break

                        # TEMP DEBUG
                        if debug_adj:
                            if all_avail:
                                print(f"  Window {display} -> AVAILABLE")
                            else:
                                fail_detail = ""
                                for sn in window:
                                    s = seat_map.get(sn)
                                    if s is None:
                                        fail_detail = f"{sn} not in seat_map"
                                        break
                                    if not (s.get("available") is True and s.get("type") in RESERVABLE_TYPES):
                                        fail_detail = f"{sn} type={s.get('type', '?')} available={s.get('available')}"
                                        break
                                print(f"  Window {display} -> FAILED ({fail_detail})")

                        current[state_key] = "AVAILABLE" if all_avail else "UNAVAILABLE"
                        if all_avail:
                            logging.info("[%s] adjacent %s  AVAILABLE", wl_name, display)
                            config_fully_available.append(display)
                            if previous.get(state_key) != "AVAILABLE":
                                config_newly_available.append(display)

                if config_fully_available:
                    print(f"\nwatch_adjacent ({count}-seat): {len(config_fully_available)} window(s) available")
                    for w in config_fully_available:
                        print(f"  {w}")
                elif total_windows > 0:
                    print(f"\nwatch_adjacent ({count}-seat): 0 of {total_windows} windows fully available")

                if config_newly_available:
                    print(f"NEWLY AVAILABLE (adjacent): {', '.join(config_newly_available)}")
                    logging.info("ADJACENT-AVAILABLE  [%s]  count=%d  %s", wl_name, count, ", ".join(config_newly_available))
                    try:
                        logging.info("[DEBUG] calling send_adjacent_notification  notifications_sent_before=%d", notifications_sent)
                        print(f"[DEBUG] calling send_adjacent_notification  notifications_sent_before={notifications_sent}")
                        _notif_result = send_adjacent_notification(url, wl_name, config_newly_available, count)
                        logging.info("[DEBUG] send_adjacent_notification returned %s", _notif_result)
                        print(f"[DEBUG] send_adjacent_notification returned {_notif_result}")
                        if _notif_result:
                            notifications_sent += 1
                            wl_notif_sent = True
                            logging.info("[DEBUG] notifications_sent incremented to %d", notifications_sent)
                            print(f"[DEBUG] notifications_sent incremented to {notifications_sent}")
                    except Exception:
                        print("[DEBUG] EXCEPTION in notification block:")
                        traceback.print_exc()

            _seats_avail = sum(
                1 for k, v in current.items()
                if not k.startswith("adj:") and v == "AVAILABLE"
            )
            _adj_avail = sum(
                1 for k, v in current.items()
                if k.startswith("adj:") and v == "AVAILABLE"
            )
            wl_results.append(WatchlistResult(
                name=wl_name,
                enabled=True,
                showtime_url=url,
                watch_seats=watch_seats,
                watch_any=watch_any_seats,
                watch_adjacent=watch_adjacent_configs,
                status="success",
                seats_available=_seats_avail,
                adjacent_windows_available=_adj_avail,
                notification_sent=wl_notif_sent,
                failure_type=None,
                error_message=None,
            ))
            state[wl_name] = current
            processed += 1

        except Exception as exc:
            failure_type = classify_page_failure(html, exc)
            if failure_type == "CHALLENGE_PAGE":
                msg = f"page received ({len(html):,} chars) is too small for a valid seat map -- Cloudflare or rate-limit block"
                logging.warning("[%s] %s: %s", wl_name, failure_type, msg)
                failed_challenge += 1
            elif failure_type == "EXPIRED_URL":
                msg = f"full page received ({len(html):,} chars) but seatingLayout is absent -- showtime may be expired or URL is invalid"
                logging.warning("[%s] %s: %s", wl_name, failure_type, msg)
                failed_expired += 1
            elif failure_type == "PARSE_ERROR":
                msg = f"seatingLayout found but could not be parsed -- possible AMC page structure change; {exc}"
                logging.exception("[%s] %s: %s", wl_name, failure_type, msg)
                failed_parse += 1
            else:
                msg = str(exc)
                logging.exception("[%s] %s: %s", wl_name, failure_type, msg)
                failed_playwright += 1
            print(f"\n[{failure_type}] {wl_name}: {msg}")
            failed += 1
            wl_results.append(WatchlistResult(
                name=wl_name,
                enabled=True,
                showtime_url=wl.get("showtime_url", ""),
                watch_seats=wl.get("watch_seats", []),
                watch_any=wl.get("watch_any", []),
                watch_adjacent=wl.get("watch_adjacent", []),
                status="failed",
                seats_available=0,
                adjacent_windows_available=0,
                notification_sent=False,
                failure_type=failure_type,
                error_message=msg,
            ))

    save_state(state)
    completed_at = datetime.now(timezone.utc)

    duration = time.monotonic() - start_time
    unique_urls = len(html_cache)
    summary_lines = [
        "## Run Summary",
        f"Watchlists processed : {processed + skipped + failed}",
        f"  Enabled            : {processed}",
        f"  Disabled skipped   : {skipped}",
        f"  Failed             : {failed}",
    ]
    if failed > 0:
        summary_lines += [
            f"    Challenge/bot    : {failed_challenge}",
            f"    Expired URL      : {failed_expired}",
            f"    Parse error      : {failed_parse}",
            f"    Playwright error : {failed_playwright}",
        ]
    summary_lines += [
        f"Unique URLs          : {unique_urls}",
        f"Cache hits           : {cache_hits}",
        f"Cache misses         : {cache_misses}",
        f"Notifications sent   : {notifications_sent}",
        f"Duration             : {duration:.2f} sec",
    ]
    print()
    for line in summary_lines:
        print(line)
    logging.info(
        "RUN SUMMARY | processed=%d skipped=%d failed=%d challenge=%d expired=%d parse=%d playwright=%d unique_urls=%d cache_hits=%d cache_misses=%d notifications=%d duration=%.2fs",
        processed, skipped, failed,
        failed_challenge, failed_expired, failed_parse, failed_playwright,
        unique_urls, cache_hits, cache_misses, notifications_sent, duration,
    )

    if args.json_output:
        result = build_run_result(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            processed=processed,
            skipped=skipped,
            failed=failed,
            failed_challenge=failed_challenge,
            failed_expired=failed_expired,
            failed_parse=failed_parse,
            failed_playwright=failed_playwright,
            notifications_sent=notifications_sent,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            wl_results=wl_results,
        )
        write_json_output(args.json_output, result)


if __name__ == "__main__":
    main()
