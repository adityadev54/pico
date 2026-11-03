import unittest
from server.contract import ContractError
from server.verification.checks import check_document_result, check_open_document

class DocumentVerificationTests(unittest.TestCase):
 def test_exact_manifest_is_required(self):
  data={'path':'Homework.pdf','size_bytes':123,'digest':'a'*64,'pages':1}
  evidence={'size_bytes':123,'digest':'a'*64}
  self.assertTrue(check_document_result(data,evidence)['ok'])
  for bad in ({'path':'../escape.pdf'},{'size_bytes':True},{'digest':'fake'},{'pages':0}):
   with self.assertRaises(ContractError):check_document_result({**data,**bad},evidence)
  with self.assertRaises(ContractError):check_document_result(data,{**evidence,'digest':'b'*64})

 def test_legacy_app_result_is_explicit_and_matches_requested_name(self):
  data={'name':'ChatGPT','opened_as':'approved_app','opened_app_id':'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'}
  self.assertTrue(check_open_document(data,'Chat GPT')['ok'])
  for query in (None,'Homework',''):
   with self.assertRaises(ContractError):check_open_document(data,query)
  with self.assertRaises(ContractError):check_open_document({**data,'opened_app_id':'not-an-id'},'ChatGPT')
  with self.assertRaises(ContractError):check_open_document({'name':'Homework.pdf'},'Homework.pdf')
