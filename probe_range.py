"""국토부 재차인원: 얼마나 과거까지 / 서울 구간도 되는지 확인 (35번 41079016)"""
import os, json, urllib.request, urllib.parse
KEY = os.environ["GG_KEY"]; U = "https://apis.data.go.kr/1613000/NumberofOnBoardPassengersbyRoute/getNumberofOnBoardPassengersbyRoute"
def n(ctpv, sgg, day, rid=None):
    q = {"serviceKey": KEY, "pageNo": 1, "numOfRows": 5, "dataType": "JSON", "opr_ymd": day, "ctpv_cd": ctpv, "sgg_cd": sgg}
    if rid: q["rte_id"] = rid
    try:
        with urllib.request.urlopen(U + "?" + urllib.parse.urlencode(q), timeout=40) as r: j = json.loads(r.read().decode())
        b = (j.get("Response") or j.get("response") or {}).get("body") or {}
        return b.get("totalCount", 0)
    except Exception as e: return f"err {e}"
for day in ["20261116", "20261105", "20261026", "20260901", "20260601", "20260115", "20250801", "20250115", "20240601"]:
    print(f"[range] 하남 35번 {day}: {n('41','41450',day,'41079016')}행")
for sgg, nm in [("11710","송파구"), ("11740","강동구")]:
    print(f"[seoul] 35번 {nm} 20261023: {n('11',sgg,'20261023','41079016')}행 / 전체 {n('11',sgg,'20261023')}행")
