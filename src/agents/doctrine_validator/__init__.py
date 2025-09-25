"""DoctrineValidatorAgent - ตรวจสอบความถูกต้องตามหลักธรรมของสคริปต์วิดีโอ"""

from .agent import DoctrineValidatorAgent
from .model import (
    DoctrineValidatorInput,
    DoctrineValidatorOutput,
    Passage,
    Passages,
    SegmentValidation,
)

__all__ = [
    "DoctrineValidatorAgent",
    "DoctrineValidatorInput",
    "DoctrineValidatorOutput",
    "Passage",
    "Passages",
    "SegmentValidation",
]
