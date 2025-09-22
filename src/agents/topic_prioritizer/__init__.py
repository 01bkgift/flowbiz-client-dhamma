"""
TopicPrioritizerAgent v1 - Agent สำหรับสร้าง Content Calendar
"""

from .agent import TopicPrioritizerAgent
from .model import (
    CandidateTopic,
    DiversitySummary,
    HistoricalContext,
    MetaInfo,
    # Legacy models for backward compatibility
    PrioritizedTopic,
    PriorityInput,
    PriorityOutput,
    PriorityScore,
    Rules,
    ScheduledTopic,
    SelfCheck,
    UnscheduledTopic,
    WeeksCapacity,
)

__all__ = [
    "TopicPrioritizerAgent",
    "CandidateTopic",
    "PriorityInput",
    "PriorityOutput",
    "WeeksCapacity",
    "Rules",
    "HistoricalContext",
    "ScheduledTopic",
    "UnscheduledTopic",
    "DiversitySummary",
    "SelfCheck",
    "MetaInfo",
    # Legacy exports
    "PrioritizedTopic",
    "PriorityScore",
]
