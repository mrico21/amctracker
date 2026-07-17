import json
import sys

with open("amc_seats.html", encoding="utf-8") as f:
    html = f.read()

marker = '\\"seatingLayout\\"'
idx = html.find(marker)
if idx == -1:
    print("seatingLayout not found")
    sys.exit(1)

print("Marker found at index:", idx)

colon_pos = html.find(":", idx + len(marker))
start = html.find("{", colon_pos)
if start == -1:
    print("Opening brace not found")
    sys.exit(1)

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

json_str = html[start : end + 1]
json_str = json_str.replace('\\"', '"')

try:
    layout = json.loads(json_str)
except json.JSONDecodeError as e:
    print("Parse failed:", e)
    sys.exit(1)

seats = layout.get("seats", [])

print("columns:", layout.get("columns"))
print("rows:", layout.get("rows"))
print("total seat objects:", len(seats))
print("available seats:", sum(1 for s in seats if s.get("available") is True))
print("CanReserve seats:", sum(1 for s in seats if s.get("type") == "CanReserve"))
print("")
print("First 10 seat records:")
for s in seats[:10]:
    print(" ", s)

print("")
print("Seat lookup:")
lookup = ["A29", "A28", "A27", "J15", "J16"]
seat_map = {s.get("name"): s for s in seats}
for name in lookup:
    seat = seat_map.get(name)
    if seat is None:
        print(f"  {name}: NOT FOUND in layout")
    else:
        available = seat.get("available")
        stype = seat.get("type")
        status = "AVAILABLE" if available is True and stype == "CanReserve" else "UNAVAILABLE"
        print(f"  {name}: {status}  (available={available}, type={stype})")
