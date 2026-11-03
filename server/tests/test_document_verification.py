import unittest
from server.contract import ContractError
from server.verification.checks import check_document_result

class DocumentVerificationTests(unittest.TestCase):
 def test_exact_manifest_is_required(self):
  data={'path':'Homework.pdf','size_bytes':123,'digest':'a'*64,'pages':1}
  evidence={'size_bytes':123,'digest':'a'*64}
  self.assertTrue(check_document_result(data,evidence)['ok'])
  for bad in ({'path':'../escape.pdf'},{'size_bytes':True},{'digest':'fake'},{'pages':0}):
   with self.assertRaises(ContractError):check_document_result({**data,**bad},evidence)
  with self.assertRaises(ContractError):check_document_result(data,{**evidence,'digest':'b'*64})
