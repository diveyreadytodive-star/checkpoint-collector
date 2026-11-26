"""서울 버스 도착정보(data.go.kr 15000314, GG_KEY 사용): 서울 시내·서울면허 광역버스의 재차인원·혼잡·만차
정류장 이름으로 arsId를 찾고 getStationByUid로 정류장 전 노선 수집 → data/seoulbus_<라벨>_<날짜>.csv"""
import os, sys, csv, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime
KEY = os.environ.get("GG_KEY", ""); B = "http://ws.bus.go.kr/api/rest"
AM, PM = (6, 10), (16, 21); EVERY = 300
TARGETS = [("올림픽공원", "올림픽공원", AM), ("석촌역", "석촌역", AM), ("가락시장", "가락시장", AM), ("잠실역", "잠실역", AM),
           ("순천향대학병원", "순천향대학병원", PM), ("잠실역_퇴근", "잠실역", PM)]
def get(path, **p):
    url = f"{B}/{path}?" + urllib.parse.urlencode({"serviceKey": KEY, **p})
    for t in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r: root = ET.fromstring(r.read())
            head = root.find("msgHeader")
            items = [{c.tag: (c.text or "") for c in it} for it in root.iter("itemList")]
            return items, (head.findtext("headerMsg") if head is not None else "")
        except Exception as e: print("재시도", e, file=sys.stderr); time.sleep(4)
    return [], "error"
def main():
    if not KEY: return
    ars = {}
    for label, name, win in TARGETS:
        items, msg = get("stationinfo/getStationByName", stSrch=name)
        ids = sorted({i.get("arsId") for i in items if i.get("arsId") and i.get("arsId") != "0"})[:3]  # 같은 이름 정류장(방향) 최대 3개
        print(f"[seoulbus] {label}: {msg} arsId={ids}")
        if ids: ars[label] = (ids, win)
    if os.environ.get("DRY") or not ars: return
    until = int(os.environ.get("RUN_UNTIL_HOUR", "99")); deadline = time.time() + 60 * int(os.environ.get("MAX_MINUTES", "100000"))
    last = {k: 0.0 for k in ars}
    while True:
        now = datetime.now()
        if now.hour >= until or time.time() > deadline: return
        for label, (ids, (a, b)) in ars.items():
            if a <= now.hour < b and time.time() - last[label] >= EVERY:
                last[label] = time.time()
                for aid in ids:
                    items, _ = get("stationinfo/getStationByUid", arsId=aid)
                    if not items: continue
                    path = f"data/seoulbus_{label}_{now:%Y%m%d}.csv"; new = not os.path.exists(path)
                    keys = sorted({k for i in items for k in i}) + ["collected_at"] if new else next(csv.reader(open(path)))
                    with open(path, "a", newline="") as f:
                        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
                        if new: w.writeheader()
                        w.writerows([dict(i, collected_at=now.isoformat(timespec="seconds")) for i in items])
        time.sleep(10)
if __name__ == "__main__": main()
