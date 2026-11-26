"""서울 OA-12913 월별 CSV: 페이지의 frmFile 폼 값 + seq로 datafile 서버에 POST → data/seoul_ridership/"""
import os, re, urllib.request, urllib.parse, http.cookiejar, zipfile, io
UA = {"User-Agent": "Mozilla/5.0"}
cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
page = op.open(urllib.request.Request("https://data.seoul.go.kr/dataList/OA-12913/S/1/datasetView.do", headers=UA), timeout=60).read().decode("utf-8", "replace")
f = re.search(r'<form[^>]*name="frmFile".*?</form>', page, re.S).group(0)
fields = dict(re.findall(r'name="([^"]+)"\s+value="([^"]*)"', f))
for n in re.findall(r'name="([^"]+)"', f): fields.setdefault(n, "")
print("[seoulfile] frmFile", fields)
# 파일명 ↔ seq: downloadFile('115') 바로 앞의 파일명
pairs = {}
for m in re.finditer(r"downloadFile\('(\d+)'\)", page):
    seg = page[max(0, m.start()-1500):m.start()]
    nm = re.findall(r"(\d{4}년_버스노선별[^<\"']*?\.(?:csv|zip))", seg)
    if nm: pairs.setdefault(nm[-1], m.group(1))
print("[seoulfile] 목록 일부", list(pairs.items())[:5])
os.makedirs("data/seoul_ridership", exist_ok=True)
for fname, seq in pairs.items():
    if not re.search(r"(2026년.*\((09|10)월\)|2025년.*\(10월\))", fname): continue
    data = urllib.parse.urlencode({**fields, "seq": seq}).encode()
    r = op.open(urllib.request.Request("https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false", data=data,
                                       headers={**UA, "Referer": "https://data.seoul.go.kr/dataList/OA-12913/S/1/datasetView.do"}), timeout=600)
    body = r.read()
    print(f"[seoulfile] {fname} seq={seq}: {len(body)} bytes, 시작 {body[:40]!r}")
    if len(body) > 1_000_000:
        open(f"data/seoul_ridership/{fname}", "wb").write(body)
