"""대체 루트 탐색: 앵커(감일 마크베르, 한남 순천향대병원, 잠실) 반경 약 600m 정류장과 경유 노선 전부
→ data/alt/stations_<앵커>.csv, data/alt/routes_<앵커>.csv"""
import os, json, csv, math, time, urllib.request, urllib.parse
KEY = os.environ["GG_KEY"]; B = "https://apis.data.go.kr/6410000"
def get(path, **p):
    url = f"{B}/{path}?" + urllib.parse.urlencode({"serviceKey": KEY, "format": "json", **p})
    for t in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: j = json.loads(r.read().decode())
            body = j.get("response", {}).get("msgBody") or {}
            for v in body.values(): return v if isinstance(v, list) else [v]
            return []
        except Exception as e: print("  재시도", e); time.sleep(3)
    return []
def dist(x1, y1, x2, y2):
    return int(math.hypot((x1-x2)*88000, (y1-y2)*111000))
anchors = {}
for s in get("busstationservice/v2/getBusStationListv2", keyword="마크베르"):
    if str(s.get("stationId")) in ("227000647", "227000344"):
        anchors["gamil"] = (float(s["x"]), float(s["y"])); break
anchors["hannam"] = (127.0054333, 37.5359)
anchors["jamsil"] = (127.0984833, 37.51555)
print("앵커:", anchors)
os.makedirs("data/alt", exist_ok=True)
for name, (x0, y0) in anchors.items():
    seen = {}
    for dx, dy in [(0,0),(0.0045,0),(-0.0045,0),(0,0.0036),(0,-0.0036),(0.0032,0.0026),(-0.0032,0.0026),(0.0032,-0.0026),(-0.0032,-0.0026)]:
        for s in get("busstationservice/v2/getBusStationAroundListv2", x=x0+dx, y=y0+dy):
            sid = str(s.get("stationId"))
            if sid in seen: continue
            d = dist(float(s["x"]), float(s["y"]), x0, y0)
            if d <= 650: seen[sid] = {**s, "dist_m": d}
    st = sorted(seen.values(), key=lambda s: s["dist_m"])
    with open(f"data/alt/stations_{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["stationId","stationName","mobileNo","x","y","dist_m","regionName"])
        for s in st: w.writerow([s.get("stationId"), s.get("stationName"), s.get("mobileNo"), s.get("x"), s.get("y"), s["dist_m"], s.get("regionName")])
    rows = []
    for s in st:
        for r in get("busstationservice/v2/getBusStationViaRouteListv2", stationId=s["stationId"]):
            rows.append([s["stationId"], s.get("stationName"), s["dist_m"], r.get("routeName"), r.get("routeId"),
                         r.get("routeTypeCd"), r.get("routeTypeName"), r.get("staOrder"), r.get("routeDestName"), r.get("regionName")])
    with open(f"data/alt/routes_{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["stationId","stationName","dist_m","routeName","routeId","routeTypeCd","routeTypeName","staOrder","routeDestName","regionName"]); w.writerows(rows)
    print(f"[{name}] 정류장 {len(st)}개, 정류장-노선 {len(rows)}건, 노선 {len({r[3] for r in rows})}개")
