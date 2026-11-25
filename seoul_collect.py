"""서울 실시간 지하철 도착 (SEOUL_KEY 있을 때만): 마크베르→삼성중앙역 환승역
→ data/subway_<역>_<날짜>.csv   (실시간 지하철 API, 1,000건/일 → 5역 × 120초 × 4시간 ≈ 600건)"""
import os, sys, csv, json, time, urllib.request, urllib.parse
from datetime import datetime
KEY = os.environ.get("SEOUL_KEY", "")
STATIONS = ["올림픽공원", "석촌", "종합운동장", "잠실", "가락시장"]   # 9호선 직결·환승 지점
AM = (6, 10); EVERY = 120
def fetch(name):
    url = f"http://swopenapi.seoul.go.kr/api/subway/{KEY}/json/realtimeStationArrival/0/40/{urllib.parse.quote(name)}"
    for t in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r: j = json.loads(r.read().decode())
            return j.get("realtimeArrivalList") or [], j.get("errorMessage", {})
        except Exception as e: print("재시도", e, file=sys.stderr); time.sleep(4)
    return [], {}
def main():
    if not KEY: print("[seoul] SEOUL_KEY 없음 → 건너뜀"); return
    rows, err = fetch(STATIONS[0]); print("[seoul] 연결 확인:", err, "필드:", sorted(rows[0].keys()) if rows else "-")
    if os.environ.get("DRY"): return
    until = int(os.environ.get("RUN_UNTIL_HOUR", "99")); deadline = time.time() + 60 * int(os.environ.get("MAX_MINUTES", "100000"))
    last = 0.0
    while True:
        now = datetime.now()
        if now.hour >= until or time.time() > deadline: return
        if AM[0] <= now.hour < AM[1] and time.time() - last >= EVERY:
            last = time.time()
            for st in STATIONS:
                rows, _ = fetch(st)
                if not rows: continue
                path = f"data/subway_{st}_{now:%Y%m%d}.csv"; new = not os.path.exists(path)
                keys = sorted({k for r in rows for k in r}) if new else next(csv.reader(open(path)))
                with open(path, "a", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=keys + (["collected_at"] if new else []), extrasaction="ignore")
                    if new: w.writeheader()
                    w.writerows([dict(r, collected_at=now.isoformat(timespec="seconds")) for r in rows])
        time.sleep(10)
if __name__ == "__main__": main()
