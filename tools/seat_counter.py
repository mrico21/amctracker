#!/usr/bin/env python3
"""
seat_counter.py — Count available reservable seats on an AMC showtime page.

Usage:
    python seat_counter.py <AMC-seat-page-URL>
"""

import json
import sys

import requests


# Seat types to exclude from the count
EXCLUDED_TYPES = {"Wheelchair", "Companion", "NotASeat"}


def fetch_page(url: str) -> str:
    """Download the AMC seat page HTML."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.text


def extract_seating_layout(html: str) -> dict:
    """
    Locate and parse the seatingLayout JSON object embedded in the page source.

    AMC uses Next.js with React Server Components. Seat data arrives in one of
    two forms depending on how the page is rendered:

      1. Plain JSON inside a <script id="__NEXT_DATA__"> tag:
             "seatingLayout": { ... }

      2. Escaped JSON inside a self.__next_f.push() RSC payload string:
             \"seatingLayout\":{\"rows\":[...]}
         Here every " in the JSON is escaped as \" because the whole object is
         embedded as a value inside a JavaScript string literal.

    Strategy: search for the key in all known forms, extract the object via
    brace-balancing, then try json.loads directly; if that fails, unescape the
    backslash-quoted characters and try once more.
    """
    # Marker forms, most-specific first.
    # '\\"seatingLayout\\"' matches the literal bytes \"seatingLayout\" that
    # appear when the JSON is embedded inside a JS string (Next.js RSC payload).
    for marker in ('"seatingLayout"', '\\"seatingLayout\\"', "'seatingLayout'", "seatingLayout"):
        idx = html.find(marker)
        if idx != -1:
            break
    else:
        raise ValueError("seatingLayout not found in page source.")

    # Find the colon separating the key from the value, then the opening brace
    colon_pos = html.find(":", idx + len(marker))
    start = html.find("{", colon_pos)
    if start == -1:
        raise ValueError("Could not locate seatingLayout object body.")

    # Walk forward, counting braces to find the matching closing brace.
    # Brace-balancing works even inside an escaped JS string because { and }
    # do not need escaping in JSON string values, so they appear as literal
    # characters in the HTML source.
    depth = 0
    end = start
    for i in range(start, len(html)):
        if html[i] == "{":
            depth += 1
        elif html[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    else:
        raise ValueError("seatingLayout object brace is never closed.")

    json_str = html[start : end + 1]

    # Case 1: plain JSON context — parse directly
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Case 2: extracted from inside a JS string — quotes are escaped as \"
    # Replace \" with " to restore valid JSON, then parse
    try:
        return json.loads(json_str.replace('\\"', '"'))
    except json.JSONDecodeError as exc:
        raise ValueError(f"seatingLayout found but could not be parsed: {exc}") from exc


def find_all_seats(data) -> list:
    """
    Recursively collect every seat-like object from the layout structure.

    Handles both flat seat arrays and nested row/seat structures.
    A seat object is identified by having 'available', 'type', and 'name' fields.
    """
    seats = []
    if isinstance(data, dict):
        if {"available", "type", "name"}.issubset(data.keys()):
            seats.append(data)
        else:
            for value in data.values():
                seats.extend(find_all_seats(value))
    elif isinstance(data, list):
        for item in data:
            seats.extend(find_all_seats(item))
    return seats


def count_available_seats(layout: dict) -> int:
    """
    Return the number of seats that are available and reservable.

    A seat qualifies when:
      - available is True
      - type is "CanReserve"
      - type is not Wheelchair, Companion, or NotASeat
    """
    seats = find_all_seats(layout)
    return sum(
        1
        for seat in seats
        if seat.get("available") is True
        and seat.get("type") == "CanReserve"
        and seat.get("type") not in EXCLUDED_TYPES
    )


def main():
    if len(sys.argv) != 2:
        print("Usage: python seat_counter.py <AMC-seat-page-URL>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Fetching: {url}")

    html = fetch_page(url)
    layout = extract_seating_layout(html)
    count = count_available_seats(layout)

    print(f"Available seats: {count}")


if __name__ == "__main__":
    main()
