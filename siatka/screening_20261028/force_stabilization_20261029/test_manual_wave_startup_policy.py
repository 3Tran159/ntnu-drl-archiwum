"""Isolated policy/API tests. No real CFD launch, stop, lock, or server restart."""
import contextlib,datetime,io,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
import manual_control_common as c
import manual_control_server as server
ROOT=c.R
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.patch=patch.object(c,'R',self.root);self.patch.start()
  self.policy=self.root/'wave_startup_policy_current.json';self.wave={'preset':'W01_M10','target_s':1.2,'wall_minutes':30};self.calm=dict(self.wave,preset='C01_M10')
 def tearDown(self):self.patch.stop();self.tmp.cleanup()
 def set_policy(self,value):self.policy.write_text(json.dumps(value),encoding='utf8')
 def test_absent_policy_preserves_legacy_validation(self):
  self.assertEqual(c.validate_request(self.wave)['preset'],'W01_M10');self.assertTrue(next(p for p in c.catalog() if p['id']=='W01_M10')['enabled'])
 def test_pending_policy_blocks_wave_and_allows_calm(self):
  self.set_policy({'status':'conditional_pending_W01a_wave_validation'})
  with self.assertRaisesRegex(ValueError,'W01a validation pending'):c.validate_request(self.wave)
  self.assertEqual(c.validate_request(self.calm)['preset'],'C01_M10')
  presets=c.catalog();self.assertTrue(all(not p['enabled'] for p in presets if c.is_wave(p)));self.assertTrue(all(p['enabled'] for p in presets if not c.is_wave(p)))
 def test_unknown_validated_flag_cannot_bind_legacy_recipe(self):
  self.set_policy({'status':'validated','passed':True,'recipe_bound':True,'do_not_initialize_full_domain_with_wave':False})
  with self.assertRaisesRegex(ValueError,'no validated inlet-startup recipe binding'):c.validate_request(self.wave)
 def test_malformed_present_policy_fails_closed(self):
  for text in ('not json','[]','null'):
   self.policy.write_text(text)
   with self.assertRaises(ValueError):c.validate_request(self.wave)
   self.assertEqual(c.validate_request(self.calm)['preset'],'C01_M10')
 def test_policy_not_cached_and_base_catalog_unchanged(self):
  base=[dict(x) for x in c.CATALOG];self.assertEqual(c.validate_request(self.wave)['preset'],'W01_M10')
  self.set_policy({'status':'pending'})
  with self.assertRaises(ValueError):c.validate_request(self.wave)
  c.catalog();self.assertEqual(c.CATALOG,base)
 def test_source_validation_rechecks_policy(self):
  p=c.preset('W01_M10');self.set_policy({'status':'pending'})
  with self.assertRaisesRegex(ValueError,'W01a validation pending'):c.validate_source(p)
 def test_mock_http_catalog_and_launch_guard(self):
  self.set_policy({'status':'conditional_pending_W01a_wave_validation'});calls=[]
  class FakeProcess:
   pid=999999
   def poll(self):return None
  def fake_popen(*a,**kw):calls.append(a);return FakeProcess()
  with patch.object(server,'R',self.root),patch.object(server,'B',self.root),patch.object(server,'PENDING',None),patch.object(server,'active',lambda:(False,{},None)),patch.object(server.subprocess,'Popen',fake_popen):
   http=server.http.server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
   with patch.object(c,'PORT',http.server_address[1]),patch.object(server,'ORIGIN','http://127.0.0.1:'+str(http.server_address[1])):
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def call(path,data=None):
     headers={}
     if data is not None:headers={'Content-Type':'application/json','Origin':server.ORIGIN,'X-NTNU-Control':server.TOKEN}
     req=urllib.request.Request(server.ORIGIN+path,None if data is None else json.dumps(data).encode(),headers,method='GET' if data is None else 'POST')
     try:
      with opener.open(req,timeout=10) as response:return response.status,json.load(response)
     except urllib.error.HTTPError as error:return error.code,json.load(error)
    try:
     code,body=call('/api/catalog');self.assertEqual(code,200);self.assertTrue(body['startup_policy']['legacy_wave_starts_blocked']);self.assertTrue(all(not p['enabled'] for p in body['presets'] if c.is_wave(p)))
     code,body=call('/api/start',self.wave);self.assertEqual(code,400);self.assertIn('W01a validation pending',body['error']);self.assertEqual(calls,[]);self.assertFalse((self.root/'manual_requests').exists())
     code,body=call('/api/start',self.calm);self.assertEqual(code,202);self.assertEqual(len(calls),1)
     self.assertFalse(any(self.root.rglob('STOP')));self.assertFalse((self.root/'queue.lock').exists())
    finally:http.shutdown();http.server_close()
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);out=io.StringIO();result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
 record={'at':datetime.datetime.now().astimezone().isoformat(),'pass':result.wasSuccessful(),'tests':result.testsRun,'real_solver_launches':0,'real_stop_markers':0,'real_locks_modified':0,'server_restarts':0,'catalog_snapshot':c.catalog(),'policy_snapshot':c.wave_startup_policy(),'log':out.getvalue()}
 (ROOT/'manual_wave_startup_policy_test_review.json').write_text(json.dumps(record,indent=2),encoding='utf8');print(out.getvalue());raise SystemExit(0 if result.wasSuccessful() else 1)
