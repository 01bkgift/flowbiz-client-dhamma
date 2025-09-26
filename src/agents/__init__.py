"""agents - โมดูลรวม AI Agents ทั้งหมด"""

from .localization_subtitle.agent import LocalizationSubtitleAgent
from .localization_subtitle.model import (
    LocalizationSubtitleInput,
    LocalizationSubtitleMeta,
    LocalizationSubtitleOutput,
    SubtitleSegment,
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
    "ScriptOutlineAgent",
    "ScriptOutlineInput",
    "ScriptOutlineOutput",
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
]

try:  # Optional dependency: sentence_transformers
    from .doctrine_validator import (
        DoctrineValidatorAgent,
        DoctrineValidatorInput,
        DoctrineValidatorOutput,
    )
except ModuleNotFoundError:  # pragma: no cover - optional dependency missing
    DoctrineValidatorAgent = None  # type: ignore[assignment]
    DoctrineValidatorInput = None  # type: ignore[assignment]
    DoctrineValidatorOutput = None  # type: ignore[assignment]
else:  # pragma: no cover - exercised when dependency is installed
    __all__.extend(
        [
            "DoctrineValidatorAgent",
            "DoctrineValidatorInput",
            "DoctrineValidatorOutput",
        ]
    )
