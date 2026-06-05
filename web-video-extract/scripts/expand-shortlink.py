#!/usr/bin/env python3
"""Follow redirects for short video links and print the final URL.

Usage:
    python3 expand-shortlink.py <url>
"""

import sys
import urllib.request


if len(sys.argv) != 2:
    raise SystemExit("usage: expand-shortlink.py <url>")

request = urllib.request.Request(
    sys.argv[1],
    headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    },
)

with urllib.request.urlopen(request, timeout=15) as response:
    print(response.geturl())
