"""Offline image check. Never contacts CtYun or requires account credentials."""
import subprocess
from pathlib import Path

import ddddocr
import requests
from DrissionPage import ChromiumOptions, ChromiumPage

assert Path("/app/CtYun.dll").is_file(), "CtYun.dll missing from base image"
subprocess.run(["dotnet", "--list-runtimes"], check=True)
ddddocr.DdddOcr(show_ad=False)
options = ChromiumOptions().set_browser_path("/usr/bin/chromium").auto_port()
options.headless()
options.set_argument("--no-sandbox")
options.set_argument("--disable-dev-shm-usage")
page = ChromiumPage(addr_or_opts=options)
try:
    page.get("about:blank")
    assert page.run_js("return 6 * 7;") == 42
finally:
    page.quit()
print("Offline smoke test passed: .NET, OCR, requests and Chromium")
