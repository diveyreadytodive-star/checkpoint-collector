"""
CHECKPOINT 11팀 - 해커톤 전 데이터 수집 스크립트 (경기 광역버스 잔여좌석 + 따릉이 재고)

사용법
  1) 키 발급
     - 공공데이터포털(data.go.kr): "경기도_버스도착정보 조회"(15080346) 활용신청 → 일반 인증키(Decoding)
     - 서울 열린데이터광장(data.seoul.go.kr): 인증키 신청 (따릉이 실시간 대여정보 OA-15493)
  2) 환경변수 설정
     export GG_KEY="공공데이터포털 Decoding 키"
     export SEOUL_KEY="열린데이터광장 키"
  3) 아래 BUS_TARGETS에 수집할 정류소 ID를 넣고 실행
     python3 collect.py bus     # 경기버스 잔여좌석 (출근 06~09시 / 퇴근 17~20시에만 호출)
     python3 collect.py bike    # 따릉이 전체 대여소 재고 스냅샷
     python3 collect.py both
  4) 노트북을 켜 두거나 서버에서 nohup / tmux로 계속 돌리면 data/*.csv 에 쌓입니다.

호출 한도 (개발계정 기준)
  - 경기 버스도착: 1,000건/일 → 정류소 3곳 × 1분 간격 × 6시간 = 1,080건이라 초과.
    POLL_SEC=90 (정류소 3곳이면 하루 약 720건) 정도로 잡으세요.
  - 따릉이: 1회 최대 1,000건이라 대여소 수만큼 페이지를 나눠 호출 (약 3천 개소 → 3~4회/스냅샷).

필드 출처
  - 경기 getBusArrivalListv2 응답 필드(remainSeatCnt1/2, crowded1/2, predictTimeSec1/2, locationNo1/2,
    plateNo1/2, lowPlate1/2, routeTypeCd)는 gbis.go.kr 공유서비스 매뉴얼 기준.
  - 따릉이 bikeList 필드명(rackTotCnt, parkingBikeTotCnt, shared 등)은 실제 첫 응답에서 꼭 확인하세요.
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
SEOUL_KEY = os.environ.get("SEOUL_KEY", "")

# 수집할 경기 정류소 ID (gbis.go.kr에서 정류소 검색 → stationId). 예시는 비워 둠.
BUS_TARGETS = [
    "102000070",   # 순천향대학병원 (서울 한남동, 퇴근 시 수원·용인·성남행 경기 직행좌석 정차) — GGB102000070에서 추정
]
# 비워 두면 정류소의 모든 노선을 저장. 특정 노선만 남기려면 노선번호를 넣으세요.
ROUTE_FILTER = ["8800"]   # 수원행
POLL_SEC = 90                 # 버스 폴링 간격(초)
BUS_WINDOWS = [(6, 9), (17, 20)]  # 수집 시간대 (시작시, 끝시)
BIKE_POLL_SEC = 600           # 따릉이 스냅샷 간격(초) - 공식 이력(OA-22382)은 1시간 단위라 더 촘촘히

GG_ARRIVAL = "https://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalListv2"
BIKE_URL = "http://openapi.seoul.go.kr:8088/{key}/json/bikeList/{start}/{end}/"

os.makedirs("data", exist_ok=True)


def get_json(url):
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def append_rows(path, fieldnames, rows):
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


# ---------------- 경기 광역버스 ----------------
BUS_FIELDS = [
    "collected_at", "stationId", "routeId", "routeName", "routeTypeCd", "staOrder", "flag",
    "plateNo1", "locationNo1", "predictTimeSec1", "remainSeatCnt1", "crowded1", "lowPlate1", "stateCd1",
    "plateNo2", "locationNo2", "predictTimeSec2", "remainSeatCnt2", "crowded2", "lowPlate2", "stateCd2",
]


def in_window(now):
    return any(s <= now.hour < e for s, e in BUS_WINDOWS)


def poll_bus_once():
    now = datetime.now()
    rows = []
    for sid in BUS_TARGETS:
        q = urllib.parse.urlencode({"serviceKey": GG_KEY, "stationId": sid, "format": "json"})
        try:
            data = get_json(f"{GG_ARRIVAL}?{q}")
            items = (data.get("response", {}).get("msgBody", {}) or {}).get("busArrivalList", [])
            if isinstance(items, dict):
                items = [items]
            for it in items:
                if ROUTE_FILTER and str(it.get("routeName")) not in ROUTE_FILTER:
                    continue
                it["collected_at"] = now.isoformat(timespec="seconds")
                it["stationId"] = sid
                rows.append(it)
        except Exception as e:  # 네트워크 오류는 기록만 하고 계속
            print(f"[bus] {sid} error: {e}", file=sys.stderr)
    if rows:
        append_rows(f"data/gg_bus_{now:%Y%m%d}.csv", BUS_FIELDS, rows)
    print(f"[bus] {now:%H:%M:%S} {len(rows)} rows")


# ---------------- 따릉이 ----------------
BIKE_FIELDS = ["collected_at", "stationId", "stationName", "rackTotCnt", "parkingBikeTotCnt",
               "shared", "stationLatitude", "stationLongitude"]


def poll_bike_once():
    now = datetime.now()
    rows, start = [], 1
    while True:
        url = BIKE_URL.format(key=SEOUL_KEY, start=start, end=start + 999)
        try:
            data = get_json(url)
        except Exception as e:
            print(f"[bike] error: {e}", file=sys.stderr)
            break
        items = (data.get("rentBikeStatus") or {}).get("row", [])
        for it in items:
            it["collected_at"] = now.isoformat(timespec="seconds")
        rows.extend(items)
        if len(items) < 1000:
            break
        start += 1000
    if rows:
        append_rows(f"data/bike_{now:%Y%m%d}.csv", BIKE_FIELDS, rows)
    print(f"[bike] {now:%H:%M:%S} {len(rows)} stations")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    if mode in ("bus", "both") and (not GG_KEY or not BUS_TARGETS):
        sys.exit("GG_KEY 환경변수와 BUS_TARGETS 정류소 ID를 먼저 채우세요.")
    if mode in ("bike", "both") and not SEOUL_KEY:
        sys.exit("SEOUL_KEY 환경변수를 먼저 설정하세요.")
    last_bike = 0.0
    until = int(os.environ.get("RUN_UNTIL_HOUR", "99"))  # GitHub Actions: 이 시각(현지)에 종료
    while True:
        now = datetime.now()
        if now.hour >= until:
            print(f"[done] {now:%H:%M} 수집 종료")
            return
        if mode in ("bus", "both") and in_window(now):
            poll_bus_once()
        if mode in ("bike", "both") and time.time() - last_bike >= BIKE_POLL_SEC:
            poll_bike_once()
            last_bike = time.time()
        time.sleep(POLL_SEC if mode != "bike" else 30)


if __name__ == "__main__":
    main()
