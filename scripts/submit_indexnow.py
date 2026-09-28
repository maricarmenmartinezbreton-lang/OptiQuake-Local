from __future__ import annotations
import json
import urllib.error
import urllib.request

HOST = "maricarmenmartinezbreton-lang.github.io"
BASE = "https://maricarmenmartinezbreton-lang.github.io/OptiQuake-Local/"
KEY = "optiquake-local-indexnow-20260928"
KEY_LOCATION = BASE + KEY + ".txt"

LANGS = [
    "en", "es", "pt", "fr", "de", "it", "ja", "ko",
    "zh-hans", "zh-hant", "ar", "hi", "ru", "tr", "id",
    "vi", "nl", "pl", "uk", "th", "bn", "fa", "he", "sw", "ms",
]

urls = [BASE, BASE + "languages.html"]
urls += [BASE + lang + ".html" for lang in LANGS]
urls += [BASE + "llms.txt", BASE + "sitemap.xml"]
payload = json.dumps({
    "host": HOST,
    "key": KEY,
    "keyLocation": KEY_LOCATION,
    "urlList": urls,
}).encode("utf-8")

request = urllib.request.Request(
    "https://api.indexnow.org/indexnow",
    data=payload,
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        code = response.getcode()
except urllib.error.HTTPError as exc:
    code = exc.code
    print(exc.read().decode("utf-8", errors="replace"))

print(f"INDEXNOW_HTTP={code}")
if code not in (200, 202):
    raise SystemExit(1)
