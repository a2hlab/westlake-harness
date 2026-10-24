import unittest
from check_identity import verify, PREFIX

class Identity(unittest.TestCase):
    def setUp(self):
        self.payload = b'a' * PREFIX + b'suffix'
        self.s = dict(dev=1, inode=2, size=len(self.payload), mtime=3, ctime=4)
    def call(self, pre=None, post=None, prefix=None, payload=None):
        return verify(self.s, self.s, self.s if pre is None else pre, self.s if post is None else post, b'a'*PREFIX if prefix is None else prefix, self.payload if payload is None else payload)
    def test_bound(self): self.assertEqual(self.call()['status'], 'bound')
    def test_prefix_changed(self): self.assertEqual(self.call(prefix=b'b'*PREFIX)['reason'], 'prefix_changed')
    def test_identity_missing(self): self.assertEqual(self.call(pre={})['status'], 'unknown')
    def test_post_changed(self): self.assertEqual(self.call(post={**self.s,'inode':7})['status'], 'identity_mismatch')
    def test_truncated(self): self.assertEqual(self.call(payload=b'a'*PREFIX)['status'], 'unknown')
    def test_oversize(self):
        s={**self.s,'size':524289}
        self.assertEqual(verify(s,s,s,s,b'a'*PREFIX,b'a'*524289)['status'],'unknown')

if __name__ == '__main__': unittest.main()
