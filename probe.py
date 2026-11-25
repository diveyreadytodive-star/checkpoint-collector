"""국토부 3종 실호출 확인: 응답 필드와 샘플을 data/probe/에 저장"""
import os, json, urllib.request, urllib.parse, datetime as dt
KEY = os.environ["GG_KEY"]
BASE = "https://apis.data.go.kr/1613000"
APIS = {
  "15142063_onboard": "NumberofOnBoardPassengersbyRoute/getNumberofOnBoardPassengersbyRoute",
  "15142062_route_daily": "TripVolumebyRoute/getDailyTripVolumebyRoute",
  "15142065_stop_route_daily": "StopbyRouteTripVolume/getDailyStopbyRouteTripVolume",
}
today = dt.date.today()
DATES = [(today - dt.timedelta(days=d)).strftime("%Y%m%d") for d in (2, 7, 30, 90)] + ["20250801"]
# (시도, 시군구): 샘플(광주 서구), 수원시, 수원 장안구, 용인시, 서울 용산구, 서울 송파구
REGIONS = [("29","29140"),("41","41110"),("41","41111"),("41","41460"),("11","11170"),("11","11710")]
os.makedirs("data/probe", exist_ok=True)
def call(path, **p):
    q = {"serviceKey": KEY, "pageNo": 1, "numOfRows": 20, "dataType": "JSON", **p}
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(q)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return getattr(e, "code", -1), str(e)
summary = {}
for name, path in APIS.items():
    summary[name] = []
    for ctpv, sgg in REGIONS:
        for d in DATES:
            st, body = call(path, opr_ymd=d, ctpv_cd=ctpv, sgg_cd=sgg)
            items, fields = [], []
            try:
                j = json.loads(body)
                it = j.get("response", j).get("body", {}).get("items", {})
                it = it.get("item", it) if isinstance(it, dict) else it
                items = it if isinstance(it, list) else ([it] if it else [])
                fields = sorted(items[0].keys()) if items else []
            except Exception:
                pass
            rec = {"region": f"{ctpv}/{sgg}", "date": d, "http": st, "n": len(items), "fields": fields, "head": body[:300]}
            summary[name].append(rec)
            print(f"[{name}] {ctpv}/{sgg} {d} http={st} n={len(items)} fields={fields[:15]}")
            if items:
                json.dump(items, open(f"data/probe/{name}_{ctpv}_{sgg}_{d}.json","w"), ensure_ascii=False, indent=1)
                break
json.dump(summary, open("data/probe/summary.json","w"), ensure_ascii=False, indent=1)
