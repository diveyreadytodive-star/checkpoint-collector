"""마크베르(감일) → 삼성중앙역: 주변 정류장(650m) 노선별로 경로를 펼쳐
① 삼성중앙역 최근접 정류장/거리 ② 경유하는 환승역 ③ 탑승 정류장→하차 후보 정류장 수 를 계산 → data/alt/options_samsungjungang.csv"""
import os, csv, json, math, time, urllib.request, urllib.parse
KEY = os.environ["GG_KEY"]; B = "https://apis.data.go.kr/6410000"
DEST = (127.0532, 37.5131)  # 삼성중앙역(9호선)
HUBS = {"잠실": (127.1000, 37.5133), "종합운동장": (127.0736, 37.5110), "삼성역": (127.0631, 37.5089), "봉은사": (127.0601, 37.5145),
        "선정릉": (127.0435, 37.5103), "수서": (127.1017, 37.4873), "복정": (127.1269, 37.4706), "가락시장": (127.1182, 37.4925),
        "둔촌동": (127.1361, 37.5277), "올림픽공원": (127.1306, 37.5163), "학동": (127.0317, 37.5142), "석촌": (127.1066, 37.5054), "잠실새내": (127.0866, 37.5115)}
def get(path, **p):
    url = f"{B}/{path}?" + urllib.parse.urlencode({"serviceKey": KEY, "format": "json", **p})
    for t in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: j = json.loads(r.read().decode())
            body = j.get("response", {}).get("msgBody") or {}
            for v in body.values(): return v if isinstance(v, list) else [v]
            return []
        except Exception as e: print("재시도", e); time.sleep(4)
    return []
def d(a, b): return int(math.hypot((a[0]-b[0])*88000, (a[1]-b[1])*111000))
rows = list(csv.DictReader(open("data/alt/routes_gamil.csv")))
seen, out = set(), []
for r in rows:
    if r["routeId"] in seen: continue
    seen.add(r["routeId"])
    st = get("busrouteservice/v2/getBusRouteStationListv2", routeId=r["routeId"])
    if not st: continue
    seqs = {s["stationId"]: i for i, s in enumerate(st)}
    board = [x for x in rows if x["routeId"] == r["routeId"]]
    for b in board:
        i0 = seqs.get(int(b["stationId"])) if int(b["stationId"]) in seqs else seqs.get(b["stationId"])
        if i0 is None: continue
        rest = st[i0+1:]
        # 회차 전까지만(같은 방향): turnYn 이후는 되돌아오는 구간
        best = min(rest, key=lambda s: d((float(s["x"]), float(s["y"])), DEST), default=None)
        if not best: continue
        bd = d((float(best["x"]), float(best["y"])), DEST)
        hubs = []
        for s in rest:
            p = (float(s["x"]), float(s["y"]))
            for h, hp in HUBS.items():
                if d(p, hp) < 300 and h not in [x[0] for x in hubs]: hubs.append((h, rest.index(s) + 1))
        out.append({"routeName": r["routeName"], "routeId": r["routeId"], "routeTypeCd": r["routeTypeCd"],
                    "board_station": b["stationName"], "board_id": b["stationId"], "walk_from_markverre_m": b["dist_m"],
                    "dest_dir": b["routeDestName"], "nearest_to_dest": best["stationName"], "nearest_dist_m": bd,
                    "stops_to_nearest": rest.index(best) + 1,
                    "hubs": " / ".join(f"{h}({n}정거장)" for h, n in hubs)})
out.sort(key=lambda x: (x["nearest_dist_m"], x["stops_to_nearest"]))
os.makedirs("data/alt", exist_ok=True)
with open("data/alt/options_samsungjungang.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
for o in out[:40]:
    print(f"{o['routeName']:>8} @{o['board_station'][:14]}({o['walk_from_markverre_m']}m) → {o['nearest_to_dest'][:14]} {o['nearest_dist_m']}m/{o['stops_to_nearest']}정거장 | {o['hubs'][:80]}")
