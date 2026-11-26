"""Small independent geometric expectations; never invokes STAR or production build."""
import unittest, math
from clip_extend_campaign_domain import clip_halfplane,area,owners_of,assert_simple
class ClipTests(unittest.TestCase):
 def test_half_rectangle(self):
  p=[[0,.01,0],[2,.01,0],[2,.01,1],[0,.01,1]];r={}
  q=clip_halfplane([0,1,2,3],p,1,False,r)
  self.assertAlmostEqual(area(p,q),1);self.assertEqual(len(q),4);assert_simple(p,q)
 def test_shared_edge_uses_one_id(self):
  p=[[0,.01,0],[2,.01,0],[2,.01,1],[0,.01,1],[2,.01,2],[0,.01,2]];r={}
  a=clip_halfplane([0,1,2,3],p,1,False,r);b=clip_halfplane([3,2,4,5],p,1,False,r)
  shared=[i for i in a if i in b and p[i][0]==1]
  self.assertEqual(len(shared),1)
  e=owners_of([a,b]);self.assertTrue(any(len(o)==2 and o[0][1:]==o[1][1:][::-1] for o in e.values()))
  self.assertEqual(len(r),3)
 def test_exact_vertex_reuse(self):
  p=[[0,.01,0],[1,.01,0],[2,.01,1],[0,.01,1]];r={}
  q=clip_halfplane([0,1,2,3],p,1,False,r)
  self.assertEqual(q.count(1),1);self.assertEqual(len(set(q)),len(q))
 def test_both_halfplanes_area(self):
  p=[[-2,.01,-1],[2,.01,-1],[2,.01,1],[-2,.01,1]];r={}
  q=clip_halfplane([0,1,2,3],p,-1,True,r);q=clip_halfplane(q,p,1,False,r)
  self.assertAlmostEqual(area(p,q),4);assert_simple(p,q)
 def test_removed_and_unchanged(self):
  p=[[0,.01,0],[1,.01,0],[1,.01,1],[0,.01,1]];r={}
  self.assertEqual(clip_halfplane([0,1,2,3],p,-1,False,r),[])
  q=clip_halfplane([0,1,2,3],p,2,False,r)
  self.assertEqual(set(q),{0,1,2,3});self.assertEqual(r,{})
 def test_tiny_positive_cell(self):
  p=[[0,.01,0],[.002,.01,0],[.002,.01,1.5e-6],[0,.01,1.5e-6]]
  q=clip_halfplane([0,1,2,3],p,.001,False,{})
  self.assertGreater(area(p,q),0);self.assertAlmostEqual(area(p,q),1.5e-9,places=18)
 def test_intersection_symmetry(self):
  p=[[0,.01,0],[3,.01,2],[3,.01,4],[0,.01,4]];r={}
  a=clip_halfplane([0,1,2,3],p,1,False,r)
  b=clip_halfplane([3,2,1,0],p,1,False,r)
  self.assertEqual(set(a),set(b));self.assertAlmostEqual(area(p,a),-area(p,b))
if __name__=="__main__":unittest.main()
