"""Unit tests for server/contracts.py."""
import json
from pathlib import Path
import unittest
from pydantic import ValidationError

from server.contracts import (
    EstablishedMessage,
    PicoMessage,
    RequestMessage,
    ToolCallMessage,
    ToolResultMessage,
    ProgressMessage,
    VerificationResultMessage,
    ApprovalRequestMessage,
    ApprovalGrantMessage,
    ClarificationQuestionMessage,
    ClarificationAnswerMessage,
    PhoneReceiptMessage,
    CancelMessage,
    ErrorMessage,
    ErrorCode,
    TaskState,
    parse_pico_message,
)


class TestContracts(unittest.TestCase):
    def setUp(self):
        self.examples_file = (
            Path(__file__).resolve().parents[2] / "docs" / "contract-examples.json"
        )

    def test_parse_contract_examples(self):
        """Verify that all messages in docs/contract-examples.json parse accurately."""
        with open(self.examples_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        examples = data["examples"]
        self.assertEqual(len(examples), 5)

        for ex in examples:
            msg = parse_pico_message(ex)
            self.assertEqual(msg.contract_version, 1)
            self.assertEqual(msg.task_id, "task-example")

        # Check types individually
        self.assertIsInstance(parse_pico_message(examples[0]), RequestMessage)
        self.assertIsInstance(parse_pico_message(examples[1]), ToolCallMessage)
        self.assertIsInstance(parse_pico_message(examples[2]), ToolResultMessage)
        self.assertIsInstance(parse_pico_message(examples[3]), ProgressMessage)
        self.assertIsInstance(parse_pico_message(examples[4]), VerificationResultMessage)

    def test_extra_fields_forbidden(self):
        """Hard rule: extra fields must be rejected."""
        invalid_request = {
            "contract_version": 1,
            "task_id": "t1",
            "type": "request",
            "device_id": "d1",
            "text": "Search docs",
            "malicious_untrusted_field": "injected",
        }
        with self.assertRaises(ValidationError):
            parse_pico_message(invalid_request)

    def test_wrong_contract_version_rejected(self):
        invalid_request = {
            "contract_version": 2,
            "task_id": "t1",
            "type": "request",
            "device_id": "d1",
            "text": "Search docs",
        }
        with self.assertRaises(ValidationError):
            parse_pico_message(invalid_request)

    def test_proposed_approval_messages(self):
        """Test approval request and grant serialization/validation."""
        req_data = {
            "contract_version": 1,
            "task_id": "t1",
            "type": "approval_request",
            "step_id": "s1",
            "approval_id": "appr_123",
            "operation": "transfer_selected_file",
            "candidate_id": "cand_999",
            "candidate_name": "quarterly-report.pdf",
            "task_version": 1,
            "expires_at_unix": 1793259999,
        }
        msg = parse_pico_message(req_data)
        self.assertIsInstance(msg, ApprovalRequestMessage)
        self.assertEqual(msg.operation, "transfer_selected_file")

        grant_data = {
            "contract_version": 1,
            "task_id": "t1",
            "type": "approval_grant",
            "approval_id": "appr_123",
            "approved": True,
            "candidate_id": "cand_999",
            "task_version": 1,
        }
        grant_msg = parse_pico_message(grant_data)
        self.assertIsInstance(grant_msg, ApprovalGrantMessage)
        self.assertTrue(grant_msg.approved)

    def test_proposed_phone_receipt_message(self):
        receipt_data = {
            "contract_version": 1,
            "task_id": "t1",
            "type": "phone_receipt",
            "step_id": "s2",
            "candidate_id": "cand_999",
            "received_bytes": 1024,
            "received_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        }
        msg = parse_pico_message(receipt_data)
        self.assertIsInstance(msg, PhoneReceiptMessage)
        self.assertEqual(msg.received_bytes, 1024)

    def test_proposed_error_message(self):
        err_data = {
            "contract_version": 1,
            "task_id": "t1",
            "type": "error",
            "error_code": "permission_denied",
            "message": "Computer helper denied access to sensitive path",
        }
        msg = parse_pico_message(err_data)
        self.assertIsInstance(msg, ErrorMessage)
        self.assertEqual(msg.error_code, ErrorCode.PERMISSION_DENIED)


if __name__ == "__main__":
    unittest.main()

