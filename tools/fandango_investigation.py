#!/usr/bin/env python3
"""
fandango_investigation.py
Read-only network investigation. Does NOT modify any AMCTracker files.

Captures all XHR/fetch/document network traffic while navigating through
Fandango to an AMC seat-selection page. Saves a structured JSON report.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_DIR = Path(__file__).parent
OUTPUT_FILE = BASE_DIR / "fandango_investigation_results.json"

# Keywords that suggest seat-map payload content
SEAT_KEYWORDS = [
    "seat", "seating", "layout", "availability", "showtime",
    "auditorium", "reservation", "booking", "ticket",
]

# Resource types to capture response bodies for
CAPTURE_TYPES = {"xhr", "fetch"}


def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return "unknown"


def sniff_body(body_bytes: bytes, content_type: str):
    """Return (is_json, body_parsed_or_None, body_text_preview)."""
    try:
        text = body_bytes.decode("utf-8", errors="replace")
    except Exception:
        return False, None, "(binary)"

    ct = content_type.lower()
    if "json" in ct or text.strip().startswith(("{", "[")):
        try:
            parsed = json.loads(text)
            return True, parsed, None
        except Exception:
            pass

    return False, None, text[:8000]


def body_mentions_seats(body_json, body_text: str) -> bool:
    target = json.dumps(body_json).lower() if body_json is not None else (body_text or "").lower()
    return any(kw in target for kw in SEAT_KEYWORDS)


def run():
    captured_requests: list[dict] = []
    captured_responses: list[dict] = []

    print("=" * 72)
    print("  FANDANGO / AMC SEAT-MAP NETWORK INVESTIGATION  (read-only)")
    print("=" * 72)
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--window-size=1440,900"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()

        # ── request listener ──────────────────────────────────────────────
        def on_request(req):
            captured_requests.append({
                "t": datetime.now().isoformat(),
                "method": req.method,
                "url": req.url,
                "resource_type": req.resource_type,
                "post_data": req.post_data,
                "headers": dict(req.headers),
            })
            if req.resource_type in CAPTURE_TYPES or "graphql" in req.url.lower():
                pd = f"  POST={req.post_data[:120]}" if req.post_data else ""
                print(f"  [XHR >] {req.method:<6} {req.url[:110]}{pd}")

        # ── response listener ─────────────────────────────────────────────
        def on_response(resp):
            rtype = resp.request.resource_type
            if rtype not in CAPTURE_TYPES and "graphql" not in resp.url.lower():
                return

            url = resp.url
            status = resp.status
            resp_headers = dict(resp.headers)
            content_type = resp_headers.get("content-type", "")

            is_json, body_parsed, body_text = False, None, None
            body_size = 0
            try:
                raw = resp.body()
                body_size = len(raw)
                is_json, body_parsed, body_text = sniff_body(raw, content_type)
            except Exception as exc:
                body_text = f"(error reading body: {exc})"

            entry = {
                "t": datetime.now().isoformat(),
                "method": resp.request.method,
                "url": url,
                "status": status,
                "content_type": content_type,
                "size_bytes": body_size,
                "resp_headers": resp_headers,
                "req_headers": dict(resp.request.headers),
                "post_data": resp.request.post_data,
                "is_json": is_json,
                "body_json": body_parsed,
                "body_text": body_text,
                "mentions_seats": body_mentions_seats(body_parsed, body_text or ""),
            }
            captured_responses.append(entry)

            tag = "[JSON]" if is_json else "[text]"
            seat_tag = " *** SEAT DATA ***" if entry["mentions_seats"] else ""
            print(f"  [RSP <] {status} {body_size:>9,}B {tag} {url[:95]}{seat_tag}")

        page.on("request", on_request)
        page.on("response", on_response)

        # ── navigate ──────────────────────────────────────────────────────
        print("Opening Fandango homepage...")
        print()
        try:
            page.goto("https://www.fandango.com", timeout=30_000)
            page.wait_for_load_state("networkidle", timeout=15_000)
        except PlaywrightTimeoutError:
            print("(networkidle timeout on homepage — continuing)")
        except Exception as exc:
            print(f"(goto error: {exc} — continuing)")

        print()
        print("-" * 72)
        print("Browser is open.  Steps:")
        print("  1. Find an AMC movie showtime on Fandango.")
        print("  2. Proceed to the seat-selection / seating-chart page.")
        print("  3. Wait for the seat map to fully render.")
        print()
        print("All XHR/fetch network traffic is being captured and logged above.")
        print()
        print("Press Enter here once the seat map has loaded completely.")
        print("-" * 72)
        input()

        browser.close()

    # ── analysis ─────────────────────────────────────────────────────────
    print()
    print("Analyzing captured traffic...")

    # Domain inventory
    domain_map: dict[str, list[dict]] = {}
    for r in captured_responses:
        d = extract_domain(r["url"])
        domain_map.setdefault(d, []).append(r)

    # Seat-bearing responses
    seat_responses = [r for r in captured_responses if r["mentions_seats"]]

    # All JSON API responses (GraphQL or otherwise)
    json_responses = [r for r in captured_responses if r["is_json"]]

    # GraphQL requests specifically
    graphql_responses = [r for r in captured_responses if "graphql" in r["url"].lower()]

    # Request auth header inventory (scrubbed — values redacted)
    auth_headers_seen: dict[str, set] = {}
    for r in captured_responses:
        for h, v in r["req_headers"].items():
            if h.lower() in (
                "authorization", "x-api-key", "x-auth-token", "x-fandango-clientid",
                "x-client-id", "x-session-token", "cookie",
            ):
                auth_headers_seen.setdefault(h.lower(), set()).add(
                    v[:8] + "..." if len(v) > 8 else v  # show only prefix for privacy
                )

    results = {
        "investigation_timestamp": datetime.now().isoformat(),
        "totals": {
            "requests_captured": len(captured_requests),
            "responses_captured": len(captured_responses),
            "json_api_responses": len(json_responses),
            "graphql_responses": len(graphql_responses),
            "seat_related_responses": len(seat_responses),
            "domains_contacted": len(domain_map),
        },
        "domains": {
            domain: {
                "response_count": len(resps),
                "json_responses": sum(1 for r in resps if r["is_json"]),
                "seat_related": sum(1 for r in resps if r["mentions_seats"]),
                "urls": sorted({r["url"] for r in resps})[:30],
            }
            for domain, resps in sorted(domain_map.items(), key=lambda x: -len(x[1]))
        },
        "auth_headers_observed": {k: sorted(v) for k, v in auth_headers_seen.items()},
        "seat_related_responses": [
            {
                "url": r["url"],
                "method": r["method"],
                "status": r["status"],
                "content_type": r["content_type"],
                "size_bytes": r["size_bytes"],
                "post_data": r["post_data"],
                "req_headers": r["req_headers"],
                "resp_headers": r["resp_headers"],
                "body_json": r["body_json"],
                "body_text_preview": (r.get("body_text") or "")[:3000],
            }
            for r in seat_responses
        ],
        "all_json_api_responses": [
            {
                "url": r["url"],
                "method": r["method"],
                "status": r["status"],
                "content_type": r["content_type"],
                "size_bytes": r["size_bytes"],
                "post_data": r["post_data"],
                "req_headers": r["req_headers"],
                "resp_headers": r["resp_headers"],
                "body_json": r["body_json"],
            }
            for r in json_responses
        ],
        "all_xhr_fetch_responses": [
            {
                "url": r["url"],
                "method": r["method"],
                "status": r["status"],
                "content_type": r["content_type"],
                "size_bytes": r["size_bytes"],
                "is_json": r["is_json"],
                "mentions_seats": r["mentions_seats"],
            }
            for r in captured_responses
        ],
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    # ── console summary ───────────────────────────────────────────────────
    t = results["totals"]
    print()
    print("=" * 72)
    print("  CAPTURE SUMMARY")
    print("=" * 72)
    print(f"  Total requests       : {t['requests_captured']}")
    print(f"  XHR/fetch responses  : {t['responses_captured']}")
    print(f"  JSON API responses   : {t['json_api_responses']}")
    print(f"  GraphQL responses    : {t['graphql_responses']}")
    print(f"  Seat-related         : {t['seat_related_responses']}")
    print(f"  Domains contacted    : {t['domains_contacted']}")
    print()
    print("  Domains (by response volume):")
    for domain, info in list(results["domains"].items())[:25]:
        seat_tag = "  [SEAT]" if info["seat_related"] else ""
        json_tag = f"  {info['json_responses']} JSON" if info["json_responses"] else ""
        print(f"    {domain:<52} {info['response_count']:>3} resp{json_tag}{seat_tag}")

    if results["auth_headers_observed"]:
        print()
        print("  Auth-related request headers observed:")
        for h, vals in results["auth_headers_observed"].items():
            print(f"    {h}: {', '.join(vals)}")

    print()
    print("  Seat-related responses:")
    if seat_responses:
        for r in seat_responses:
            print(f"    {r['method']:<6} {r['status']}  {r['size_bytes']:>9,}B  {r['url'][:80]}")
            if r["is_json"] and isinstance(r.get("body_json"), dict):
                top_keys = list(r["body_json"].keys())[:8]
                print(f"           JSON top-level keys: {top_keys}")
    else:
        print("    (none detected — may need manual keyword tuning in results JSON)")

    print()
    print(f"Full results saved to: {OUTPUT_FILE}")
    print()


if __name__ == "__main__":
    run()
