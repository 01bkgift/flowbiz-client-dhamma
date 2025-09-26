"""Pydantic models for SeoMetadataAgent."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SeoMetadataInput(BaseModel):
    """Input schema for generating SEO metadata."""

    topic_title: str = Field(description="หัวข้อหลักของวิดีโอ")
    script_summary: str = Field(description="สรุปเนื้อหาหลักของสคริปต์")
    citations_list: list[str] = Field(
        default_factory=list, description="รายการอ้างอิงที่ต้องใส่ใน metadata"
    )
    primary_keywords: list[str] = Field(
        description="คีย์เวิร์ดหลักสำหรับใช้ใน metadata", min_length=1
    )

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("topic_title", "script_summary")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("ต้องระบุข้อความอย่างน้อย 1 ตัวอักษร")
        return value

    @field_validator("citations_list")
    @classmethod
    def validate_citations(cls, value: list[str]) -> list[str]:
        return [item for item in value if item.strip()]

    @field_validator("primary_keywords")
    @classmethod
    def validate_keywords(cls, value: list[str]) -> list[str]:
        cleaned = [kw.strip() for kw in value if kw.strip()]
        if not cleaned:
            raise ValueError("ต้องระบุ primary keywords อย่างน้อย 1 คำ")
        return cleaned


class SelfCheck(BaseModel):
    """Self-validation flags for metadata constraints."""

    title_within_60: bool
    description_within_400: bool
    tags_15_25: bool
    hashtags_le_8: bool = Field(alias="hashtags_≤8")

    model_config = ConfigDict(populate_by_name=True)


class MetaInfo(BaseModel):
    """Metadata summary for generated output."""

    title_length: int
    description_length: int
    tags_count: int
    hashtags_count: int
    primary_keyword_in_title: bool
    no_clickbait: bool
    self_check: SelfCheck


class SeoMetadataOutput(BaseModel):
    """Output schema for SEO metadata generation."""

    title: str
    description: str
    tags: list[str]
    meta: MetaInfo
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        if len(value) < 15 or len(value) > 25:
            raise ValueError("จำนวน tag ต้องอยู่ระหว่าง 15 ถึง 25 รายการ")
        return value
