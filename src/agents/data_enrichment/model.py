"""
Pydantic Models for DataEnrichmentAgent v1
Schema for enriching data with metadata, keywords, entities, and references
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class EnrichmentConfig(BaseModel):
    """Configuration for enrichment process"""

    enrichment_schema: list[str] = Field(
        default=["keyword", "entity", "external_reference", "context"],
        description="Types of enrichment to apply",
    )
    min_confidence_pct: int = Field(
        default=70, description="Minimum confidence percentage threshold"
    )


class DataItem(BaseModel):
    """Single data item to enrich"""

    id: str = Field(description="Unique identifier")
    title: str = Field(description="Item title")
    description: str = Field(default="", description="Item description")
    raw_content: str = Field(default="", description="Raw content for enrichment")


class DataEnrichmentInput(BaseModel):
    """Input for DataEnrichmentAgent v1"""

    data_type: Literal["video", "topic", "research", "script"] = Field(
        default="video", description="Type of data being enriched"
    )
    items: list[DataItem] = Field(description="Items to enrich")
    config: EnrichmentConfig = Field(
        default_factory=EnrichmentConfig, description="Enrichment configuration"
    )

    @field_validator("items")
    @classmethod
    def validate_items(cls, v):
        if not v:
            raise ValueError("At least one item is required for enrichment")
        return v


class EnrichedField(BaseModel):
    """Single enriched field"""

    enrichment_type: Literal["keyword", "entity", "external_reference", "context"] = (
        Field(description="Type of enrichment")
    )
    value: str | list[str] = Field(description="Enriched value(s)")
    confidence_pct: int = Field(description="Confidence percentage (0-100)")
    source: Literal["internal", "knowledge_base", "web", "manual", "external"] = Field(
        description="Source of enrichment"
    )
    flag: list[str] = Field(default_factory=list, description="Flags for this field")
    suggestion: list[str] = Field(default_factory=list, description="Suggestions")

    @field_validator("confidence_pct")
    @classmethod
    def validate_confidence(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Confidence must be between 0 and 100")
        return v


class EnrichedItem(BaseModel):
    """Item with enriched fields"""

    id: str = Field(description="Original item ID")
    enriched_field: list[EnrichedField] = Field(description="List of enriched fields")


class FieldCount(BaseModel):
    """Count of enrichments by type"""

    keyword: int = Field(default=0)
    entity: int = Field(default=0)
    external_reference: int = Field(default=0)
    context: int = Field(default=0)


class SelfCheck(BaseModel):
    """Self-check results"""

    all_sections_present: bool = Field(description="All required sections are present")
    no_empty_fields: bool = Field(description="No critical empty fields")


class EnrichmentSummary(BaseModel):
    """Summary of enrichment results"""

    total: int = Field(description="Total items processed")
    enriched: int = Field(description="Successfully enriched items")
    low_confidence: int = Field(default=0, description="Items with low confidence")
    enrichment_fail: int = Field(default=0, description="Failed enrichments")
    field_count: FieldCount = Field(description="Count by enrichment type")
    self_check: SelfCheck = Field(description="Self-check results")


class DataEnrichmentOutput(BaseModel):
    """Output for DataEnrichmentAgent v1"""

    enrichment_result: list[EnrichedItem] = Field(description="Enriched items")
    enrichment_summary: EnrichmentSummary = Field(description="Summary of enrichment")


class ErrorResponse(BaseModel):
    """Error response"""

    error: dict[str, str] = Field(
        description="Error details with code, message, suggested_fix"
    )
