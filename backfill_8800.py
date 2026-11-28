"""8800번 과거 데이터 백필 (국토부 재차인원 · 노선별 일 이용량)
기존 backfill2.py는 서울 용산구(순천향대병원 4개 정류장)만 받았다.
여기서는 승차가 일어나는 경기 수원 구간과 서울 하차 구간(중구·서초구)을 채운다.
  rte_id 41036043 (경기 routeId 200000205, 수원버스터미널 기점)
  기간 2026-07-01 ~ 2026-10-26 (국토부 확인된 최신 제공일)
→ data/hist/onboard_8800_<sgg>.csv, data/hist/route_daily_8800_<sgg>.csv
서비스별 하루 1,000건 한도 → API별 950건에서 멈춘다(최근 날짜부터 받음)."""
import os, json, csv, time, urllib.request, urllib.parse, datetime as dt

KEY = os.environ["GG_KEY"]
BASE = "https://apis.data.go.kr/1613000"
APIS = {
    "onboard": "NumberofOnBoardPassengersbyRoute/getNumberofOnBoardPassengersbyRoute",
    "route_daily": "TripVolumebyRoute/getDailyTripVolumebyRoute",
}
RID = "41036043"
START, END = dt.date(2026, 7, 1), dt.date(2026, 10, 26)
# (ctpv, sgg, 이름) — 수원 4개 구가 승차 구간, 중구·서초구는 서울 하차 구간
REGIONS = {
    "onboard": [("41", "41111", "수원 장안구"), ("41", "41113", "수원 권선구"),
                ("41", "41115", "수원 팔달구"), ("41", "41117", "수원 영통구"),
                ("11", "11140", "서울 중구"), ("11", "11650", "서울 서초구")],
    "route_daily": [("41", "41111", "수원 장안구"), ("41", "41113", "수원 권선구"),
                    ("41", "41115", "수원 팔달구"), ("41", "41117", "수원 영통구")],
}
LIMIT = 950
calls = {k: 0 for k in APIS}


def get(api, day, ctpv, sgg):
    q = {"serviceKey": KEY, "pageNo": 1, "numOfRows": 1000, "dataType": "JSON",
         "opr_ymd": day, "ctpv_cd": ctpv, "sgg_cd": sgg, "rte_id": RID}
    for t in range(3):
        try:
            calls[api] += 1
            with urllib.request.urlopen(f"{BASE}/{APIS[api]}?" + urllib.parse.urlencode(q), timeout=60) as r:
                j = json.loads(r.read().decode("utf-8", "replace"))
            b = (j.get("Response") or j.get("response") or {}).get("body") or {}
            it = b.get("items") or {}
            it = it.get("item", []) if isinstance(it, dict) else it
            return it if isinstance(it, list) else [it]
        except Exception as e:
            print(f"  재시도 {t + 1} {api} {sgg} {day}: {e}")
            time.sleep(5 * (t + 1))
    return []


os.makedirs("data/hist", exist_ok=True)
summary = {}
for api, regions in REGIONS.items():
    for ctpv, sgg, label in regions:
        path = f"data/hist/{api}_8800_{sgg}.csv"
        rows, d, empty_streak = [], END, 0
        while d >= START and calls[api] < LIMIT:
            got = [x for x in get(api, d.strftime("%Y%m%d"), ctpv, sgg) if x]
            rows += got
            # 이 구에 8800 정류장이 없으면 처음 7일 연속 빈 응답 → 다음 구로
            empty_streak = 0 if got else empty_streak + 1
            if not rows and empty_streak >= 7:
                print(f"[{api}] {label}: 최근 7일 응답 없음 → 건너뜀")
                break
            d -= dt.timedelta(days=1)
        if rows:
            fields = list(dict.fromkeys(k for r in rows for k in r))
            with open(path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                w.writeheader(); w.writerows(rows)
        days = len({r.get("opr_ymd") for r in rows})
        summary[f"{api}_{sgg}"] = {"label": label, "rows": len(rows), "days": days,
                                   "stops": len({r.get("sttn_id") for r in rows if r.get("sttn_id")})}
        print(f"[{api}] {label}: {len(rows)}행, {days}일 (호출 누계 {calls[api]})")

json.dump({"route": "8800", "rte_id": RID, "range": [START.isoformat(), END.isoformat()],
           "calls": calls, "files": summary},
          open("data/hist/backfill_8800_summary.json", "w"), ensure_ascii=False, indent=1)
print("호출 수:", calls)
