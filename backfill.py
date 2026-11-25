"""국토부 과거 데이터 백필 (재차인원·노선별 이용량)
# 실행: 이 파일이 바뀌어 push되면 backfill 워크플로가 돈다
1) 기준일 하루치를 시군구 전체로 받아 우리 노선 후보(rte_id)를 찾고
2) 그 rte_id만 지정해 최근 N일치를 받는다 → data/hist/<api>_<rte_id>.csv
서비스별 하루 1,000건 한도 안에서 동작하도록 페이지·일수를 제한."""
import os, json, csv, time, urllib.request, urllib.parse, datetime as dt
KEY = os.environ["GG_KEY"]; BASE = "https://apis.data.go.kr/1613000"
APIS = {"onboard": "NumberofOnBoardPassengersbyRoute/getNumberofOnBoardPassengersbyRoute",
        "route_daily": "TripVolumebyRoute/getDailyTripVolumebyRoute"}
LAST = dt.date(2026, 10, 26)            # 확인된 최신 제공일
DAYS = int(os.environ.get("DAYS", "28"))
REGIONS = [("41","41450","하남시"), ("41","41111","수원 장안구"), ("41","41113","수원 권선구"),
           ("41","41115","수원 팔달구"), ("41","41117","수원 영통구"), ("11","11170","서울 용산구")]
KEYWORDS = ["잠실역8번출구", "수서역", "감일", "순천향", "한남", "8800"]
calls = {k: 0 for k in APIS}
def call(api, page, **p):
    q = {"serviceKey": KEY, "pageNo": page, "numOfRows": 1000, "dataType": "JSON", **p}
    url = f"{BASE}/{APIS[api]}?" + urllib.parse.urlencode(q)
    for t in range(4):
        try:
            calls[api] += 1
            with urllib.request.urlopen(url, timeout=60) as r:
                j = json.loads(r.read().decode("utf-8", "replace"))
            R = j.get("Response") or j.get("response") or {}
            b = R.get("body") or {}; it = b.get("items") or {}
            it = it.get("item", []) if isinstance(it, dict) else it
            return (it if isinstance(it, list) else [it]), int(b.get("totalCount", 0) or 0)
        except Exception as e:
            print(f"  재시도 {t+1}: {e}"); time.sleep(5 * (t + 1))
    return [], 0
def fetch_all(api, maxpage=12, **p):
    rows, page = [], 1
    while page <= maxpage:
        items, tot = call(api, page, **p)
        rows += items
        if not items or len(rows) >= tot: break
        page += 1
    return rows
os.makedirs("data/hist", exist_ok=True)
# 1) 후보 노선 찾기
cands = {}
for ctpv, sgg, label in REGIONS:
    rows = fetch_all("route_daily", opr_ymd=LAST.strftime("%Y%m%d"), ctpv_cd=ctpv, sgg_cd=sgg)
    names = {(r.get("rte_id"), r.get("rte_nm")) for r in rows}
    hit = {rid: nm for rid, nm in names if any(k in str(nm) for k in KEYWORDS)}
    print(f"[{label}] 노선 {len(names)}개, 후보 {len(hit)}개: {list(hit.values())[:12]}")
    for rid, nm in hit.items(): cands[rid] = (ctpv, sgg, label, nm)
    with open(f"data/hist/routes_{sgg}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["rte_id", "rte_nm"]); w.writerows(sorted(names, key=lambda x: str(x[1])))
json.dump(cands, open("data/hist/candidates.json", "w"), ensure_ascii=False, indent=1)
# 2) 후보 노선 N일치
for api in APIS:
    for rid, (ctpv, sgg, label, nm) in cands.items():
        out, fields = [], None
        for d in range(DAYS):
            if calls[api] > 900: print(f"[{api}] 한도 보호로 중단"); break
            day = (LAST - dt.timedelta(days=d)).strftime("%Y%m%d")
            rows = fetch_all(api, maxpage=3, opr_ymd=day, ctpv_cd=ctpv, sgg_cd=sgg, rte_id=rid)
            out += rows
        if out:
            fields = list(out[0].keys())
            with open(f"data/hist/{api}_{rid}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(out)
        print(f"[{api}] {nm} ({label}, {rid}): {len(out)}행")
print("호출 수:", calls)
