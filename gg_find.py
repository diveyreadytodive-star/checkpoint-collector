"""15163060(경기 광역버스 승하차)의 실제 제공 경로 찾기: data.go.kr LINK → 경기데이터드림"""
import re, urllib.request, http.cookiejar
UA = {"User-Agent": "Mozilla/5.0"}
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def get(u):
    try: return op.open(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")
    except Exception as e: return f"ERR {e}"
p = get("https://www.data.go.kr/data/15163060/openapi.do")
for u in sorted(set(re.findall(r'https?://[^"\'\s<>]*gg\.go\.kr[^"\'\s<>]*', p)))[:20]: print("[gg] 링크", u)
for m in re.findall(r'(infId=[A-Z0-9]+)', p)[:5]: print("[gg] infId", m)
i = p.find("LINK"); print("[gg] LINK 주변", repr(p[i-400:i+400]) if i >= 0 else "-")
s = get("https://data.gg.go.kr/portal/data/dataset/searchDatasetPage.do?searchWord=%EA%B4%91%EC%97%AD%EB%B2%84%EC%8A%A4")
print("[gg] 드림 검색 길이", len(s))
for m in sorted(set(re.findall(r"infId=([A-Z0-9]+)[^\"']*", s)))[:20]: print("[gg] 검색 infId", m)
for t in re.findall(r'title="([^"]*승하차[^"]*)"', s)[:20]: print("[gg] 제목", t)
for m in re.finditer(r'([A-Z0-9]{20})[^<]{0,200}승하차', s): print("[gg] 후보", m.group(1))
