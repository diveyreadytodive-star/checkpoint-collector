"""정류장 단위 수집: 정류장 하나에 오는 '모든 노선'의 다음 버스 2대(빈자리·혼잡도·도착예정)를 한 번에
→ data/station_<라벨>_<날짜>.csv  (대체 루트 비교 + 고혼잡 노선 관찰)
도착정보 API 한도(1,000건/일)를 이 스크립트가 전부 씀: 정류장 수 × (창 길이 ÷ 주기) ≤ 약 900"""
import os, sys, csv, json, time, urllib.request, urllib.parse
from datetime import datetime
KEY = os.environ.get("GG_KEY", ""); B = "https://apis.data.go.kr/6410000"
AM, PM = (6, 10), (16, 21)
EVERY = 240
STATIONS = [
    # 출근: 하남 감일 → 서울 (35·87·38·9202·31·33·8 등 대체 루트 비교)
    {"label": "감일_마크베르4.5단지", "id": "227000647", "win": AM},
    {"label": "감일_마크베르5단지", "id": "227000344", "win": AM},
    {"label": "감일_역사공원제일풍경채", "id": "227000081", "win": AM},
    {"label": "감일_스윗시티1단지", "id": "227000333", "win": AM},
    # 8800 출근(서울행) 만석 구간: 11/26 실측 0석 비율 우만동4단지 60%, 경기대후문 58% (고속도로 진입 전 마지막 승차)
    {"label": "8800_우만동4단지", "id": "202000053", "win": AM},
    {"label": "8800_경기대수원캠퍼스후문", "id": "203000166", "win": AM},
    # 출근 고혼잡 노선 (OSINT): 하남 미사 3000(황산사거리 만차), 안성 4401
    {"label": "미사_황산사거리_3000", "kw": "황산사거리", "must": "3000", "dest": "금토천교", "win": AM},
    {"label": "안성_공도_4401", "kw": "공도", "must": "4401", "dest": "강남", "win": AM},
    # 퇴근: 서울 → 경기 (8800·5007·5500-2 / 1112·1007 / 7770 등)
    {"label": "한남_순천향대학병원", "id": "102000070", "win": PM},
    {"label": "잠실_잠실대교남단_경기행", "id": "123000002", "win": PM},
    {"label": "잠실_광역환승센터", "id": "123000611", "win": PM},
    # 8800 퇴근(수원행) 만석 구간: 명동성당 0석 17%, 순천향대병원 23% (11/26 실측)
    {"label": "8800_명동성당", "id": "101000001", "win": PM},
    {"label": "서울역환승센터6번", "id": "101000006", "win": PM},
]
def call(path, **p):
    url = f"{B}/{path}?" + urllib.parse.urlencode({"serviceKey": KEY, "format": "json", **p})
    for t in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: j = json.loads(r.read().decode())
            body = j.get("response", {}).get("msgBody") or {}
            for v in body.values(): return v if isinstance(v, list) else [v]
            return []
        except Exception as e:
            print("  재시도", e, file=sys.stderr); time.sleep(4)
    return []
def resolve(s):
    if s.get("id"): return True
    for st in call("busstationservice/v2/getBusStationListv2", keyword=s["kw"])[:15]:
        for r in call("busstationservice/v2/getBusStationViaRouteListv2", stationId=st["stationId"]):
            if str(r.get("routeName")) == s["must"] and s["dest"] in str(r.get("routeDestName")):
                s["id"] = str(st["stationId"]); print(f"[resolve] {s['label']} → {s['id']} {st.get('stationName')}"); return True
    print(f"[resolve] {s['label']}: 못 찾음 → 제외"); return False
def append(path, rows):
    if not rows: return
    new = not os.path.exists(path)
    keys = sorted({k for r in rows for k in r})
    if not new:
        with open(path) as f: keys = next(csv.reader(f))
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        if new: w.writeheader()
        w.writerows(rows)
def main():
    if not KEY: sys.exit("GG_KEY 필요")
    os.makedirs("data", exist_ok=True)
    act = [s for s in STATIONS if resolve(s)]
    if os.environ.get("DRY"):
        print("[dry] 정류장:", [(s["label"], s["id"]) for s in act])
        for s in act[:2]: print("  샘플", s["label"], [ (r.get("routeName"), r.get("remainSeatCnt1"), r.get("crowded1")) for r in call("busarrivalservice/v2/getBusArrivalListv2", stationId=s["id"])][:10])
        return
    json.dump({s["label"]: s["id"] for s in act}, open("data/station_ids.json", "w"), ensure_ascii=False, indent=1)
    until = int(os.environ.get("RUN_UNTIL_HOUR", "99"))
    deadline = time.time() + 60 * int(os.environ.get("MAX_MINUTES", "100000"))
    last = {s["label"]: 0.0 for s in act}
    while True:
        now = datetime.now()
        if now.hour >= until or time.time() > deadline: print("[done]"); return
        for s in act:
            a, b = s["win"]
            if a <= now.hour < b and time.time() - last[s["label"]] >= EVERY:
                rows = call("busarrivalservice/v2/getBusArrivalListv2", stationId=s["id"])
                stamp = now.isoformat(timespec="seconds")
                append(f"data/station_{s['label']}_{now:%Y%m%d}.csv", [dict(r, collected_at=stamp, stationId=s["id"]) for r in rows])
                last[s["label"]] = time.time()
                print(f"[{now:%H:%M}] {s['label']}: 노선 {len(rows)}개")
        time.sleep(10)
if __name__ == "__main__":
    main()
