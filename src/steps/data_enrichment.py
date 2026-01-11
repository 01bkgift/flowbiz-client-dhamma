"""
DataEnrichment Pipeline Step
Wraps DataEnrichmentAgent for orchestrator integration
Supports input_from to receive data from ResearchRetrieval
"""

import json
import logging
from pathlib import Path
from typing import TypedDict

from agents.data_enrichment import (
    DataEnrichmentAgent,
    DataEnrichmentInput,
    DataItem,
    EnrichmentConfig,
)
from agents.data_enrichment.model import ErrorResponse
from automation_core.base_step import BaseStep

logger = logging.getLogger(__name__)


class DataEnrichmentContext(TypedDict, total=False):
    """Context for DataEnrichmentStep"""

    # Input from previous step (via input_from in pipeline)
    input_file: str  # Path to research_bundle.json or similar

    # Direct input (alternative to input_file)
    items: list[dict]  # Direct item list

    # Agent parameters
    data_type: str  # video, topic, research, script
    enrichment_schema: list[str]  # keyword, entity, external_reference, context
    min_confidence_pct: int

    # Output location
    output_dir: str


class DataEnrichmentStep(BaseStep):
    """Pipeline step for data enrichment with metadata, keywords, and context"""

    def __init__(self):
        super().__init__(
            step_id="data_enrichment",
            step_type="DataEnrichment",
            version="1.0.0",
        )
        self.agent = DataEnrichmentAgent()

    def execute(self, context: DataEnrichmentContext) -> dict:
        """
        Execute data enrichment

        Input context (from input_from):
        - input_file: Path to research_bundle.json from ResearchRetrieval

        Direct input (alternative):
        - items: List of items with id, title, description

        Agent parameters:
        - data_type: Type of data (default: video)
        - enrichment_schema: Types of enrichment (default: all)
        - min_confidence_pct: Minimum confidence threshold (default: 70)

        Output:
        - data_enrichment.json: DataEnrichmentOutput serialized
        """
        # Get items from input_from file or direct input
        items = self._get_items(context)

        if not items:
            return {
                "status": "error",
                "error": "No items to enrich. Provide input_file or direct items.",
            }

        # Build agent input
        try:
            agent_input = DataEnrichmentInput(
                data_type=context.get("data_type", "video"),
                items=[DataItem(**item) for item in items],
                config=EnrichmentConfig(
                    enrichment_schema=context.get(
                        "enrichment_schema",
                        ["keyword", "entity", "external_reference", "context"],
                    ),
                    min_confidence_pct=int(context.get("min_confidence_pct", 70)),
                ),
            )
        except Exception as e:
            self.logger.error(f"Failed to create agent input: {e}")
            return {"status": "error", "error": f"Invalid input parameters: {e}"}

        # Run agent
        self.logger.info(
            f"Running DataEnrichment for {len(items)} items, "
            f"schema: {agent_input.config.enrichment_schema}"
        )
        result = self.agent.run(agent_input)

        # Handle error response
        if isinstance(result, ErrorResponse):
            self.logger.error(f"Agent returned error: {result.error}")
            return {
                "status": "error",
                "error": result.error.get("message", "Unknown error"),
                "error_code": result.error.get("code"),
                "suggested_fix": result.error.get("suggested_fix"),
            }

        # Save output
        output_dir = Path(context.get("output_dir", "output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "data_enrichment.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(
            f"Enriched {result.enrichment_summary.enriched}/{result.enrichment_summary.total} items, "
            f"{result.enrichment_summary.low_confidence} low confidence"
        )

        return {
            "status": "success",
            "output_file": str(output_path),
            "total_items": result.enrichment_summary.total,
            "enriched_count": result.enrichment_summary.enriched,
            "low_confidence_count": result.enrichment_summary.low_confidence,
            "field_counts": result.enrichment_summary.field_count.model_dump(),
        }

    def _get_items(self, context: DataEnrichmentContext) -> list[dict]:
        """
        Extract items from context.
        Priority: 1) Direct items, 2) From input_file
        """
        # Priority 1: Direct items
        direct_items = context.get("items", [])
        if direct_items:
            return direct_items

        # Priority 2: From input_file (set by orchestrator via input_from)
        input_file = context.get("input_file")
        if input_file:
            input_path = Path(input_file)
            if input_path.exists():
                try:
                    with open(input_path, encoding="utf-8") as f:
                        data = json.load(f)

                    # Handle research_bundle.json (from ResearchRetrieval)
                    if "passages" in data:
                        # Convert passages to items
                        items = []
                        for i, passage in enumerate(data.get("passages", [])[:5]):
                            items.append(
                                {
                                    "id": f"P{i + 1:03d}",
                                    "title": passage.get(
                                        "title", data.get("topic", "")
                                    ),
                                    "description": passage.get("snippet", ""),
                                    "raw_content": passage.get("content", ""),
                                }
                            )
                        return items

                    # Handle topics_ranked.json (from TopicPrioritizer)
                    if "scheduled" in data or "topics" in data:
                        topics = data.get("scheduled", data.get("topics", []))
                        items = []
                        for i, topic in enumerate(topics[:5]):
                            items.append(
                                {
                                    "id": f"T{i + 1:03d}",
                                    "title": topic.get(
                                        "topic_title", topic.get("title", "")
                                    ),
                                    "description": topic.get(
                                        "notes", topic.get("reason", "")
                                    ),
                                }
                            )
                        return items

                    # Handle generic items list
                    if "items" in data:
                        return data["items"]

                except Exception as e:
                    self.logger.warning(f"Failed to read input file {input_path}: {e}")

        return []
