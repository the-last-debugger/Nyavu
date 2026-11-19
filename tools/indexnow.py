"""Tell the search engines that the pages changed.

Bing, Yandex, Seznam and Naver share IndexNow: one POST announces every URL, and the key is verified by
fetching it from the site root. Google does not take part; it still discovers pages through the sitemap,
which Search Console has to be told about once.

    python tools/indexnow.py [origin]
"""
import json
import sys
import urllib.request

DEFAULT_ORIGIN = "https://nyavu.onrender.com"
KEY = "nyavu2026indexnow"
PAGES = ["/", "/learn/is-this-link-safe", "/learn/how-phishing-works", "/about"]
ENDPOINTS = ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]


def announce(origin: str) -> int:
    host = origin.split("://", 1)[-1].rstrip("/")
    body = json.dumps({
        "host": host,
        "key": KEY,
        "keyLocation": f"{origin}/{KEY}.txt",
        "urlList": [origin + path for path in PAGES],
    }).encode()
    failures = 0
    for endpoint in ENDPOINTS:
        request = urllib.request.Request(endpoint, data=body,
                                         headers={"Content-Type": "application/json; charset=utf-8",
                                                  "User-Agent": "Nyavu/1.0 (+%s)" % origin})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                print(f"{endpoint}: {response.status}")
        except Exception as error:
            failures += 1
            print(f"{endpoint}: {error}")
    return failures


if __name__ == "__main__":
    origin = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ORIGIN).rstrip("/")
    print(f"announcing {len(PAGES)} urls for {origin}")
    sys.exit(1 if announce(origin) else 0)
