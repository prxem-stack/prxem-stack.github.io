"""Idempotent automatic news digests and admin campaigns through FCM topics."""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'news-alert'
UTC = timezone.utc

def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default

def write(path, data):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    temp.replace(path)

def record_health(data):
    path=ROOT/'push-health.json'
    previous=read(path,{})
    old={k:v for k,v in previous.items() if k!='checkedAt'}
    new={k:v for k,v in data.items() if k!='checkedAt'}
    try:
        recent=datetime.now(UTC)-datetime.fromisoformat(previous['checkedAt'].replace('Z','+00:00'))<timedelta(minutes=25)
    except (KeyError,ValueError):
        recent=False
    if old!=new or not recent:
        write(path,data)

def signature(event):
    return hashlib.sha256(json.dumps({k:event.get(k) for k in ('id','title','date','country','impact','summary','explanation','pairInsights')},sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def plan(feed, config, state, now):
    baseline=state.get('events')
    current={str(e['id']):signature(e) for e in feed.get('events',[]) if e.get('status')=='published'}
    receipts=state.get('receipts',{})
    queue=[]
    if baseline is not None and config.get('automatic',True):
        changes=[e for e in feed.get('events',[]) if e.get('status')=='published' and baseline.get(str(e['id']))!=signature(e) and now-timedelta(hours=2)<=datetime.fromisoformat(e['date'].replace('Z','+00:00'))<=now+timedelta(days=7)]
        if changes:
            changes.sort(key=lambda x:x['date'])
            digest=hashlib.sha256('|'.join(sorted(signature(e) for e in changes)).encode()).hexdigest()[:24]
            queue.append({'id':'auto-'+digest,'title':f"{len(changes)} economic news update{'s' if len(changes)>1 else ''}",'body':changes[0]['country']+' · '+changes[0]['title'][:180]+(' + more updates' if len(changes)>1 else ''),'audience':'news_all','eventId':changes[0]['id'],'kind':'automatic'})
    if config.get('automatic',True) and config.get('releaseAlerts',True):
        before=int(config.get('beforeMinutes',15))
        if not 1<=before<=60:
            raise ValueError('Automatic reminder must be 1–60 minutes')
        for e in feed.get('events',[]):
            if e.get('status')!='published' or e.get('impact')!='high':
                continue
            seconds=(datetime.fromisoformat(e['date'].replace('Z','+00:00'))-now).total_seconds()
            if not 0<=seconds<=before*60:
                continue
            minutes=max(1,int((seconds+59)//60))
            key='release-'+hashlib.sha256((e['id']+'|'+e['date']).encode()).hexdigest()[:24]
            queue.append({'id':key,'title':f"High-impact {e['country']} news in {minutes} min",'body':e['title'][:220],'audience':'news_all','eventId':e['id'],'kind':'release_alert'})
    for item in config.get('campaigns',[]):
        if not isinstance(item,dict) or not item.get('id') or not item.get('title') or not item.get('body'):
            raise ValueError('Invalid notification campaign')
        if item.get('audience') not in ['news_all','news_test','news_usd','news_eur','news_gbp','news_jpy','news_cad','news_aud','news_nzd','news_chf']:
            raise ValueError('Invalid notification audience')
        due=datetime.fromisoformat(item['dueAt'].replace('Z','+00:00'))
        if due<=now:
            queue.append({**item,'expired':due<now-timedelta(hours=24)})
    return [x for x in queue if x['id'] not in receipts],current

def sender(account):
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    credentials=service_account.Credentials.from_service_account_info(account,scopes=['https://www.googleapis.com/auth/firebase.messaging'])
    session=AuthorizedSession(credentials)
    project=account['project_id']
    if project!='prop-firm-news-alert':
        raise ValueError('Refusing to send using another app project')
    def send(item):
        key=item['id']
        payload={'message':{'topic':item['audience'],'notification':{'title':item['title'],'body':item['body']},'data':{'campaignId':key,'eventId':str(item.get('eventId','')),'kind':'news_update'},'android':{'priority':'HIGH','ttl':'3600s','collapse_key':key,'notification':{'channel_id':'market_pulse_news','tag':key}},'apns':{'headers':{'apns-push-type':'alert','apns-priority':'10','apns-collapse-id':key[:64],'apns-expiration':str(int(datetime.now(UTC).timestamp())+3600)},'payload':{'aps':{'sound':'default'}}}}}
        response=session.post(f'https://fcm.googleapis.com/v1/projects/{project}/messages:send',json=payload,timeout=20)
        response.raise_for_status()
        return response.json()['name']
    return send

def dispatch(feed,config,state,now,send,persist):
    queue,current=plan(feed,config,state,now)
    result={'events':state.get('events'),'receipts':dict(state.get('receipts',{}))}
    # Claim before network I/O: an interrupted or ambiguous request is not replayed.
    for item in queue:
        if item['id'] in result['receipts']:
            continue
        receipt={'state':'expired' if item.get('expired') else 'sending','at':now.isoformat(),'title':item['title']}
        result['receipts'][item['id']]=receipt
        if item.get('expired'):
            persist(result)
            continue
        persist(result)
        try:
            receipt.update(state='accepted',providerId=send(item))
        except Exception as error:
            # Operator can inspect and explicitly enqueue a replacement; no blind retry.
            receipt.update(state='needs_review',error=type(error).__name__)
        persist(result)
    result['events']=current
    # Bound fingerprints to the current feed, retaining the last 1000 receipts.
    result['receipts']=dict(list(result['receipts'].items())[-1000:])
    persist(result)
    return result

def main():
    now=datetime.now(UTC)
    feed=read(ROOT/'reviewed.json',{})
    config=read(ROOT/'notifications.json',{'automatic':True,'campaigns':[]})
    state=read(ROOT/'push-state.json',{'receipts':{}})
    raw=os.environ.get('FCM_SERVICE_ACCOUNT_JSON','')
    if not raw:
        # Do not mark scheduled campaigns sent or suppress future news while unconfigured.
        record_health({'checkedAt':now.isoformat(),'status':'setup_required','reason':'FCM_SERVICE_ACCOUNT_JSON is not configured','accepted':0})
        if 'events' not in state:
            state['events']={e['id']:signature(e) for e in feed.get('events',[]) if e.get('status')=='published'}
            write(ROOT/'push-state.json',state)
        print('Push setup required; no notifications sent')
        return
    def persist(value):
        write(ROOT/'push-state.json',value)
        if os.environ.get('CI_PUSH_STATE_COMMIT')=='1':
            subprocess.run(['git','add','news-alert/push-state.json'],check=True)
            unchanged=subprocess.run(['git','diff','--cached','--quiet']).returncode==0
            if not unchanged:
                subprocess.run(['git','commit','-m','Record news push dispatch state'],check=True)
                for attempt in range(3):
                    subprocess.run(['git','pull','--rebase','origin','main'],check=True)
                    if subprocess.run(['git','push','origin','HEAD:main']).returncode==0:
                        break
                else:
                    raise RuntimeError('Could not persist dispatch claim; no send attempted')
    result=dispatch(feed,config,state,now,sender(json.loads(raw)),persist)
    bad=[x for x in result['receipts'].values() if x['state'] in ('sending','needs_review')]
    record_health({'checkedAt':now.isoformat(),'status':'needs_review' if bad else 'ok','accepted':sum(x['state']=='accepted' for x in result['receipts'].values()),'receipts':result['receipts'],'note':'Accepted by FCM does not confirm delivery to a phone'})
    print('Push processed:',len(result['receipts']),'receipts;',len(bad),'need review')
    if bad:raise SystemExit(1)

if __name__=='__main__':main()
