import re, time, urllib.request, http.cookiejar, os
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36", "Accept-Language": "ko-KR,ko"}
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def get(u, t=180):
    for k in range(3):
        try: return op.open(urllib.request.Request(u, headers=UA), timeout=t).read().decode("utf-8", "replace")
        except Exception as e: print("[gg] 재시도", k, e); time.sleep(5)
    return ""
inf = "EZOL8S376JX2S29VQIO332623372"
p = get(f"https://data.gg.go.kr/portal/data/service/selectServicePage.do?infId={inf}&infSeq=1")
os.makedirs("data/gg", exist_ok=True); open("data/gg/page.html", "w").write(p)
t = re.search(r"<title>(.*?)</title>", p, re.S); print("[gg] title", t.group(1).strip() if t else len(p))
for m in sorted(set(re.findall(r"openapi\.gg\.go\.kr/([A-Za-z0-9]+)", p))): print("[gg] api", m)
for m in sorted(set(re.findall(r"([A-Za-z]*[Ff]ile[A-Za-z]*\([^)]{0,80}\))", p)))[:15]: print("[gg] fileFn", m)
for m in sorted(set(re.findall(r'(/portal/[^"\']*(?:[Dd]own|[Ff]ile)[^"\']*)', p)))[:15]: print("[gg] url", m)
for m in re.findall(r"(\d{6}[^<]{0,40}\.(?:csv|xlsx|zip))", p)[:20]: print("[gg] 파일", m)
