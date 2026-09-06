#!/usr/bin/env python3
"""Offline checks for the public website. No browser, network or dependencies.

Checks all local HTML references/fragments, expected per-app pages, metadata,
public-only content and CSS mobile/reduced-motion rules. A passing result is not
a visual viewport test or a claim that GitHub Pages / app-ads.txt is verified.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = '/premharsh-utilities/'
HOST = 'prxem-stack.github.io'
APPS = ['photo', 'milk', 'shifts', 'attendance', 'fuel', 'tailor', 'recipes', 'packing', 'knitting', 'room']

class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids = set()
        self.refs = []
        self.h1 = 0
        self.title = 0
        self.lang = False
        self.viewport = False
        self.description = False
        self.canonical = False
        self.errors = []
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            if attrs['id'] in self.ids:
                self.errors.append(f'duplicate ID: {attrs["id"]}')
            self.ids.add(attrs['id'])
        self.h1 += tag == 'h1'
        self.title += tag == 'title'
        if tag == 'html':
            self.lang = bool(attrs.get('lang'))
        if tag == 'meta' and attrs.get('name') == 'viewport':
            self.viewport = 'width=device-width' in attrs.get('content', '')
        if tag == 'meta' and attrs.get('name') == 'description':
            self.description = bool(attrs.get('content', '').strip())
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical = attrs.get('href', '').startswith('https://' + HOST + BASE)
        for field in ['href', 'src']:
            if attrs.get(field):
                self.refs.append(attrs[field])
        if tag == 'img' and 'alt' not in attrs:
            self.errors.append('image missing alt')
        if tag in ['script', 'iframe', 'form']:
            self.errors.append(f'unexpected active/embedded content: {tag}')

def main():
    errors = []
    pages = {p.resolve(): Page(p) for p in ROOT.rglob('*.html')}
    for path, page in pages.items():
        name = str(path.relative_to(ROOT))
        errors.extend(f'{name}: {e}' for e in page.errors)
        for prop, ok in [('single h1', page.h1 == 1), ('single title', page.title == 1), ('language', page.lang), ('viewport', page.viewport), ('description', page.description), ('canonical', page.canonical)]:
            if not ok:
                errors.append(f'{name}: missing/invalid {prop}')
        for reference in page.refs:
            parsed = urlsplit(reference)
            if parsed.scheme in ['mailto', 'tel', 'data', 'javascript']:
                errors.append(f'{name}: unexpected URL scheme: {reference}')
                continue
            if parsed.netloc and parsed.netloc != HOST:
                continue
            local = unquote(parsed.path)
            if parsed.netloc == HOST or local.startswith('/'):
                if not local.startswith(BASE):
                    errors.append(f'{name}: wrong project base: {reference}')
                    continue
                target = ROOT / local[len(BASE):]
            elif local:
                target = path.parent / local
            else:
                target = path
            target = target.resolve()
            if target.is_dir():
                target = target / 'index.html'
            if not target.is_relative_to(ROOT) or not target.exists():
                errors.append(f'{name}: broken local reference: {reference}')
            elif parsed.fragment and target in pages and parsed.fragment not in pages[target].ids:
                errors.append(f'{name}: missing anchor: {reference}')

    for app in APPS:
        for section in ['apps', 'privacy']:
            if not (ROOT / section / app / 'index.html').is_file():
                errors.append(f'missing {section}/{app}/index.html')
        policy = (ROOT / 'privacy' / app / 'index.html').read_text()
        if 'Advertising and privacy choices' not in policy or 'GitHub' not in policy:
            errors.append(f'{app}: incomplete privacy information')
        if not (ROOT / 'assets' / 'icons' / f'{app}.png').is_file():
            errors.append(f'{app}: missing icon')

    css = (ROOT / 'assets/style.css').read_text()
    for rule in ['@media(max-width:740px)', '@media(max-width:440px)', '@media(prefers-reduced-motion:reduce)', 'minmax(0,1fr)', ':focus-visible', '.skip-link']:
        if rule not in css:
            errors.append(f'CSS lacks required responsive/accessibility rule: {rule}')
    if css.count('{') != css.count('}'):
        errors.append('unbalanced CSS braces')
    if '@import' in css or re.search(r'url\(\s*["\']?https?://', css):
        errors.append('external font/asset dependency in CSS')
    for p in ROOT.rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.dart', '.apk', '.aab', '.ipa', '.zip', '.keystore', '.jks', '.p12', '.mobileprovision'}:
            errors.append(f'unexpected app/source/credential artifact: {p.relative_to(ROOT)}')
    html_text = '\n'.join(p.read_text() for p in pages)
    for forbidden in ['ca-app-pub-', '@gmail.com', '/Users/', 'pending owner details', 'pending support email', 'PENDING', 'TODO']:
        if forbidden in html_text:
            errors.append(f'private/internal/unfinished content in HTML: {forbidden}')
    expected_ad_line = 'google.com, pub-7658767097946231, DIRECT, f08c47fec0942fa0\n'
    if (ROOT / 'app-ads.txt').read_text() != expected_ad_line:
        errors.append('incorrect app-ads.txt publisher declaration')
    if not (ROOT / '.nojekyll').exists():
        errors.append('missing .nojekyll')
    for template in ['bug_report', 'feature_request', 'privacy_question']:
        template_path = ROOT / '.github' / 'ISSUE_TEMPLATE' / f'{template}.yml'
        if not template_path.exists():
            template_path = ROOT.parent / '.github' / 'ISSUE_TEMPLATE' / f'utilities_{template}.yml'
        content = template_path.read_text()
        if 'This report will be public' not in content or 'public-confirmation' not in content:
            errors.append(f'{template}: missing public-post guidance')
    result = {'passed': not errors, 'html_pages': len(pages), 'app_pages': len(APPS), 'app_privacy_pages': len(APPS), 'references_checked': sum(len(p.refs) for p in pages.values()), 'mobile_css_rules_checked': True, 'browser_visual_check': 'not performed by this offline checker', 'external_links_checked': False, 'errors': errors}
    print(json.dumps(result, indent=2))
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
