from playwright.sync_api import sync_playwright

URL = "https://www.amctheatres.com/showtimes/143822631/seats"
OUTPUT = "amc_seats.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(URL, timeout=120000)
    page.wait_for_timeout(15000)

    html = page.content()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved", len(html), "chars to", OUTPUT)

    for term in ["seatingLayout", "CanReserve", "available"]:
        print(term + ":", "FOUND" if term in html else "NOT FOUND")

    browser.close()
