"""Detect official-page changes; never infer trading limits from arbitrary HTML.

Checks cover only listed URLs, not every linked article or account agreement.
Reviewed model patches can be published separately after checking applicability.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent


def run():
    path = ROOT / 'status.json'
    previous = json.loads(path.read_text()) if path.exists() else {'firms': {}}
    now = datetime.now(timezone.utc).isoformat()
    result = {'schemaVersion': 1, 'checkedAt': now, 'firms': {}}
    for firm, urls in json.loads((ROOT / 'sources.json').read_text()).items():
        old = previous.get('firms', {}).get(firm, {})
        pages = []
        try:
            for url in urls:
                with urlopen(Request(url, headers={'User-Agent': 'PropFirmRulesMonitor/1.0'}), timeout=20) as response:
                    if urlparse(response.url).hostname != urlparse(url).hostname:
                        raise ValueError('Unexpected redirect')
                    raw = response.read(2_000_001)
                    if len(raw) > 2_000_000:
                        raise ValueError('Page too large')
                    html = raw.decode('utf-8', errors='replace')
                html = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', html, flags=re.S | re.I)
                text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()
                if len(text) < 300 or any(x in text.lower() for x in ('verify you are human', 'just a moment...', 'access denied')):
                    raise ValueError('Page unavailable or challenged')
                pages.append(hashlib.sha256(text.encode()).hexdigest())
            digest = hashlib.sha256(''.join(pages).encode()).hexdigest()
            changed = bool(old.get('digest') and old['digest'] != digest)
            pending = changed or old.get('reviewRequired', True)
            result['firms'][firm] = {'sources': urls, 'digest': digest, 'lastSuccessfulCheck': now,
                'status': 'review_pending' if pending else 'unchanged', 'reviewRequired': pending,
                'changedAt': now if changed else old.get('changedAt')}
        except Exception as error:
            result['firms'][firm] = {**old, 'sources': urls, 'status': 'unavailable',
                'reviewRequired': True, 'error': type(error).__name__}
    path.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    run()
