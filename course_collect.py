"""
CHECKPOINT 11팀 - 노선 전 구간(코스) 수집기  (주력 2 + 예비 3 노선)

주력
  - 8800   수원행 직행좌석   기준 정류소 102000070 순천향대학병원(한남동)        퇴근
  - 1112   수원 경희대↔강변역  기준 정류소 123000001 잠실역.잠실대교남단(중)     출근·퇴근
예비 (OSINT로 고른 혼잡 정류장)
  - 7770   수원역↔사당역      기준 정류소 121001315 사당역(중)                 퇴근
           근거: 서울시 - 사당역 과천방면 정류소 하루 3만 명, 퇴근 2만 명. 7770·7780·7790·7800 4개 노선에 집중
  - M5443  호매실↔강남역      기준 정류소 201000359 홈플러스서수원점            출근
           근거: 2022 경기일보 현장 보도 - 만석 무정차 통과
  - M5107  경희대↔서울역      (기준 정류소 없이 노선 전체만)                    퇴근
           근거: 명동입구 혼잡 대책으로 신설 광교 정류장으로 옮긴 수원 노선

정류소 ID와 노선 ID는 TAGO 기반 사이트(koreacharts)의 GGB 접두어를 뺀 값으로 추정한 것.
시작할 때 정류소 경유노선 API로 맞는지 자동 확인하고, 틀리면 그 정류소의 노선 목록을 보여준다.

무엇을 모으나
  1) 시작 1회: 노선 정류소 목록(순번·이름·좌표) → data/route_<노선>.csv
  2) 노선 위 모든 차량 위치 + 응답의 모든 필드 → data/course_<노선>_<날짜>.csv
     plateNo(차량번호)별로 시간순으로 이으면 "이 버스가 몇 시에 어느 정류소를 지났나"
  3) 기준 정류소 도착정보(remainSeatCnt 잔여좌석 공식 제공) → data/arrival_<노선>_<날짜>.csv

사용법
  export GG_KEY="공공데이터포털 일반 인증키(Decoding)"
  (활용신청: 경기도_버스도착정보 15080346, 버스위치정보 15080648, 버스노선 15080662, 정류소 15080666)
  python3 course_collect.py

하루 호출량 (개발계정 서비스별 1,000건/일)
  위치정보·도착정보 각각: 8800·1112 각 360(90초 간격, 9시간) + 7770 100 ≈ 820  → 테스트·재시도 여유 약 180
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

GG_KEY = os.environ.get("GG_KEY", "")
BASE = "https://apis.data.go.kr/6410000"

AM, PM = (6, 10), (16, 21)
TARGETS = [
    {"route": "8800", "station": "102000070", "label": "순천향대학병원(한남동)", "windows": [AM, PM], "every": 90},
    {"route": "1112", "station": "123000001", "label": "잠실역.잠실대교남단(중)", "windows": [AM, PM], "every": 90},
    {"route": "7770", "station": "121001315", "label": "사당역(중)", "routeId": "233000031", "windows": [PM], "every": 180},
    # 한도 때문에 꺼 둔 예비 노선 (주력이 실패하면 위 줄과 바꿔 쓰기)
    # {"route": "M5443", "station": "201000359", "label": "홈플러스서수원점", "routeId": "200000325", "windows": [AM], "every": 180},
    # {"route": "M5107", "station": None, "label": "노선 전체", "routeId": "234001243", "windows": [PM], "every": 180},
]

os.makedirs("data", exist_ok=True)


def call(path, **params):
    params.update({"serviceKey": GG_KEY, "format": "json"})
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8"))
    return (data.get("response") or {}).get("msgBody") or {}


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def append(path, rows):
    if not rows:
        return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    exists = os.path.exists(path)
    if exists:
        with open(path, encoding="utf-8") as f:
            header = next(csv.reader(f), [])
        if any(k not in header for k in keys):  # 새 필드가 생기면 다른 파일로
            path = path.replace(".csv", f"_{int(time.time())}.csv")
            exists = False
        else:
            keys = header
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerows(rows)


def resolve(t):
    if t.get("station"):
        routes = as_list(call("busstationservice/v2/getBusStationViaRouteListv2",
                              stationId=t["station"]).get("busRouteList"))
        hits = [r for r in routes if str(r.get("routeName")) == t["route"]]
        if not hits:
            names = sorted({str(r.get("routeName")) for r in routes})
            print(f"[!] {t['label']}({t['station']})에 {t['route']}번이 없음 → 이 노선은 건너뜀. "
                  f"이 정류소 노선: {names}", file=sys.stderr)
            return False
        r = hits[0]
        if t.get("routeId") and str(r["routeId"]) != t["routeId"]:
            print(f"[i] {t['route']} routeId 추정값 {t['routeId']} → 실제 {r['routeId']}로 교체")
        t["routeId"] = str(r["routeId"])
        t["staOrder"] = r.get("staOrder")
        print(f"[ok] {t['route']} @ {t['label']}: routeId={t['routeId']} 유형={r.get('routeTypeCd')} "
              f"방향끝={r.get('routeDestName')} 순번={t['staOrder']}")
    st = as_list(call("busrouteservice/v2/getBusRouteStationListv2",
                      routeId=t["routeId"]).get("busRouteStationList"))
    if not st:
        print(f"[!] {t['route']} routeId={t['routeId']} 정류소 목록이 비어 있음 → 건너뜀", file=sys.stderr)
        return False
    if os.path.exists(f"data/route_{t['route']}.csv"):
        os.remove(f"data/route_{t['route']}.csv")
    append(f"data/route_{t['route']}.csv", st)
    print(f"     정류소 {len(st)}개 → data/route_{t['route']}.csv")
    return True


def poll(t, now):
    stamp, day = now.isoformat(timespec="seconds"), f"{now:%Y%m%d}"
    n_loc = n_arr = 0
    try:
        loc = as_list(call("buslocationservice/v2/getBusLocationListv2",
                           routeId=t["routeId"]).get("busLocationList"))
        append(f"data/course_{t['route']}_{day}.csv", [dict(v, collected_at=stamp) for v in loc])
        n_loc = len(loc)
    except Exception as e:
        print(f"[loc] {t['route']} error: {e}", file=sys.stderr)
    if t.get("station"):
        try:
            arr = as_list(call("busarrivalservice/v2/getBusArrivalItemv2", stationId=t["station"],
                               routeId=t["routeId"], staOrder=t["staOrder"]).get("busArrivalItem"))
            append(f"data/arrival_{t['route']}_{day}.csv",
                   [dict(a, collected_at=stamp, stationId=t["station"]) for a in arr])
            n_arr = len(arr)
        except Exception as e:
            print(f"[arr] {t['route']} error: {e}", file=sys.stderr)
    print(f"[{now:%H:%M:%S}] {t['route']}: 차량 {n_loc}대, 도착정보 {n_arr}건")


def main():
    if not GG_KEY:
        sys.exit("GG_KEY 환경변수를 먼저 설정하세요.")
    active = [t for t in TARGETS if resolve(t)]
    if not active:
        sys.exit("수집할 노선이 없습니다.")
    sample = as_list(call("buslocationservice/v2/getBusLocationListv2",
                          routeId=active[0]["routeId"]).get("busLocationList"))
    print("[info] 위치정보 응답 필드:", sorted(sample[0].keys()) if sample else "지금 운행 차량 없음")
    last = {t["route"]: 0.0 for t in active}
    until = int(os.environ.get("RUN_UNTIL_HOUR", "99"))  # GitHub Actions: 이 시각(현지)에 종료
    while True:
        now = datetime.now()
        if now.hour >= until:
            print(f"[done] {now:%H:%M} 수집 종료")
            return
        for t in active:
            if any(s <= now.hour < e for s, e in t["windows"]) and time.time() - last[t["route"]] >= t["every"]:
                poll(t, now)
                last[t["route"]] = time.time()
        time.sleep(15)


if __name__ == "__main__":
    main()
