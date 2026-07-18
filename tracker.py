import argparse
import json
import logging
import os
import sys
from pathlib import Path

import requests

from playwright.sync_api import sync_playwright


WATCHLIST = Path(__file__).parent / "watchlist.json"
STATE_FILE = Path(__file__).parent / "state.json"
LOG_FILE = Path(__file__).parent / "tracker.log"


def load_watchlist():
    with open(WATCHLIST, encoding="utf-8") as f:
        data = json.load(f)
    url = data.get("showtime_url", "").strip()
    seats = data.get("watch_seats", [])
    if not url:
        print("ERROR: watchlist.json is missing 'showtime_url'")
        sys.exit(1)
    if not seats:
        print("ERROR: watchlist.json has no 'watch_seats'")
        sys.exit(1)
    return url, seats


def fetch_html(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=120_000)
        page.wait_for_timeout(8_000)
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


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def send_notification(showtime_url: str, name: str, old: str, new: str) -> None:
    user_key = os.environ.get("PUSHOVER_USER_KEY")
    api_token = os.environ.get("PUSHOVER_API_TOKEN")
    if not user_key or not api_token:
        return
    try:
        requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": api_token,
                "user": user_key,
                "title": "AMC Seat Alert",
                "message": f"{name}: {old} -> {new}\n{showtime_url}",
            },
            timeout=10,
        )
        logging.info("notification sent  %s  %s -> %s", name, old, new)
    except requests.RequestException:
        pass


def main():
    parser = argparse.ArgumentParser(description="AMC seat tracker")
    parser.add_argument("--debug", action="store_true", help="Save raw HTML to amc_seats.html")
    parser.add_argument("--simulate-available", metavar="SEAT", action="append", default=[], help="Override seat to AVAILABLE (testing only)")
    parser.add_argument("--test-notification", action="store_true", help="Send a test Pushover message and exit")
    args = parser.parse_args()

    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info("--- run started ---")

    if args.test_notification:
        user_key = os.environ.get("PUSHOVER_USER_KEY")
        api_token = os.environ.get("PUSHOVER_API_TOKEN")
        if not user_key or not api_token:
            print("ERROR: PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN must be set")
            sys.exit(1)
        send_notification("https://www.amctheatres.com", "TEST", "UNAVAILABLE", "AVAILABLE")
        print("Test notification sent.")
        return

    url, watch_seats = load_watchlist()

    print(f"Showtime : {url}")
    print(f"Watching : {', '.join(watch_seats)}")
    print("Loading page...")

    html = fetch_html(url)

    if args.debug:
        Path("amc_seats.html").write_text(html, encoding="utf-8")
        print(f"[debug] HTML saved ({len(html):,} chars)")

    layout = extract_seating_layout(html)
    all_seats = collect_seats(layout)
    seat_map = {s["name"]: s for s in all_seats if s.get("name")}

    previous = load_state()
    current = {}

    print(f"\n{'Seat':<6}  {'Status':<12}  {'Type':<12}  Tier")
    print("-" * 44)
    for name in watch_seats:
        seat = seat_map.get(name)
        if seat is None:
            print(f"{name:<6}  {'NOT FOUND':<12}")
            current[name] = "NOT FOUND"
            logging.info("seat %-6s  NOT FOUND", name)
            continue
        available = seat.get("available") is True
        stype = seat.get("type", "")
        tier = seat.get("seatTier", "")
        status = "AVAILABLE" if available and stype == "CanReserve" else "UNAVAILABLE"
        if name in args.simulate_available:
            status = "AVAILABLE"
        current[name] = status
        logging.info("seat %-6s  %s", name, status)
        print(f"{name:<6}  {status:<12}  {stype:<12}  {tier}")

    changes = [
        (name, previous[name], current[name])
        for name in watch_seats
        if name in previous and previous[name] != current.get(name)
    ]
    if changes:
        print("\nCHANGE DETECTED")
        for name, old, new in changes:
            print(f"  {name}: {old} -> {new}")
            logging.info("CHANGE  %s  %s -> %s", name, old, new)
            send_notification(url, name, old, new)

    save_state(current)


if __name__ == "__main__":
    main()
