"""대안 경로 좌석제 노선 과거 데이터 백필 (국토부 재차인원 · 노선별 일 이용량)
대상: data/gg/seat_routes.json (TMAP 데모 경로의 좌석제 버스 구간 — 경기 routeId·정류장 목록 포함)
  3007 7001 2007 3102 1552 8501 6008 P9301 8202 4402 M4403
1) 국토부 rte_id 찾기 (한 번만, data/hist/seat_rte_ids.json 에 저장 → 다음 실행은 건너뜀)
   - 기점 시군구의 노선 목록(일 이용량 하루치, 없으면 받아 data/hist/routes_<sgg>.csv 저장)에서
     이름(기점-종점)이 경기 노선 기점·종점과 비슷한 후보 → 재차인원 1건씩 받아 정류장 이름 겹침이 가장 큰 것
   - 그 rte_id로 경유 시군구마다 1건씩 확인 → 행이 있는 시군구만 백필 대상
2) 최근 평일부터 거꾸로 재차인원(onboard)·일 이용량(route_daily)을 받는다 — 이미 받은 날은 건너뜀(이어받기)
   → data/hist/onboard_<노선>_<sgg>.csv, data/hist/route_daily_<노선>_<sgg>.csv, data/hist/backfill_seat_summary.json
한도: 서비스별 하루 1,000건 → API별 LIMIT(기본 900)에서 멈춤. 한도 초과 응답이 오면 바로 멈추고 저장.
남은 날은 다음 날 같은 명령으로 다시 실행하면 이어서 받는다:
  gh workflow run task.yml -R diveyreadytodive-star/checkpoint-collector -f script=backfill_seat.py"""
import os, re, json, csv, time, difflib, urllib.request, urllib.parse, datetime as dt

KEY = os.environ["GG_KEY"]
BASE = "https://apis.data.go.kr/1613000"
APIS = {"onboard": "NumberofOnBoardPassengersbyRoute/getNumberofOnBoardPassengersbyRoute",
        "route_daily": "TripVolumebyRoute/getDailyTripVolumebyRoute"}
START, END = dt.date(2026, 7, 1), dt.date(2026, 10, 26)   # 국토부 확인된 최신 제공일
PROBE_DAY = "20261021"                                     # 후보 확인용 평일
LIMIT = int(os.environ.get("LIMIT", "900"))
DEADLINE = time.time() + 60 * int(os.environ.get("MAX_MINUTES", "300"))   # 작업 시간 제한 전에 저장하고 끝낸다
WEEKDAYS_ONLY = os.environ.get("WEEKDAYS_ONLY", "1") == "1"
ONLY = [x for x in os.environ.get("ROUTES", "").split(",") if x]
# 경기 정류장 regionName → 국토부 시군구 코드 (서울 구간은 하차라 제외)
# 화성: 2026-02 일반구 신설로 41590 은 국토부 0건 → 41591·41593·41595·41597 도 탐색
SGG = {"수원": ["41111", "41113", "41115", "41117"], "화성": ["41590", "41591", "41593", "41595", "41597"], "오산": ["41370"], "의왕": ["41430"],
       "용인": ["41461", "41463", "41465"], "성남": ["41131", "41133", "41135"], "안산": ["41271", "41273"],
       "안성": ["41550"], "과천": ["41290"]}
calls = {k: 0 for k in APIS}
blocked = set()   # 한도 초과된 API


def call(api, page=1, rows=1000, **p):
    """(items, totalCount). 실패 ([], -1). 한도 초과면 blocked 에 넣고 ([], -1)"""
    if api in blocked or calls[api] >= LIMIT:
        return [], -1
    q = {"serviceKey": KEY, "pageNo": page, "numOfRows": rows, "dataType": "JSON", **p}
    for t in range(3):
        calls[api] += 1
        try:
            with urllib.request.urlopen(f"{BASE}/{APIS[api]}?" + urllib.parse.urlencode(q), timeout=60) as r:
                raw = r.read().decode("utf-8", "replace")
        except Exception as e:
            print(f"  재시도 {t + 1} {api}: {e}"); time.sleep(5 * (t + 1)); continue
        if "LIMITED_NUMBER_OF_SERVICE_REQUESTS" in raw or "<returnReasonCode>22<" in raw:
            print(f"[{api}] 일 한도 초과 → 중단"); blocked.add(api); return [], -1
        try:
            j = json.loads(raw)
        except ValueError:
            print(f"  재시도 {t + 1} {api}: JSON 아님 {raw[:120]!r}"); time.sleep(5); continue
        b = (j.get("Response") or j.get("response") or {}).get("body") or {}
        it = b.get("items") or {}
        it = it.get("item", []) if isinstance(it, dict) else it
        it = it if isinstance(it, list) else [it]
        return [x for x in it if x], int(b.get("totalCount", 0) or 0)
    return [], -1


def norm(s):
    return re.sub(r"\([^)]*\)?|[\s.·,\-]", "", str(s or ""))


def catalog(ctpv, sgg, fresh=False):
    path = f"data/hist/routes_{sgg}.csv"
    if os.path.exists(path) and not fresh:
        return {r["rte_id"]: r["rte_nm"] for r in csv.DictReader(open(path))}
    names, page = {}, 1
    while page <= 60:
        items, tot = call("route_daily", page, opr_ymd=PROBE_DAY, ctpv_cd=ctpv, sgg_cd=sgg)
        for r in items:
            names[r.get("rte_id")] = r.get("rte_nm")
        if not items or tot < 0 or page * 1000 >= tot:
            break
        page += 1
    if names and "route_daily" not in blocked:
        with open(path, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["rte_id", "rte_nm"]); w.writerows(sorted(names.items(), key=lambda x: str(x[1])))
    print(f"[catalog] {sgg}: 노선 {len(names)}개")
    return names


def sim(a, b):
    a, b = norm(a), norm(b)
    return difflib.SequenceMatcher(None, a, b).ratio() if a and b else 0.0


TAKEN = {"41036043"}   # 8800 (backfill_8800.py)


def resolve(no, r):
    """→ {"rte_id", "rte_nm", "overlap", "sggs": [[ctpv, sgg], ...]} 또는 None"""
    stops = r["stops"]
    gg_names = {norm(s["name"]) for s in stops}
    first_region = next((s["region"] for s in stops if s.get("region") in SGG), None)
    if not first_region:
        return None
    ends = [r.get("start"), r.get("end"), stops[0]["name"], stops[-1]["name"]]
    best = None
    def cands_in(sgg, fresh=False):
        out = []
        for rid, nm in catalog("41", sgg, fresh).items():
            score = max(sim(p, e) for p in str(nm).split("-") for e in ends if e)
            if score >= 0.6:
                out.append((score, rid, nm))
        return sorted(out, reverse=True)[:6]
    for sgg in SGG[first_region]:
        cands = cands_in(sgg)
        if not cands and os.path.exists(f"data/hist/routes_{sgg}.csv"):
            cands = cands_in(sgg, fresh=True)   # 예전 목록이 잘렸을 수 있다
        for score, rid, nm in cands:
            if rid in TAKEN:
                continue
            items, tot = call("onboard", rows=300, opr_ymd=PROBE_DAY, ctpv_cd="41", sgg_cd=sgg, rte_id=rid)
            names = {norm(x.get("sttn_nm")) for x in items}
            hit = len(names & gg_names)
            ov = hit / max(1, len(names))          # 국토부 정류장 중 경기 노선 정류장 비율
            fit = hit * ov                         # 많이 겹치고 남는 게 적을수록
            print(f"  [{no}] 후보 {rid} {nm} ({sgg}) 이름 {score:.2f} 겹침 {hit}/{len(names)}")
            if names and (not best or fit > best["fit"]):
                best = {"rte_id": rid, "rte_nm": nm, "overlap": round(ov, 2), "fit": round(fit, 2), "found_in": sgg}
        if best and best["overlap"] >= 0.8 and best["fit"] >= 5:
            break   # 충분히 확실하면 다른 구는 안 본다
    if not best or best["overlap"] < 0.4:
        return None
    sggs = []
    for region in dict.fromkeys(s.get("region") for s in stops):
        for sgg in SGG.get(region, []):
            if sgg == best["found_in"]:
                sggs.append(["41", sgg]); continue
            items, _ = call("onboard", rows=10, opr_ymd=PROBE_DAY, ctpv_cd="41", sgg_cd=sgg, rte_id=best["rte_id"])
            if items:
                sggs.append(["41", sgg])
    best["sggs"] = sggs
    return best


def days():
    d = END
    while d >= START:
        if not WEEKDAYS_ONLY or d.weekday() < 5:
            yield d.strftime("%Y%m%d")
        d -= dt.timedelta(days=1)


def load(path):
    return list(csv.DictReader(open(path))) if os.path.exists(path) else []


def save(path, rows):
    if not rows:
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)


os.makedirs("data/hist", exist_ok=True)
routes = json.load(open("data/gg/seat_routes.json"))
if ONLY:
    routes = {k: v for k, v in routes.items() if k in ONLY}
ids_path = "data/hist/seat_rte_ids.json"
ids = json.load(open(ids_path)) if os.path.exists(ids_path) else {}
TAKEN |= {v["rte_id"] for v in ids.values()}
for no, r in routes.items():
    if no in ids:
        continue
    got = resolve(no, r)
    print(f"[resolve] {no}: {got}", flush=True)
    if got:
        TAKEN.add(got["rte_id"])
        ids[no] = {"route_id": r["route_id"], **got}
        json.dump(ids, open(ids_path, "w"), ensure_ascii=False, indent=1)

# 백필: 노선·시군구를 번갈아 하루씩 → 한도에 걸려도 모든 노선이 비슷한 일수를 갖는다
jobs = [(no, c, s) for no in routes if no in ids for c, s in ids[no]["sggs"]]
store = {}
for api in APIS:
    for no, c, s in jobs:
        path = f"data/hist/{api}_{no}_{s}.csv"
        rows = load(path)
        store[(api, no, s)] = (path, rows, {x.get("opr_ymd") for x in rows})
stopped = None
for i, day in enumerate(days()):
    if all(api in blocked or calls[api] >= LIMIT for api in APIS):
        stopped = "한도"; break
    if time.time() > DEADLINE:
        stopped = "시간"; break
    if i and i % 5 == 0:   # 5일마다 중간 저장 (작업이 끊겨도 받은 만큼 남게)
        for path, rows, _ in store.values():
            save(path, rows)
        print(f"[backfill] {day}까지, 호출 {calls}", flush=True)
    for api in APIS:
        for no, c, s in jobs:
            path, rows, have = store[(api, no, s)]
            if day in have:
                continue
            page, got = 1, []
            while True:
                items, tot = call(api, page, opr_ymd=day, ctpv_cd=c, sgg_cd=s, rte_id=ids[no]["rte_id"])
                got += items
                if tot < 0 or not items or page * 1000 >= tot or page >= 5:
                    break
                page += 1
            if tot >= 0:   # 실패·한도면 그날은 다음 실행에서 다시
                rows += got; have.add(day)
for (api, no, s), (path, rows, have) in store.items():
    save(path, rows)

summary = {"range": [START.isoformat(), END.isoformat()], "weekdays_only": WEEKDAYS_ONLY, "calls": calls, "stopped": stopped,
           "blocked": sorted(blocked), "routes": {}}
for no, r in routes.items():
    info = ids.get(no)
    ent = {"gg_route_id": r["route_id"], "rte_id": info and info["rte_id"], "rte_nm": info and info["rte_nm"],
           "overlap": info and info["overlap"], "files": {}}
    for (api, n, s), (path, rows, have) in store.items():
        if n == no:
            ent["files"][os.path.basename(path)] = {
                "rows": len(rows), "days": len({x.get("opr_ymd") for x in rows}),
                "stops": len({x.get("sttn_id") for x in rows if x.get("sttn_id")}) or None}
    summary["routes"][no] = ent
    print(no, json.dumps(ent, ensure_ascii=False), flush=True)
json.dump(summary, open("data/hist/backfill_seat_summary.json", "w"), ensure_ascii=False, indent=1)
print("호출 수:", calls, "한도 초과:", sorted(blocked))
