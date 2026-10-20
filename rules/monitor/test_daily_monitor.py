import unittest
from unittest.mock import patch
import daily_monitor as m

class MonitorTests(unittest.TestCase):
 def test_normalize_ignores_script_navigation(self):
  a='<title>Rules</title><nav>random</nav><h1>Trading objectives</h1><p>'+('Real source content '*20)+'</p>'
  b=a.replace('random','changed nav')+'<script>fake claim</script>'
  self.assertEqual(m.parse(a)[0]['hash'],m.parse(b)[0]['hash'])
 def test_blocked_page_rejected(self):
  with self.assertRaises(ValueError):m.parse('Vercel Security Checkpoint '+('x'*200))
 def test_url_allowlist(self):
  for url in ['http://firm.com/','https://evil.test/','https://user:secret@firm.com/','https://firm.com:8443/']:
   with self.assertRaises(ValueError):m.safe_url(url,{'firm.com'})
 def test_sitemap_excludes_external_and_login(self):
  xml='<urlset><url><loc>https://firm.com/blog/new</loc></url><url><loc>https://evil.test/news</loc></url><url><loc>https://firm.com/login/news</loc></url></urlset>'
  self.assertEqual(m.sitemap_urls(xml,{'firm.com'}),['https://firm.com/blog/new'])
 def test_notice_is_unverified_not_rule_patch(self):
  r=m.make_notice({'id':'firm','name':'Firm'},'https://firm.com/',{'hash':'old','headings':['Old']},{'hash':'new','title':'Rules','headings':['New']},'2026-10-21T00:00:00Z')
  self.assertEqual(r['status'],'review_pending');self.assertEqual(r['addedHeadings'],['New']);self.assertNotIn('rulePatches',r)
 def test_first_run_baseline_not_new_feature(self):
  firm={'id':'firm','name':'Firm','hosts':['firm.com'],'seeds':['https://firm.com/']}
  raw='<title>Firm</title><h1>Objectives</h1><p>'+('Real official source content '*20)+'</p>'
  def get(url,hosts):
   if url.endswith('robots.txt'):return 'User-agent: *\nAllow: /',url
   if 'sitemap' in url:return '<urlset/>',url
   return raw,url
  with patch.object(m,'download',side_effect=get):
   _,state,coverage,notices=m.scan(firm,{},'2026-10-21T00:00:00Z',1)
  self.assertEqual(notices,[]);self.assertEqual(coverage['status'],'ok');self.assertIn('https://firm.com/',state['pages'])
 def test_failed_source_does_not_remove_previous_baseline(self):
  firm={'id':'firm','name':'Firm','hosts':['firm.com'],'seeds':['https://firm.com/']}
  old={'pages':{'https://firm.com/':{'hash':'previous','checkedAt':'2026-10-20'}}}
  with patch.object(m,'download',side_effect=ValueError('blocked')):
   _,state,coverage,notices=m.scan(firm,old,'2026-10-21',1)
  self.assertEqual(coverage['status'],'unavailable');self.assertEqual(state['pages']['https://firm.com/']['hash'],'previous');self.assertEqual(notices,[])

 def test_public_api_baseline_and_edit(self):
  firm={'id':'firm','name':'Firm','hosts':['firm.com'],'seeds':['https://firm.com/'],'articleApi':'https://firm.com/api/articles'}
  article={'html_url':'https://firm.com/rules','title':'Account rule','body':'<p>Original rule.</p>','draft':False,'edited_at':'2026-10-20T00:00:00Z'}
  def get(url,hosts):
   if '/api/' in url:return m.json.dumps({'articles':[article],'next_page':None}),url
   raise ValueError('Website unavailable')
  with patch.object(m,'download',side_effect=get):
   _,state,coverage,notices=m.scan(firm,{},'2026-10-21T00:00:00Z',1)
   self.assertEqual(coverage['pagesChecked'],1);self.assertEqual(notices,[])
   article['body']='<p>Changed rule.</p>'
   _,_,coverage,notices=m.scan(firm,state,'2026-10-22T00:00:00Z',2)
   self.assertEqual(len(notices),1);self.assertEqual(notices[0]['status'],'review_pending')
 def test_private_draft_api_article_excluded(self):
  firm={'id':'firm','name':'Firm','hosts':['firm.com'],'seeds':['https://firm.com/'],'articleApi':'https://firm.com/api/articles'}
  def get(url,hosts):
   if '/api/' in url:return m.json.dumps({'articles':[{'draft':True,'body':'Secret'}]}),url
   raise ValueError('Unavailable')
  with patch.object(m,'download',side_effect=get):
   _,state,coverage,notices=m.scan(firm,{},'2026-10-21',1)
  self.assertEqual(coverage['pagesChecked'],0);self.assertEqual(notices,[])

 def test_html_to_api_migration_is_not_a_rule_change(self):
  firm={'id':'firm','name':'Firm','hosts':['firm.com'],'seeds':['https://firm.com/'],'articleApi':'https://firm.com/api/articles'}
  old={'pages':{'https://firm.com/rules':{'hash':'html-with-navigation','headings':['Related articles'],'checkedAt':'2026-10-20'}}}
  def get(url,hosts):
   if '/api/' in url:return m.json.dumps({'articles':[{'html_url':'https://firm.com/rules','title':'Rule','body':'<p>Rule content</p>','draft':False}]}),url
   raise ValueError('Unavailable')
  with patch.object(m,'download',side_effect=get):
   _,state,coverage,notices=m.scan(firm,old,'2026-10-21',1)
  self.assertEqual(notices,[]);self.assertEqual(state['pages']['https://firm.com/rules']['channel'],'article_api')

if __name__=='__main__':unittest.main()
