#!/usr/bin/env python3
"""解析短链，跟随 HTTP 重定向，输出最终的完整 URL。

用法：python expand-shortlink.py <url>
"""
import sys
import requests

url = sys.argv[1]

r = requests.get(
    url,
    allow_redirects=True,
    timeout=15,
    headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    },
)

print(r.url)
