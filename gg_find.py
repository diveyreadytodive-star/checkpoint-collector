import re, urllib.request, http.cookiejar
UA = {"User-Agent": "Mozilla/5.0"}
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def get(u):
    try: return op.open(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")
    except Exception as e: return f"ERR {e}"
for inf in ["EZOL8S376JX2S29VQIO332623372"]:
    for path in ["service/selectServicePage.do", "dataset/selectDatasetPage.do"]:
        p = get(f"https://data.gg.go.kr/portal/data/{path}?infId={inf}&infSeq=1")
        t = re.search(r"<title>(.*?)</title>", p, re.S)
        print(f"[gg] {path} len={len(p)} title={t.group(1).strip() if t else p[:120]!r}")
        for h in re.findall(r"<h[1-4][^>]*>([^<]{4,80})</h", p)[:6]: print("[gg]  h:", h.strip())
        for m in sorted(set(re.findall(r"(openapi\.gg\.go\.kr/[A-Za-z0-9]+)", p)))[:5]: print("[gg]  api:", m)
        for m in sorted(set(re.findall(r"(/portal/data/[a-zA-Z/]*[dD]own[a-zA-Z/]*\.do[^\"' ]*)", p)))[:8]: print("[gg]  down:", m)
        for m in sorted(set(re.findall(r"(fn\w*[Dd]own\w*)\(", p)))[:8]: print("[gg]  fn:", m)
        for m in re.findall(r"(fileSeq|fileNo|atchFileId)\W+['\"]?([A-Za-z0-9_-]+)", p)[:8]: print("[gg]  file:", m)
