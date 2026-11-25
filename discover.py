"""감일 '마크베르' 정류장과 35·87·38번 노선 찾기 → data/discover_gamil.json"""
import os, json, urllib.request, urllib.parse
KEY = os.environ["GG_KEY"]; B = "https://apis.data.go.kr/6410000"
def get(path, **p):
    url = f"{B}/{path}?" + urllib.parse.urlencode({"serviceKey": KEY, "format": "json", **p})
    with urllib.request.urlopen(url, timeout=30) as r:
        j = json.loads(r.read().decode())
    body = j.get("response", {}).get("msgBody") or {}
    for v in body.values():
        return v if isinstance(v, list) else [v]
    print("응답:", json.dumps(j, ensure_ascii=False)[:300]); return []
out = {}
for kw in ["마크베르", "감일"]:
    st = get("busstationservice/v2/getBusStationListv2", keyword=kw)
    print(f"[{kw}] 정류소 {len(st)}개")
    for s in st:
        sid = s.get("stationId"); nm = s.get("stationName")
        routes = get("busstationservice/v2/getBusStationViaRouteListv2", stationId=sid)
        rs = [(r.get("routeName"), r.get("routeId"), r.get("routeTypeCd"), r.get("staOrder"), r.get("routeDestName")) for r in routes]
        out[f"{sid} {nm} ({s.get('mobileNo')})"] = rs
        hit = [r for r in rs if str(r[0]) in ("35","87","38")]
        print(f"  {sid} {nm} mobileNo={s.get('mobileNo')} x={s.get('x')} y={s.get('y')} | 35/87/38: {hit}")
os.makedirs("data", exist_ok=True)
json.dump(out, open("data/discover_gamil.json","w"), ensure_ascii=False, indent=1)
