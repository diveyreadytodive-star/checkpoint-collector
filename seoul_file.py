import os, re, urllib.request, urllib.parse, http.cookiejar
UA = {"User-Agent": "Mozilla/5.0"}
cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
page = op.open(urllib.request.Request("https://data.seoul.go.kr/dataList/OA-12913/S/1/datasetView.do", headers=UA), timeout=60).read().decode("utf-8", "replace")
i = page.find("function downloadFile")
print("[seoulfile] 함수정의:", page[i:i+1200].replace("\n", " ") if i >= 0 else "페이지에 없음")
for m in re.findall(r'<script[^>]+src="([^"]+)"', page)[:40]:
    if "data" in m.lower() or "common" in m.lower() or "file" in m.lower(): print("[seoulfile] js", m)
k = page.find("downloadFile(")
print("[seoulfile] 호출 예:", page[k-300:k+120].replace("\n"," "))
data = urllib.parse.urlencode({"infId": "OA-12913", "seq": "115", "infSeq": "1"}).encode()
r = op.open(urllib.request.Request("https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?useCache=false", data=data, headers={**UA, "Referer": "https://data.seoul.go.kr/"}), timeout=60)
print("[seoulfile] 응답:", r.read().decode("utf-8","replace"))
