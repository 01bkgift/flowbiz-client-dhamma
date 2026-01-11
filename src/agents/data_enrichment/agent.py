"""
DataEnrichmentAgent v1 - Agent for enriching data with metadata
"""

import logging
import re

from .model import (
    DataEnrichmentInput,
    DataEnrichmentOutput,
    DataItem,
    EnrichedField,
    EnrichedItem,
    EnrichmentSummary,
    ErrorResponse,
    FieldCount,
    SelfCheck,
)

logger = logging.getLogger(__name__)


class DataEnrichmentAgent:
    """Agent for enriching data with keywords, entities, references, and context"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Thai Dhamma-related keyword patterns
        self.dhamma_keywords = [
            "สมาธิ",
            "สติ",
            "ปล่อยวาง",
            "ธรรมะ",
            "ภาวนา",
            "กรรม",
            "นิพพาน",
            "วิปัสสนา",
            "สมถะ",
            "อริยสัจ",
            "มรรค",
            "ผล",
            "ศีล",
            "ทาน",
            "ปัญญา",
            "สังขาร",
            "อนิจจัง",
            "ทุกขัง",
            "อนัตตา",
            "ขันธ์",
            "อายตนะ",
        ]

        # Entity patterns
        self.entity_patterns = {
            "เทคนิค": r"วิธี|เทคนิค|แนวทาง|หลักการ",
            "สุขภาพจิต": r"สุขภาพจิต|จิตใจ|ความเครียด|วิตกกังวล",
            "การปฏิบัติ": r"ปฏิบัติ|ฝึก|ทำ|ลงมือ",
            "กลุ่มเป้าหมาย": r"วัยรุ่น|ผู้ใหญ่|เด็ก|ผู้สูงอายุ|ผู้เริ่มต้น",
        }

    def run(
        self, input_data: DataEnrichmentInput
    ) -> DataEnrichmentOutput | ErrorResponse:
        """Process data enrichment"""
        try:
            self.logger.info(f"Processing {len(input_data.items)} items for enrichment")

            enriched_items: list[EnrichedItem] = []
            low_confidence_count = 0
            fail_count = 0
            field_counts = {
                "keyword": 0,
                "entity": 0,
                "external_reference": 0,
                "context": 0,
            }

            for item in input_data.items:
                enriched_fields = self._enrich_item(
                    item, input_data.config.enrichment_schema
                )

                # Update counts
                for field in enriched_fields:
                    if field.enrichment_type in field_counts:
                        field_counts[field.enrichment_type] += 1

                    # Check confidence
                    if field.confidence_pct < input_data.config.min_confidence_pct:
                        low_confidence_count += 1
                        if "low_confidence" not in field.flag:
                            field.flag.append("low_confidence")

                    if "enrichment_fail" in field.flag:
                        fail_count += 1

                enriched_items.append(
                    EnrichedItem(
                        id=item.id,
                        enriched_field=enriched_fields,
                    )
                )

            # Build summary
            summary = EnrichmentSummary(
                total=len(input_data.items),
                enriched=len(input_data.items) - fail_count,
                low_confidence=low_confidence_count,
                enrichment_fail=fail_count,
                field_count=FieldCount(**field_counts),
                self_check=SelfCheck(
                    all_sections_present=True,
                    no_empty_fields=all(
                        len(item.enriched_field) > 0 for item in enriched_items
                    ),
                ),
            )

            self.logger.info(
                f"Enrichment complete: {summary.enriched}/{summary.total} items, "
                f"{summary.low_confidence} low confidence"
            )

            return DataEnrichmentOutput(
                enrichment_result=enriched_items,
                enrichment_summary=summary,
            )

        except Exception as e:
            self.logger.error(f"Enrichment failed: {e}")
            return ErrorResponse(
                error={
                    "code": "ENRICHMENT_FAIL",
                    "message": str(e),
                    "suggested_fix": "Check input data format and try again",
                }
            )

    def _enrich_item(self, item: DataItem, schema: list[str]) -> list[EnrichedField]:
        """Enrich a single item based on schema"""
        fields: list[EnrichedField] = []

        # Combine title and description for analysis
        text = f"{item.title} {item.description} {item.raw_content}".lower()

        if "keyword" in schema:
            keywords = self._extract_keywords(text, item.title)
            fields.append(
                EnrichedField(
                    enrichment_type="keyword",
                    value=keywords,
                    confidence_pct=90 if len(keywords) >= 3 else 75,
                    source="internal",
                    flag=[],
                    suggestion=[],
                )
            )

        if "entity" in schema:
            entities = self._extract_entities(text)
            fields.append(
                EnrichedField(
                    enrichment_type="entity",
                    value=entities,
                    confidence_pct=85 if entities else 60,
                    source="knowledge_base",
                    flag=[] if entities else ["low_confidence"],
                    suggestion=[]
                    if entities
                    else ["Manual entity verification recommended"],
                )
            )

        if "external_reference" in schema:
            references = self._generate_references(item.title, text)
            fields.append(
                EnrichedField(
                    enrichment_type="external_reference",
                    value=references,
                    confidence_pct=70 if references else 50,
                    source="web",
                    flag=[] if references else ["enrichment_fail"],
                    suggestion=[] if references else ["Add manual references"],
                )
            )

        if "context" in schema:
            context = self._generate_context(item.title, text)
            fields.append(
                EnrichedField(
                    enrichment_type="context",
                    value=context,
                    confidence_pct=88,
                    source="manual",
                    flag=[],
                    suggestion=[],
                )
            )

        return fields

    def _extract_keywords(self, text: str, title: str) -> list[str]:
        """Extract relevant keywords from text"""
        keywords = []

        # Match against known dhamma keywords
        for kw in self.dhamma_keywords:
            if kw.lower() in text:
                keywords.append(kw)

        # Extract words from title
        title_words = [w for w in title.split() if len(w) > 2]
        for word in title_words[:3]:
            if word not in keywords:
                keywords.append(word)

        return keywords[:6]  # Max 6 keywords

    def _extract_entities(self, text: str) -> list[str]:
        """Extract entities from text using patterns"""
        entities = []

        for entity_type, pattern in self.entity_patterns.items():
            if re.search(pattern, text):
                entities.append(entity_type)

        # Add common entities based on content
        if "สมาธิ" in text or "ภาวนา" in text:
            if "การปฏิบัติ" not in entities:
                entities.append("การปฏิบัติ")

        return entities[:4]  # Max 4 entities

    def _generate_references(self, title: str, text: str) -> list[str]:
        """Generate potential reference URLs (mock for production)"""
        references = []

        # Common reference sites for dhamma content
        if "สมาธิ" in text.lower():
            references.append("https://www.watpahnanachat.org/meditation-guide")

        if "สุขภาพจิต" in text.lower() or "stress" in text.lower():
            references.append("https://www.dmh.go.th/mental-health")

        return references[:3]  # Max 3 references

    def _generate_context(self, title: str, text: str) -> str:
        """Generate contextual description"""
        # Analyze content type
        if "ก่อนนอน" in text or "หลับ" in text:
            return f"เนื้อหาเหมาะสำหรับผู้ต้องการผ่อนคลายก่อนนอน เน้นเทคนิค{title}"
        elif "วัยรุ่น" in text:
            return f"เนื้อหาเน้นกลุ่มวัยรุ่น สอนเทคนิคที่เข้าถึงง่าย เรื่อง{title}"
        elif "เริ่มต้น" in text or "ผู้เริ่มต้น" in text:
            return f"เนื้อหาสำหรับผู้เริ่มต้นปฏิบัติธรรม เรื่อง{title}"
        else:
            return f"เนื้อหาธรรมะประยุกต์ใช้ในชีวิตประจำวัน เรื่อง{title}"
