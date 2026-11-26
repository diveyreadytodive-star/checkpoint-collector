"""서울 열린데이터광장 OA-12913(버스 정류장별 시간대별 승하차) 월별 CSV 내려받기
페이지 HTML에서 다운로드 파라미터(seq)를 찾아 datafile 서버로 요청 → data/seoul_ridership/"""
import os, re, urllib.request, urllib.parse, http.cookiejar
UA = {"User-Agent": "Mozilla/5.0"}
cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
page = op.open(urllib.request.Request("https://data.seoul.go.kr/dataList/OA-12913/S/1/datasetView.do", headers=UA), timeout=60).read().decode("utf-8", "replace")
os.makedirs("data/seoul_ridership", exist_ok=True)
calls = re.findall(r"downloadFile\(([^)]*)\)", page)
print("[seoulfile] downloadFile 호출", len(calls), calls[:6])
names = re.findall(r"(\d{4}년_버스노선별[^<\"']*?\.csv)", page)
print("[seoulfile] 파일명 예", names[:4])
for m in re.finditer(r"(fn_?[Dd]ownload\w*|download\w*)\(([^)]*)\)", page):
    pass
# 파일명과 seq 짝 찾기: downloadFile('seq') 형태를 가정, 파일명 순서와 맞춤
want = [("2026", "10"), ("2026", "09"), ("2025", "10")]
seqs = [re.sub(r"[^0-9]", "", c.split(",")[0]) for c in calls]
pairs = list(zip(names, seqs))
print("[seoulfile] 짝", pairs[:8])
for fname, seq in pairs:
    if not any(f"{y}년" in fname and f"({m}월)" in fname for y, m in want): continue
    data = urllib.parse.urlencode({"infId": "OA-12913", "seq": seq, "infSeq": "1"}).encode()
    for url in ["https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?useCache=false",
                "https://data.seoul.go.kr/dataList/dataView/fileDownload.do"]:
        try:
            r = op.open(urllib.request.Request(url, data=data, headers={**UA, "Referer": "https://data.seoul.go.kr/"}), timeout=300)
            body = r.read()
            print(f"[seoulfile] {fname} seq={seq} {url.split('/')[2]} → {len(body)} bytes, 시작 {body[:60]!r}")
            if len(body) > 1_000_000:
                open(f"data/seoul_ridership/{fname}", "wb").write(body); break
        except Exception as e:
            print(f"[seoulfile] {fname} {url.split('/')[2]} 실패: {e}")
