import unittest

from server.contract import ContractError
from server.verification.checks import (
    check_search_outcome,
    check_exact_file,
    check_transfer_receipt,
    check_checklist,
    check_fs_manifest,
    check_process_result,
    check_organize_manifest,
    check_open_document,
)


class VerificationTests(unittest.TestCase):
    def test_search_outcomes(self):
        self.assertTrue(check_search_outcome({
            "status": "succeeded",
            "data": {"candidates": [{"candidate_id": "c1", "name": "a.txt"}]},
        })["ok"])
        self.assertEqual(check_search_outcome({
            "status": "failed", "error": {"code": "no_match"},
        })["code"], "no_match")
        self.assertEqual(check_search_outcome({
            "status": "failed", "error": {"code": "invalid_args"},
        })["code"], "invalid_args")
        self.assertEqual(check_search_outcome({
            "status": "failed", "error": {"code": "unsupported_tool"},
        })["code"], "unsupported_tool")
        with self.assertRaises(ContractError):
            check_search_outcome({"status": "succeeded", "data": {"candidates": []}})

    def test_exact_file_identity(self):
        candidate = {"candidate_id": "c1", "size_bytes": 12, "digest": "abc"}
        approval = {"candidate_id": "c1"}
        check_exact_file(candidate, approval, {"candidate_id": "c1", "size_bytes": 12, "digest": "abc"})
        with self.assertRaises(ContractError):
            check_exact_file(candidate, {"candidate_id": "c2"}, {"candidate_id": "c1"})
        with self.assertRaises(ContractError):
            check_exact_file(candidate, approval, {"candidate_id": "c1", "size_bytes": 13, "digest": "abc"})

    def test_transfer_receipt_checks_both(self):
        evidence = {"size_bytes": 12, "digest": "abc"}
        check_transfer_receipt(evidence, {"authenticated": True, "size_bytes": 12, "digest": "abc"})
        with self.assertRaises(ContractError):
            check_transfer_receipt(evidence, {"authenticated": False, "size_bytes": 12, "digest": "abc"})
        with self.assertRaises(ContractError):
            check_transfer_receipt(evidence, {"authenticated": True, "size_bytes": 12, "digest": "changed"})

    def test_missing_fields_fail_closed(self):
        with self.assertRaises(ContractError):
            check_transfer_receipt({"size_bytes": 12}, {"authenticated": True, "size_bytes": 12})

    def test_checklist_content_matches(self):
        check_checklist(["a", "b"], ["a", "b"])
        with self.assertRaises(ContractError):
            check_checklist(["a"], ["a", "b"])

    def test_fs_manifest_shapes(self):
        self.assertTrue(check_fs_manifest({"entries": []}, "fs_list")["ok"])
        with self.assertRaises(ContractError):
            check_fs_manifest({}, "fs_list")
        good = {"path": "n.txt", "size_bytes": 2, "digest": "ab", "content": "hi"}
        self.assertTrue(check_fs_manifest(good, "fs_read")["ok"])
        self.assertTrue(check_fs_manifest(
            {"path": "n.txt", "size_bytes": 2, "digest": "ab", "binary": True},
            "fs_read")["ok"])
        with self.assertRaises(ContractError):
            check_fs_manifest({"path": "n.txt"}, "fs_write")

    def test_organize_manifest_counts(self):
        good = {"folder": "Santosh_Photos", "copied_count": 3,
                "duplicates_skipped": 1, "found": 4}
        self.assertEqual(check_organize_manifest(good)["copied"], 3)
        empty = {"folder": "Santosh_Photos", "copied_count": 0,
                 "duplicates_skipped": 0, "found": 0}
        self.assertTrue(check_organize_manifest(empty)["ok"])
        for bad in ({}, {"folder": "x"}, dict(good, copied_count=-1),
                    dict(good, found=2), dict(good, folder="")):
            with self.assertRaises(ContractError):
                check_organize_manifest(bad)

    def test_open_document_needs_name_and_identity(self):
        self.assertEqual(
            check_open_document({"name": "r.docx", "candidate_id": "c"})["name"],
            "r.docx")
        for bad in ({}, {"name": "r.docx"}, {"candidate_id": "c"}, {"name": ""}):
            with self.assertRaises(ContractError):
                check_open_document(bad)

    def test_process_result_needs_fields_not_zero_exit(self):
        self.assertEqual(
            check_process_result({"exit_code": 1, "stdout": "", "stderr": "x"})["exit_code"], 1)
        with self.assertRaises(ContractError):
            check_process_result({"stdout": "", "stderr": ""})


if __name__ == "__main__":
    unittest.main()
