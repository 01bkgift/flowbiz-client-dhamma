"""
TopicPrioritizer Pipeline Step
Wraps TopicPrioritizerAgent for orchestrator integration
"""

import json
import logging
from pathlib import Path
from typing import Literal, TypedDict

from agents.topic_prioritizer import (
    CandidateTopic,
    HistoricalContext,
    PriorityInput,
    Rules,
    TopicPrioritizerAgent,
    WeeksCapacity,
)
from automation_core.base_step import BaseStep

logger = logging.getLogger(__name__)


class TopicPrioritizerContext(TypedDict, total=False):
    """Context for TopicPrioritizerStep"""

    input_file: str  # Path to trend_candidates.json
    output_dir: str
    strategy_focus: Literal["fast_growth", "evergreen_balance", "depth_series"]
    weeks: int
    longform_per_week: int
    shorts_per_week: int


class TopicPrioritizerStep(BaseStep):
    """Pipeline step for topic prioritization and content calendar generation"""

    def __init__(self):
        super().__init__(
            step_id="topic_prioritizer",
            step_type="TopicPrioritizer",
            version="1.0.0",
        )
        self.agent = TopicPrioritizerAgent()

    def execute(self, context: TopicPrioritizerContext) -> dict:
        """
        Execute topic prioritization

        Input context:
        - input_file: Path to trend_candidates.json from TrendScout
        - strategy_focus: "fast_growth" | "evergreen_balance" | "depth_series"
        - weeks: Number of weeks to plan (default: 4)
        - longform_per_week: Longform videos per week (default: 2)
        - shorts_per_week: Shorts per week (default: 4)

        Output:
        - topics_ranked.json: PriorityOutput serialized
        """
        # Load input from TrendScout
        input_file = Path(context.get("input_file", "output/trend_candidates.json"))

        if not input_file.exists():
            self.logger.error(f"Input file not found: {input_file}")
            return {
                "status": "error",
                "error": f"Input file not found: {input_file}",
            }

        try:
            with open(input_file, encoding="utf-8") as f:
                trend_data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load input file: {e}")
            return {
                "status": "error",
                "error": f"Failed to load input file: {e}",
            }

        # Convert topics to CandidateTopic format
        candidate_topics = self._convert_to_candidates(trend_data.get("topics", []))

        if not candidate_topics:
            self.logger.warning("No candidate topics found in input")
            return {
                "status": "error",
                "error": "No candidate topics in input file",
            }

        # Build PriorityInput
        agent_input = PriorityInput(
            candidate_topics=candidate_topics,
            strategy_focus=context.get("strategy_focus", "evergreen_balance"),
            capacity=WeeksCapacity(
                weeks=int(context.get("weeks", 4)),
                longform_per_week=int(context.get("longform_per_week", 2)),
                shorts_per_week=int(context.get("shorts_per_week", 4)),
            ),
            rules=Rules(),
            historical_context=HistoricalContext(
                recent_longform_avg_views=3200,
                recent_shorts_avg_views=1800,
                pillar_performance={},
            ),
        )

        # Run agent
        self.logger.info(
            f"Running TopicPrioritizer with {len(candidate_topics)} topics, "
            f"strategy: {agent_input.strategy_focus}"
        )
        result = self.agent.run(agent_input)

        # Save output
        output_dir = Path(context.get("output_dir", "output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "topics_ranked.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(
            f"Prioritized {result.meta.scheduled_count} topics, "
            f"{result.meta.unscheduled_count} unscheduled"
        )

        return {
            "status": "success",
            "output_file": str(output_path),
            "scheduled_count": result.meta.scheduled_count,
            "unscheduled_count": result.meta.unscheduled_count,
            "strategy_focus": result.strategy_focus,
            "diversity_ok": result.meta.self_check.diversity_ok,
        }

    def _convert_to_candidates(self, topics: list[dict]) -> list[CandidateTopic]:
        """Convert TrendScout output topics to CandidateTopic format"""
        candidates = []

        for topic in topics:
            # Map from TrendScout/mock_topics format to CandidateTopic
            # TrendScout uses: title, category, keywords, priority, why_now
            # CandidateTopic needs: title, pillar, predicted_14d_views, scores, reason

            try:
                candidate = CandidateTopic(
                    title=topic.get("title", ""),
                    pillar=topic.get("category", topic.get("pillar", "ธรรมะประยุกต์")),
                    predicted_14d_views=topic.get(
                        "predicted_14d_views",
                        topic.get("priority", 3) * 2000  # Estimate from priority
                    ),
                    scores=topic.get("scores", {
                        "search_intent": 0.7,
                        "freshness": 0.6,
                        "evergreen": 0.5,
                        "brand_fit": 0.8,
                        "composite": 0.65,
                    }),
                    reason=topic.get("reason", topic.get("why_now", "")),
                )
                candidates.append(candidate)
            except Exception as e:
                self.logger.warning(f"Failed to convert topic {topic.get('title')}: {e}")
                continue

        return candidates
