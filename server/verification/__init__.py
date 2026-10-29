"""Verification checks. Santosh owns this package.

Consume native evidence + authenticated phone receipts; never accept
model narration as proof.
"""
from .checks import (
    check_search_outcome,
    check_exact_file,
    check_transfer_receipt,
    check_checklist,
    check_fs_manifest,
    check_process_result,
    check_organize_manifest,
    check_open_document,
)

__all__ = [
    "check_search_outcome",
    "check_exact_file",
    "check_transfer_receipt",
    "check_checklist",
    "check_fs_manifest",
    "check_process_result",
    "check_organize_manifest",
    "check_open_document",
]
