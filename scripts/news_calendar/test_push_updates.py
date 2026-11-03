import unittest
from datetime import datetime,timezone,timedelta
from push_updates import plan,dispatch,signature
N=datetime(2026,11,4,tzinfo=timezone.utc)
def event(title='CPI',days=1):return dict(id='event-1',title=title,date=(N+timedelta(days=days)).isoformat(),country='USD',impact='high',status='published')
class PushTests(unittest.TestCase):
 def test_first_import_is_not_a_broadcast(self):
  queue,current=plan({'events':[event()]},{},{},N);self.assertEqual(queue,[]);self.assertEqual(len(current),1)
 def test_timestamp_refresh_does_not_broadcast(self):
  e=event();queue,_=plan({'events':[{**e,'reviewedAt':'new'}]},{},{'events':{e['id']:signature(e)}},N);self.assertEqual(queue,[])
 def test_new_events_create_one_digest(self):
  queue,_=plan({'events':[event()]},{},{'events':{}},N);self.assertEqual(len(queue),1);self.assertEqual(queue[0]['audience'],'news_all')
 def test_past_and_far_future_are_not_notified(self):
  queue,_=plan({'events':[event(days=-3),{**event(days=30),'id':'far'}]},{},{'events':{}},N);self.assertEqual(queue,[])
 def test_paused_automatic_still_allows_scheduled_manual(self):
  item=dict(id='manual-123',title='Update',body='Read news',audience='news_all',dueAt=N.isoformat())
  queue,_=plan({'events':[event()]},{'automatic':False,'campaigns':[item]},{'events':{}},N);self.assertEqual([x['id'] for x in queue],['manual-123'])
 def test_accepted_campaign_is_not_resent(self):
  calls=[];states=[];feed={'events':[event()]};state={'events':{}}
  out=dispatch(feed,{},state,N,lambda x:calls.append(x) or 'fcm-id',lambda s:states.append(s.copy()))
  dispatch(feed,{},out,N,lambda x:calls.append(x),lambda s:None);self.assertEqual(len(calls),1);self.assertTrue(states)
 def test_uncertain_send_is_not_blindly_replayed(self):
  calls=[]
  def fail(x):calls.append(x);raise TimeoutError()
  out=dispatch({'events':[event()]},{},{'events':{}},N,fail,lambda s:None)
  dispatch({'events':[event()]},{},out,N,fail,lambda s:None);self.assertEqual(len(calls),1);self.assertEqual(list(out['receipts'].values())[0]['state'],'needs_review')
 def test_future_manual_waits(self):
  item=dict(id='manual-123',title='Update',body='News',audience='news_all',dueAt=(N+timedelta(hours=1)).isoformat())
  queue,_=plan({'events':[]},{'campaigns':[item]},{'events':{}},N);self.assertEqual(queue,[])
if __name__=='__main__':unittest.main()
