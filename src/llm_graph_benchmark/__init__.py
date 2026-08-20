"""Method-neutral evaluation for document-to-knowledge-graph systems."""

from .bundle import BenchmarkBundle, SubmissionBundle
from .validation import ValidationIssue, ValidationResult

__all__ = [
    "BenchmarkBundle",
    "SubmissionBundle",
    "ValidationIssue",
    "ValidationResult",
]

__version__ = "0.1.0"
