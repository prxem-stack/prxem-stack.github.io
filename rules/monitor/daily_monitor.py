"""Daily official-source discovery and change detection. No inferred rule patches.
Only a source-change notice is automatic; business meaning requires review.
"""
import concurrent.futures, hashlib, html, json, re, sys
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
UA = 'PropFirmDailyMonitor/1.0'
LIMIT = 1500000
PAGES_PER_FIRM = 6
PATTERN = re.compile(r'rule|news|blog|announc|update|platform|payout|reward|model|challenge|evaluation|trading-objective|faq|help|product|pricing', re.I)
BLOCK = re.compile(r'login|sign-in|checkout|register|affiliate|/tag/|/author/|/page/|privacy|cookie|terms', re.I)


def safe_url(url, hosts):
    p = urlsplit(url)
    if p.scheme != 'https' or p.username or p.password or p.port not in (None,443) or p.hostname not in hosts:
        raise ValueError('Source outside official host allowlist')
    if re.search(r'\.(pdf|zip|mp4|png|jpg|webp|svg|css|js)$', p.path, re.I):
        raise ValueError('Not a source page')
    return urlunsplit(('https',p.netloc,p.path or '/',p.query,''))


class Redirects(HTTPRedirectHandler):
    def __init__(self, hosts): self.hosts=hosts
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl,self.hosts)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def download(url, hosts):
    url=safe_url(url,hosts)
    with build_opener(Redirects(hosts)).open(Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xml,text/xml,text/plain'}),timeout=12) as r:
        safe_url(r.url,hosts)
        if not any(x in r.headers.get('Content-Type','').lower() for x in ('html','xml','text/plain','application/json')):
            raise ValueError('Unsupported source type')
        limit=8*1024*1024 if 'application/json' in r.headers.get('Content-Type','').lower() else LIMIT
        data=r.read(limit+1)
        if len(data)>limit: raise ValueError('Source exceeds size limit')
        return data.decode('utf-8','replace'),r.url


class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.skip=[];self.title=False;self.heading=False;self.parts=[];self.titles=[];self.headings=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a' and a.get('href'):self.links.append(a['href'])
        if tag in ('script','style','noscript','svg','nav','footer','header'):
            self.skip.append(tag)
        if self.skip:return
        if tag=='title':self.title=True
        if tag in ('h1','h2','h3'):self.heading=True;self.headings.append('')
    def handle_endtag(self,tag):
        if self.skip:
            if tag==self.skip[-1]:self.skip.pop()
            return
        if tag=='title':self.title=False
        if tag in ('h1','h2','h3'):self.heading=False
    def handle_data(self,value):
        if self.skip:return
        value=re.sub(r'\s+',' ',html.unescape(value)).strip()
        if not value:return
        self.parts.append(value)
        if self.title:self.titles.append(value)
        if self.heading and self.headings:self.headings[-1]+=' '+value


def parse(raw, min_chars=150):
    if re.search(r'vercel security checkpoint|just a moment\.\.\.|verify you are human|access denied|cf-chl-',raw,re.I):
        raise ValueError('Official source blocked automated access')
    p=Page();p.feed(raw)
    text=' '.join(p.parts)
    if len(text)<min_chars:raise ValueError('Insufficient official page content')
    # Hash the full normalized page, but retain at most 70 words of headings.
    headings=[];remaining=70
    for h in p.headings:
        h=h.strip()[:120];words=h.split()[:remaining]
        if words:headings.append(' '.join(words));remaining-=len(words)
        if remaining<=0:break
    return {'hash':hashlib.sha256(text.encode()).hexdigest(),'title':' '.join(p.titles)[:140], 'headings':headings},p.links


def sitemap_urls(raw,hosts):
    tree=ET.fromstring(raw);out=[]
    for e in tree.iter():
        if e.tag.split('}')[-1]!='loc' or not e.text:continue
        try:u=safe_url(e.text.strip(),hosts)
        except (ValueError,TypeError):continue
        if PATTERN.search(u) and not BLOCK.search(u):out.append(u)
    return list(dict.fromkeys(out))[:400]


def make_notice(firm,url,before,after,now,kind='page_changed'):
    identity=hashlib.sha256((firm['id']+url+after['hash']).encode()).hexdigest()[:24]
    added=[h for h in after['headings'] if h not in before.get('headings',[])][:3]
    removed=[h for h in before.get('headings',[]) if h not in after['headings']][:3]
    return {'id':identity,'firmId':firm['id'],'firm':firm['name'],'source':url,'detectedAt':now,'kind':kind,'status':'review_pending',
            'comparisonChannel':after.get('channel','html'),'title':after['title'] or 'Official page updated','summary':'A change was detected on this official page. Its meaning and account applicability have not been verified.',
            'addedHeadings':added,'removedHeadings':removed,'beforeHash':before.get('hash'), 'afterHash':after['hash']}


def scan(firm, previous, now, day):
    hosts=set(firm['hosts']);robots={};errors=[];current=dict(previous.get('pages',{}));notices=[];checked=[]
    def allowed(url):
        p=urlsplit(url);origin=p.scheme+'://'+p.netloc
        if origin not in robots:
            robot=RobotFileParser();robot.set_url(origin+'/robots.txt')
            try:
                raw,_=download(origin+'/robots.txt',hosts);robot.parse(raw.splitlines())
            except Exception as e:
                # An unavailable robots file must not silently turn into permission.
                if getattr(e,'code',None)==404:robot.parse([])
                else:raise ValueError('robots.txt unavailable; source skipped')
            robots[origin]=robot
        if not robots[origin].can_fetch(UA,url):raise ValueError('Disallowed by robots.txt')
    def get(url):allowed(url);return download(url,hosts)
    inventory=set(previous.get('inventory',[]));discovered=set();home=firm['seeds'][0]
    api_checked=False
    if firm.get('articleApi'):
        # Documented anonymous Help Center API; no login, proxy or bot-challenge bypass.
        api=firm['articleApi']
        try:
            for _ in range(5):
                raw,_=download(api,hosts);batch=json.loads(raw)
                articles=batch.get('articles')
                if not isinstance(articles,list) or len(articles)>100:raise ValueError('Invalid official API response')
                for article in articles:
                    if article.get('draft') or not isinstance(article.get('body'),str):continue
                    url=safe_url(article['html_url'],hosts)
                    snapshot,_=parse('<title>'+html.escape(article.get('title',''))+'</title><h1>'+html.escape(article.get('title',''))+'</h1>'+article['body'],min_chars=1)
                    snapshot['channel']='article_api'
                    snapshot['sourceEditedAt']=article.get('edited_at') or article.get('updated_at')
                    before=current.get(url)
                    if before and before.get('channel')=='article_api' and before['hash']!=snapshot['hash']:notices.append(make_notice(firm,url,before,snapshot,now))
                    elif not before and previous.get('apiCheckedAt') and article.get('created_at','')>previous['apiCheckedAt']:
                        notices.append(make_notice(firm,url,{},snapshot,now,'page_added'))
                    current[url]={**snapshot,'checkedAt':now};checked.append(url);discovered.add(url)
                api_checked=True
                if not batch.get('next_page'):break
                api=safe_url(batch['next_page'],hosts)
        except Exception as e:errors.append({'source':firm['articleApi'],'error':type(e).__name__+': '+str(e)[:160]})
    try:
        raw,final=get(home);snapshot,links=parse(raw)
        for href in links:
            try:u=safe_url(urljoin(final,href),hosts)
            except (ValueError,TypeError):continue
            if PATTERN.search(u) and not BLOCK.search(u) and not urlsplit(u).query:discovered.add(u)
        for sm in ['/sitemap.xml','/sitemap_index.xml']:
            try:
                rawsm,_=get(urljoin(home,sm));discovered.update(sitemap_urls(rawsm,hosts))
            except Exception:pass
        before=current.get(home)
        if before and before.get('channel','html')=='html' and before['hash']!=snapshot['hash']:notices.append(make_notice(firm,home,before,snapshot,now))
        current[home]={**snapshot,'checkedAt':now};checked.append(home)
    except Exception as e:errors.append({'source':home,'error':type(e).__name__+': '+str(e)[:160]})
    inventory.update(discovered);inventory.update(firm['seeds']);inventory=sorted(inventory)[:400]
    # Rotate discovery pages, retaining explicit rule/help seeds every day.
    seeds=firm['seeds'][1:3];candidates=[u for u in inventory if u not in seeds and u!=home]
    offset=(day*max(1,PAGES_PER_FIRM-1-len(seeds)))%max(1,len(candidates))
    candidates=candidates[offset:]+candidates[:offset]
    queue=[u for u in dict.fromkeys(seeds+candidates) if u not in checked][:PAGES_PER_FIRM-1]
    for url in queue:
        try:
            raw,final=get(url);snapshot,_=parse(raw);before=current.get(url)
            if before and before.get('channel','html')=='html' and before['hash']!=snapshot['hash']:notices.append(make_notice(firm,url,before,snapshot,now))
            # First capture establishes a baseline; never invent a new feature/date.
            current[url]={**snapshot,'checkedAt':now};checked.append(url)
        except Exception as e:errors.append({'source':url,'error':type(e).__name__+': '+str(e)[:160]})
    # Cap retained observations; prune oldest unvisited pages.
    current=dict(sorted(current.items(),key=lambda x:x[1].get('checkedAt',''),reverse=True)[:150])
    checked=list(dict.fromkeys(checked))
    status='ok' if checked and not errors else 'partial' if checked else 'unavailable'
    return firm['id'],{'pages':current,'inventory':inventory,'apiCheckedAt':now if api_checked else previous.get('apiCheckedAt')},{'id':firm['id'],'name':firm['name'],'status':status,'checkedAt':now,'pagesChecked':len(checked),'knownPages':len(inventory),'errors':errors},notices


def write_json(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)


def main():
    nowdt=datetime.now(timezone.utc);now=nowdt.isoformat();day=nowdt.toordinal()
    firms=json.loads((ROOT/'firms.json').read_text())['firms']
    try:old=json.loads((ROOT/'state.json').read_text())
    except (OSError,ValueError):old={}
    try:prior=json.loads((ROOT/'updates.json').read_text()).get('updates',[])
    except (OSError,ValueError):prior=[]
    state={};coverage=[];new=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures=[pool.submit(scan,f,old.get(f['id'],{}),now,day) for f in firms]
        for future in concurrent.futures.as_completed(futures):
            key,s,c,n=future.result();state[key]=s;coverage.append(c);new.extend(n)
    cutoff=(nowdt-timedelta(days=90)).isoformat()
    updates={u['id']:u for u in prior if u.get('detectedAt','')>=cutoff}
    updates.update({u['id']:u for u in new})
    # Approval records are maintained separately by the owner, never by crawled text.
    try:reviews=json.loads((ROOT/'reviews.json').read_text())
    except (OSError,ValueError):reviews={}
    for key,review in reviews.items():
        if key in updates and review.get('status') in ('reviewed','dismissed'):
            updates[key].update({k:review[k] for k in ('status','summary','appliesTo','reviewedAt') if k in review})
    records=sorted(updates.values(),key=lambda x:x['detectedAt'],reverse=True)[:600]
    feed={'schemaVersion':1,'checkedAt':now,'validUntil':(nowdt+timedelta(hours=48)).isoformat(),'coverage':sorted(coverage,key=lambda c:c['name']),
          'updates':[u for u in records if u['status']!='dismissed'],'limits':{'pagesPerFirmPerRun':PAGES_PER_FIRM,'apiArticlesPerFirmPerRun':50,'coverage':'Official allowlisted pages only; discovery rotates daily. Blocked sources are reported, not bypassed. First run establishes baselines.'}}
    write_json(ROOT/'state.json',state);write_json(ROOT/'updates.json',feed)
    print(json.dumps({'firms':len(firms),'reachable':sum(c['pagesChecked']>0 for c in coverage),'checkedPages':sum(c['pagesChecked'] for c in coverage),'newChangeNotices':len(new)}))

if __name__=='__main__':main()
