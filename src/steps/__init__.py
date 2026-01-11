from .trend_scout import TrendScoutStep
from .topic_prioritizer import TopicPrioritizerStep

# Register step for orchestrator
STEP_REGISTRY = {
    "TrendScout": TrendScoutStep,
    "TopicPrioritizer": TopicPrioritizerStep,
}
