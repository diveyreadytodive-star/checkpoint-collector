"""국토부 재차인원 장기 백필: 8800(순천향대병원, 용산구) + 35(하남·송파) — 2026-07-01 ~ 2026-10-26
→ data/hist/onboard_<노선>_<시군구>.csv (정류장×시간대 평균 재차인원, 일별)"""
import os, json, csv, time, urllib.request, urllib.parse, datetime as dt
KEY = os.environ["GG_KEY"]; U = "https://apis.data.go.kr/1613000/NumberofOnBoardPassengersbyRoute/getNumberofOnBoardPassengersbyRoute"
JOBS = [("8800", "41036043", "11", "11170"), ("35", "41079016", "41", "41450"), ("35", "41079016", "11", "11710")]
START, END = dt.date(2026, 7, 1), dt.date(2026, 10, 26)
calls = 0
def get(day, ctpv, sgg, rid):
    global calls
    q = {"serviceKey": KEY, "pageNo": 1, "numOfRows": 1000, "dataType": "JSON", "opr_ymd": day, "ctpv_cd": ctpv, "sgg_cd": sgg, "rte_id": rid}
    for t in range(3):
        try:
            calls += 1
            with urllib.request.urlopen(U + "?" + urllib.parse.urlencode(q), timeout=60) as r: j = json.loads(r.read().decode())
            b = (j.get("Response") or j.get("response") or {}).get("body") or {}
            it = b.get("items") or {}; it = it.get("item", []) if isinstance(it, dict) else it
            return it if isinstance(it, list) else [it]
        except Exception as e: time.sleep(5)
    return []
os.makedirs("data/hist", exist_ok=True)
for name, rid, ctpv, sgg in JOBS:
    path = f"data/hist/onboard_{name}_{sgg}.csv"; rows = []; d = END
    while d >= START and calls < 950:
        rows += get(d.strftime("%Y%m%d"), ctpv, sgg, rid); d -= dt.timedelta(days=1)
    if rows:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print(f"[backfill2] {name} {sgg}: {len(rows)}행, {len({r['opr_ymd'] for r in rows})}일 (호출 누계 {calls})")
