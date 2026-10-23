import unittest
from parse_trace import parse

def trace(events):
    return '\n'.join(f'x-{tid} (-------) [000] ..... {ts:.6f}: tracing_mark_write: {mark}' for tid,ts,mark in events)
class ParserTests(unittest.TestCase):
    def test_nested_union_not_sum(self):
        r=parse(trace([(1,1,'B|6291|outer'),(1,2,'B|6291|inner'),(1,3,'E|6291|inner'),(1,4,'E|6291|outer')]))
        self.assertEqual(r['complete_count'],2);self.assertEqual(r['complete_span_wall_union_seconds'],3)
    def test_thread_isolation(self):
        r=parse(trace([(1,1,'B|6291|one'),(2,2,'B|6291|two'),(1,3,'E|6291|one'),(2,4,'E|6291|two')]))
        self.assertEqual(r['complete_count'],2);self.assertEqual(r['complete_span_wall_union_seconds'],3)
    def test_pid_mismatch_no_cross_pair(self):
        r=parse(trace([(1,1,'B|6291|one'),(1,2,'E|999|one')]))
        self.assertEqual(r['complete_count'],0);self.assertEqual(r['anomalies'][0]['reason'],'pid_mismatch')
    def test_named_mismatch_no_search_down(self):
        r=parse(trace([(1,1,'B|6291|outer'),(1,2,'B|6291|inner'),(1,3,'E|6291|outer')]))
        self.assertEqual(r['complete_count'],0);self.assertEqual(len(r['excluded_spans']),2)
    def test_bare_end_and_parent_tainted(self):
        r=parse(trace([(1,1,'B|6291|outer'),(1,2,'B|6291|inner'),(1,3,'E'),(1,4,'E|6291|outer')]))
        self.assertEqual(r['complete_count'],0);self.assertTrue(all(s['duration_ms'] is None for s in r['excluded_spans']))
    def test_unclosed_and_orphan(self):
        r=parse(trace([(1,1,'E|6291|x'),(1,2,'B|6291|x')]))
        self.assertEqual(r['complete_count'],0);self.assertEqual(r['excluded_spans'][0]['status'],'unclosed_at_trace_end')
    def test_other_pid_valid(self):
        r=parse(trace([(1,1,'B|999|x'),(1,2,'E|999|x')]))
        self.assertEqual(r['complete_count'],0)
    def test_unknown_fragment_taints(self):
        r=parse(trace([(1,1,'B|6291|x'),(1,2,'fragment'),(1,3,'E|6291|x')]))
        self.assertEqual(r['complete_count'],0)
    def test_counter_async_separate(self):
        r=parse(trace([(1,1,'B|6291|x'),(1,2,'S|6291|async|1'),(1,3,'F|6291|async|1'),(1,4,'E|6291|x')]))
        self.assertEqual(r['complete_count'],1);self.assertEqual(len(r['async_and_counter_markers']),2)
    def test_tagged_end_no_name(self):
        r=parse(trace([(1,1,'B|6291|x|I48'),(1,2,'E|6291|I48')]))
        self.assertEqual(r['complete_count'],1)
if __name__=='__main__':unittest.main()
