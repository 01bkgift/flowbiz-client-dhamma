"""agents - โมดูลรวม AI Agents ทั้งหมด"""

# ruff: noqa: I001

from __future__ import annotations

from typing import Any

from .data_sync import (
    DataSyncAgent,
    DataSyncLogEntry,
    DataSyncPayload,
    DataSyncRequest,
    DataSyncResponse,
    SyncData,
    SyncRule,
)
from .error_flag import (
    AgentError as ErrorFlagAgentError,
    AgentLog as ErrorFlagAgentLog,
    CriticalItem as ErrorFlagCriticalItem,
    ErrorFlagAgent,
    ErrorFlagInput,
    ErrorFlagOutput,
    WarningItem as ErrorFlagWarningItem,
)
from .localization_subtitle.agent import LocalizationSubtitleAgent
from .localization_subtitle.model import (
    LocalizationSubtitleInput,
    LocalizationSubtitleMeta,
    LocalizationSubtitleOutput,
    SubtitleSegment,
)
from .multi_channel_publish import (
    ChannelPublishPayload as MultiChannelPublishChannelPayload,
    MultiChannelPublishAgent,
    MultiChannelPublishInput,
    MultiChannelPublishLogEntry,
    MultiChannelPublishOutput,
    PublishAssets as MultiChannelPublishAssets,
    PublishRequest as MultiChannelPublishRequest,
)
from .personalization import (
    EngagementMetrics as PersonalizationEngagementMetrics,
    PersonalizedRecommendation,
    PersonalizationAgent,
    PersonalizationConfig,
    PersonalizationInput,
    PersonalizationMeta,
    PersonalizationOutput,
    PersonalizationRequest,
    RecommendationItem as PersonalizationRecommendationItem,
    TrendInterest as PersonalizationTrendInterest,
    UserProfile as PersonalizationUserProfile,
    ViewHistoryItem as PersonalizationViewHistoryItem,
)
from .research_retrieval.agent import ResearchRetrievalAgent
from .research_retrieval.model import ResearchRetrievalInput, ResearchRetrievalOutput
from .scheduling_publishing.agent import SchedulingPublishingAgent
from .scheduling_publishing.model import (
    AudienceAnalytics,
    ContentCalendarEntry,
    ScheduleConstraints,
    SchedulingInput,
    SchedulingOutput,
)
from .script_outline.agent import ScriptOutlineAgent
from .script_outline.model import ScriptOutlineInput, ScriptOutlineOutput
from .script_writer.agent import ScriptWriterAgent
from .script_writer.model import ScriptWriterInput, ScriptWriterOutput
from .seo_metadata.agent import SeoMetadataAgent
from .seo_metadata.model import SeoMetadataInput, SeoMetadataOutput
from .topic_prioritizer.agent import TopicPrioritizerAgent
from .topic_prioritizer.model import PriorityInput, PriorityOutput
from .trend_scout.agent import TrendScoutAgent
from .trend_scout.model import TrendScoutInput, TrendScoutOutput

__all__ = [
    "TrendScoutAgent",
    "TrendScoutInput",
    "TrendScoutOutput",
    "TopicPrioritizerAgent",
    "PriorityInput",
    "PriorityOutput",
    "ResearchRetrievalAgent",
    "ResearchRetrievalInput",
    "ResearchRetrievalOutput",
    "MultiChannelPublishAgent",
    "MultiChannelPublishInput",
    "MultiChannelPublishOutput",
    "MultiChannelPublishRequest",
    "MultiChannelPublishAssets",
    "MultiChannelPublishChannelPayload",
    "MultiChannelPublishLogEntry",
    "ScriptOutlineAgent",
    "ScriptOutlineInput",
    "ScriptOutlineOutput",
    "PersonalizationAgent",
    "PersonalizationInput",
    "PersonalizationOutput",
    "PersonalizationRequest",
    "PersonalizedRecommendation",
    "PersonalizationMeta",
    "PersonalizationConfig",
    "PersonalizationTrendInterest",
    "PersonalizationUserProfile",
    "PersonalizationViewHistoryItem",
    "PersonalizationEngagementMetrics",
    "PersonalizationRecommendationItem",
    "ScriptWriterAgent",
    "ScriptWriterInput",
    "ScriptWriterOutput",
    "SeoMetadataAgent",
    "SeoMetadataInput",
    "SeoMetadataOutput",
    "SchedulingPublishingAgent",
    "SchedulingInput",
    "SchedulingOutput",
    "ContentCalendarEntry",
    "ScheduleConstraints",
    "AudienceAnalytics",
    "LocalizationSubtitleAgent",
    "LocalizationSubtitleInput",
    "LocalizationSubtitleOutput",
    "LocalizationSubtitleMeta",
    "SubtitleSegment",
    "DataSyncAgent",
    "DataSyncRequest",
    "DataSyncResponse",
    "DataSyncPayload",
    "DataSyncLogEntry",
    "SyncData",
    "SyncRule",
    "ErrorFlagAgent",
    "ErrorFlagInput",
    "ErrorFlagOutput",
    "ErrorFlagAgentLog",
    "ErrorFlagAgentError",
    "ErrorFlagCriticalItem",
    "ErrorFlagWarningItem",
]


def __getattr__(name: str) -> Any:  # pragma: no cover
    """Lazy-load optional DoctrineValidator exports.

    เหตุผล: ลดภาระการ import dependency หนักใน package-level import.
    """
    if name not in {
        "DoctrineValidatorAgent",
        "DoctrineValidatorInput",
        "DoctrineValidatorOutput",
    }:
        raise AttributeError(name)

    try:
        from .doctrine_validator import (  # type: ignore
            DoctrineValidatorAgent,
            DoctrineValidatorInput,
            DoctrineValidatorOutput,
        )
    except ModuleNotFoundError:
        return None

    globals().update(
        {
            "DoctrineValidatorAgent": DoctrineValidatorAgent,
            "DoctrineValidatorInput": DoctrineValidatorInput,
            "DoctrineValidatorOutput": DoctrineValidatorOutput,
        }
    )
    return globals()[name]
