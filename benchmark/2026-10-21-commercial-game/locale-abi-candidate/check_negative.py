#!/usr/bin/env python3
"""Counterexamples call the actual delivery ELF ABI guard."""
import copy,unittest
from pathlib import Path
from check_elf import dynsyms,validate_abi
D=Path(__file__).resolve().parent
class Counterexamples(unittest.TestCase):
 def setUp(self):
  self.b=dynsyms((D/'evidence/baseline-symbols.txt').read_text());self.c=dynsyms((D/'evidence/candidate-symbols.txt').read_text())
 def test_exact(self):self.assertEqual(len(validate_abi(self.b,self.c)),5)
 def bad(self,name,value):
  self.c[name]=value
  with self.assertRaises(AssertionError):validate_abi(self.b,self.c)
 def test_ctype_function(self):self.bad('_ctype_@@LIBC',(8,'FUNC','GLOBAL','DEFAULT',False))
 def test_ctype_array257(self):self.bad('_ctype_@@LIBC',(257,'OBJECT','GLOBAL','DEFAULT',False))
 def test_ctype_pointer32(self):self.bad('_ctype_@@LIBC',(4,'OBJECT','GLOBAL','DEFAULT',False))
 def test_wrong_version(self):
  self.c['_ctype_@@LIBM']=self.c.pop('_ctype_@@LIBC')
  with self.assertRaises(AssertionError):validate_abi(self.b,self.c)
 def test_unversioned_candidate_rejected(self):
  self.c['_ctype_']=self.c.pop('_ctype_@@LIBC')
  with self.assertRaises(AssertionError):validate_abi(self.b,self.c)
 def test_added_assert2(self):self.bad('__assert2@@LIBC',(4,'FUNC','GLOBAL','DEFAULT',False))
 def test_old_object_size(self):self.bad('__sF@@LIBC',(712,'OBJECT','GLOBAL','DEFAULT',False))
 def test_missing_old_atfork(self):
  del self.c['__register_atfork@@LIBC']
  with self.assertRaises(AssertionError):validate_abi(self.b,self.c)
if __name__=='__main__':unittest.main()
