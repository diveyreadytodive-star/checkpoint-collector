"""국토부 3종 실호출: 필드 전체 + 우리 노선(8800·1112·7770)·정류장 행 추출 → data/probe/"""
import os, json, urllib.request, urllib.parse, time
KEY = os.environ["GG_KEY"]
BASE = "https://apis.data.go.kr/1613000"
APIS = {
  "onboard": "NumberofOnBoardPassengersbyRoute/getNumberofOnBoardPassengersbyRoute",
  "route_daily": "TripVolumebyRoute/getDailyTripVolumebyRoute",
  "stop_route_daily": "StopbyRouteTripVolume/getDailyStopbyRouteTripVolume",
}
DATE = os.environ.get("PROBE_DATE", "20261026")  # 최신 제공일(약 1개월 지연)
REGIONS = [("11","11170","용산구"),("11","11710","송파구"),("11","11650","서초구"),("41","41111","수원 장안구"),("41","41117","수원 영통구")]
KEYS = ["8800","1112","7770","순천향","잠실","사당"]
os.makedirs("data/probe", exist_ok=True)
def call(path, page, **p):
    q = {"serviceKey": KEY, "pageNo": page, "numOfRows": 1000, "dataType": "JSON", **p}
    for t in range(3):
        try:
            with urllib.request.urlopen(f"{BASE}/{path}?" + urllib.parse.urlencode(q), timeout=60) as r:
                j = json.loads(r.read().decode("utf-8","replace"))
            R = j.get("Response") or j.get("response") or {}
            if not R: return [], 0, json.dumps(j)[:200]
            b = R.get("body", {}); it = b.get("items") or {}
            it = it.get("item", []) if isinstance(it, dict) else it
            return (it if isinstance(it, list) else [it]), int(b.get("totalCount", 0) or 0), ""
        except Exception as e:
            err = str(e); time.sleep(3)
    return [], 0, err
report = {}
for name, path in APIS.items():
    rep = report[name] = {"fields": None, "regions": {}}
    for ctpv, sgg, label in REGIONS:
        rows, page, total = [], 1, None
        while page <= 15:
            items, tot, err = call(path, page, opr_ymd=DATE, ctpv_cd=ctpv, sgg_cd=sgg)
            if err: print(f"[{name}] {label} p{page} 오류: {err}"); break
            total = tot; rows += items
            if not items or len(rows) >= tot: break
            page += 1
        if rows and not rep["fields"]:
            rep["fields"] = list(rows[0].keys()); rep["sample"] = rows[0]
        hit = [r for r in rows if any(k in json.dumps(r, ensure_ascii=False) for k in KEYS)]
        rep["regions"][label] = {"total": total, "fetched": len(rows), "hits": len(hit)}
        print(f"[{name}] {label} {DATE}: 전체 {total}, 받음 {len(rows)}, 우리노선·정류장 {len(hit)}")
        if hit: json.dump(hit, open(f"data/probe/{name}_{sgg}_{DATE}.json","w"), ensure_ascii=False, indent=1)
    print(f"[{name}] 필드: {rep['fields']}")
json.dump(report, open("data/probe/summary.json","w"), ensure_ascii=False, indent=1)
