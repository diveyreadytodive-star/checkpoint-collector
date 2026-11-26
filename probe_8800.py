import os, json, urllib.request, urllib.parse, csv, glob
KEY = os.environ["GG_KEY"]; U = "https://apis.data.go.kr/1613000/NumberofOnBoardPassengersbyRoute/getNumberofOnBoardPassengersbyRoute"
ids = sorted({r["rte_id"] for f in glob.glob("data/hist/routes_41*.csv") for r in csv.DictReader(open(f)) if "수원버스터미널" in r["rte_nm"]})
print("[8800] 후보", ids)
for rid in ids:
    q = {"serviceKey": KEY, "pageNo": 1, "numOfRows": 300, "dataType": "JSON", "opr_ymd": "20261023", "ctpv_cd": "11", "sgg_cd": "11170", "rte_id": rid}
    try:
        with urllib.request.urlopen(U + "?" + urllib.parse.urlencode(q), timeout=40) as r: j = json.loads(r.read().decode())
        b = (j.get("Response") or j.get("response") or {}).get("body") or {}
        it = (b.get("items") or {}); it = it.get("item", []) if isinstance(it, dict) else it
        st = sorted({x.get("sttn_nm") for x in (it if isinstance(it, list) else [it]) if x})
        print(f"[8800] {rid} 용산구 {b.get('totalCount',0)}행 정류장 {st[:6]}")
    except Exception as e: print("[8800]", rid, e)
