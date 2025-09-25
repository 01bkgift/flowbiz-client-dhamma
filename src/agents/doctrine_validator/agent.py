"""DoctrineValidatorAgent - ตรวจสอบความถูกต้องตามหลักธรรมของสคริปต์"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from difflib import SequenceMatcher

from automation_core.base_agent import BaseAgent

from .model import (
    DoctrineValidatorInput,
    DoctrineValidatorOutput,
    ErrorResponse,
    MetaInfo,
    Passage,
    Passages,
    RewriteSuggestion,
    ScriptSegment,
    SegmentStatus,
    SegmentType,
    SegmentValidation,
    SelfCheck,
    Summary,
)

logger = logging.getLogger(__name__)

# Pattern สำหรับดึง citation เช่น [CIT:p123]
CITATION_PATTERN = re.compile(r"\[CIT:([^\]]+)\]")

SENSITIVE_PHRASES = [
    "สมาธิรักษาโรค",
    "หายป่วยแน่นอน",
    "รวยเร็ว",
    "รับรองหาย",
    "หายชัวร์",
]


class DoctrineValidatorAgent(
    BaseAgent[DoctrineValidatorInput, DoctrineValidatorOutput | ErrorResponse]
):
    """Agent สำหรับตรวจสอบความถูกต้องของสคริปต์ตามหลักธรรม"""

    def __init__(self) -> None:
        super().__init__(
            name="DoctrineValidatorAgent",
            version="1.0.0",
            description="ตรวจสอบ doctrinal integrity ของสคริปต์วิดีโอธรรมะ",
        )

    def run(
        self, input_data: DoctrineValidatorInput
    ) -> DoctrineValidatorOutput | ErrorResponse:
        try:
            logger.info("เริ่มตรวจสอบ doctrinal integrity")
            passage_map = self._build_passage_map(input_data.passages)

            processed_segments: list[SegmentValidation] = []
            summary_counter = {
                SegmentStatus.OK: 0,
                SegmentStatus.MISMATCH: 0,
                SegmentStatus.HALLUCINATION: 0,
                SegmentStatus.UNCLEAR: 0,
                SegmentStatus.MISSING_CITATION: 0,
                SegmentStatus.UNVERIFIABLE: 0,
            }
            rewrite_suggestions: list[RewriteSuggestion] = []
            global_warnings: list[str] = []
            unmatched_citation_count = 0

            total_teaching = 0
            teaching_with_citation = 0

            ignored_indexes = set(input_data.ignore_segments)

            for index, segment in enumerate(input_data.script_segments):
                if index in ignored_indexes:
                    continue

                normalized_type = segment.normalized_type
                if normalized_type == SegmentType.TEACHING:
                    total_teaching += 1

                segment_result = self._validate_segment(
                    index=index,
                    segment=segment,
                    normalized_type=normalized_type,
                    passage_map=passage_map,
                    strictness=input_data.strictness,
                    check_sensitive=input_data.check_sensitive,
                )

                if segment_result.status == SegmentStatus.MISSING_CITATION:
                    global_warnings.append(f"segment {index} มีเนื้อหาสอนแต่ไม่มี citation")
                if segment_result.status == SegmentStatus.UNVERIFIABLE:
                    global_warnings.append(
                        f"segment {index} ไม่สามารถตรวจสอบกับ passages ได้"
                    )
                if segment_result.status == SegmentStatus.MISMATCH:
                    global_warnings.append(
                        f"segment {index} มีเนื้อหาไม่ตรงกับ passages ที่อ้าง"
                    )
                if segment_result.status == SegmentStatus.HALLUCINATION:
                    global_warnings.append(f"segment {index} มีใจความที่ไม่พบใน passages")

                unmatched_citation_count += sum(
                    1 for warn in segment_result.warnings if "ไม่พบ" in warn
                )

                if segment_result.suggestions:
                    rewrite_suggestions.append(
                        RewriteSuggestion(
                            segment_index=index,
                            suggestion=segment_result.suggestions,
                        )
                    )

                if (
                    segment_result.matched_passages
                    and normalized_type == SegmentType.TEACHING
                ):
                    teaching_with_citation += 1

                processed_segments.append(segment_result)
                summary_counter[segment_result.status] += 1

            total_segments = len(processed_segments)

            if total_segments == 0:
                return self._create_error_response(
                    {
                        "code": "MISSING_DATA",
                        "message": "ไม่มี segment สำหรับตรวจสอบ",
                        "suggested_fix": "ตรวจสอบ ignore_segments หรือเพิ่ม script_segments",
                    }
                )

            citation_coverage = (
                teaching_with_citation / total_teaching if total_teaching else 1.0
            )
            ok_ratio = (
                summary_counter[SegmentStatus.OK] / total_segments
                if total_segments
                else 0
            )

            recommend_rewrite = (
                summary_counter[SegmentStatus.MISMATCH] > 0
                or summary_counter[SegmentStatus.HALLUCINATION] > 0
                or summary_counter[SegmentStatus.MISSING_CITATION] > 0
            )

            output = DoctrineValidatorOutput(
                validated_at=datetime.now(UTC).isoformat(),
                strictness=input_data.strictness,
                segments=processed_segments,
                summary=Summary(
                    total=total_segments,
                    ok=summary_counter[SegmentStatus.OK],
                    mismatch=summary_counter[SegmentStatus.MISMATCH],
                    hallucination=summary_counter[SegmentStatus.HALLUCINATION],
                    unclear=summary_counter[SegmentStatus.UNCLEAR],
                    missing_citation=summary_counter[SegmentStatus.MISSING_CITATION],
                    unverifiable=summary_counter[SegmentStatus.UNVERIFIABLE],
                    recommend_rewrite=recommend_rewrite,
                ),
                rewrite_suggestions=rewrite_suggestions,
                meta=MetaInfo(
                    citation_coverage=round(citation_coverage, 2),
                    overall_confidence=round(ok_ratio, 2),
                    strictness=input_data.strictness,
                    self_check=SelfCheck(
                        ok_ratio=round(ok_ratio, 2),
                        no_unmatched_citation=unmatched_citation_count == 0,
                        no_missing_citation=summary_counter[
                            SegmentStatus.MISSING_CITATION
                        ]
                        == 0,
                    ),
                ),
                warnings=global_warnings,
            )

            logger.info("ตรวจสอบสคริปต์เสร็จสิ้น %s segments", output.summary.total)
            return output
        except Exception as exc:  # pragma: no cover - unexpected error path
            logger.exception("เกิดข้อผิดพลาดระหว่างการตรวจสอบ")
            return self._create_error_response(
                {
                    "code": "SCHEMA_VIOLATION",
                    "message": str(exc),
                    "suggested_fix": "ตรวจสอบรูปแบบข้อมูลนำเข้าอีกครั้ง",
                }
            )

    def _create_error_response(self, error_dict: dict[str, str]) -> ErrorResponse:
        return ErrorResponse(error=error_dict)

    def _build_passage_map(self, passages: Passages) -> dict[str, Passage]:
        passage_map: dict[str, Passage] = {}
        for passage in passages.primary + passages.supportive:
            passage_map[passage.id] = passage
        return passage_map

    def _validate_segment(
        self,
        *,
        index: int,
        segment: ScriptSegment,
        normalized_type: SegmentType,
        passage_map: dict[str, Passage],
        strictness: str,
        check_sensitive: bool,
    ) -> SegmentValidation:
        citations = self._extract_citations(segment.text)
        matched_passages: list[str] = []
        warnings: list[str] = []
        suggestions: str | None = None
        notes: str | None = None
        status = SegmentStatus.OK

        if normalized_type == SegmentType.TEACHING and not citations:
            status = SegmentStatus.MISSING_CITATION
            suggestions = "เพิ่ม citation ให้กับใจความสอนหลัก"
        elif not citations:
            status = SegmentStatus.UNVERIFIABLE
            notes = "ไม่มี citation ให้ตรวจสอบ"

        # Sensitive phrase detection
        if check_sensitive:
            lowered = segment.text.lower()
            flagged = [
                phrase for phrase in SENSITIVE_PHRASES if phrase.lower() in lowered
            ]
            for phrase in flagged:
                warnings.append(f"พบถ้อยคำสุ่มเสี่ยง: '{phrase}'")

        similarity_records: list[float] = []
        for cit in citations:
            passage = passage_map.get(cit)
            if passage is None:
                warnings.append(f"Citation ID '{cit}' ไม่พบใน passages")
                status = SegmentStatus.UNVERIFIABLE
                continue

            if (
                strictness == "strict"
                and passage.license
                and passage.license != "public_domain"
            ):
                warnings.append(
                    f"Citation ID '{cit}' มี license '{passage.license}' ไม่ใช่ public_domain"
                )

            sentence_text = self._extract_sentence_with_citation(segment.text, cit)
            similarity = self._compute_similarity(sentence_text, passage)
            similarity_records.append(similarity)
            matched_passages.append(cit)

            if similarity < 0.6:
                status = SegmentStatus.MISMATCH
            elif similarity < 0.78 and status not in {
                SegmentStatus.MISMATCH,
                SegmentStatus.MISSING_CITATION,
            }:
                status = SegmentStatus.UNCLEAR

        if (
            not citations
            and normalized_type == SegmentType.TEACHING
            and strictness == "strict"
        ):
            warnings.append("โหมด strict ต้องมี citation สำหรับทุก teaching")

        if status == SegmentStatus.OK and similarity_records:
            avg_similarity = sum(similarity_records) / len(similarity_records)
            notes = f"similarity_avg={avg_similarity:.2f}"

        if (
            status == SegmentStatus.UNVERIFIABLE
            and normalized_type == SegmentType.TEACHING
        ):
            suggestions = "ตรวจสอบว่ามีการอ้างอิง passages ที่ถูกต้อง"

        return SegmentValidation(
            index=index,
            segment_type=normalized_type.value,
            text=segment.text,
            status=status,
            matched_passages=matched_passages,
            notes=notes,
            warnings=warnings,
            suggestions=suggestions,
        )

    def _extract_citations(self, text: str) -> list[str]:
        citations: list[str] = []
        for raw in CITATION_PATTERN.findall(text):
            for part in raw.split(","):
                cleaned = part.strip()
                if cleaned:
                    citations.append(cleaned)
        return citations

    def _extract_sentence_with_citation(self, text: str, citation_id: str) -> str:
        matches = list(CITATION_PATTERN.finditer(text))
        for match in matches:
            if citation_id in match.group(1).split(","):
                start = match.start()
                end = match.end()
                sentence_start = self._find_sentence_start(text, start)
                sentence_end = self._find_sentence_end(text, end)
                return text[sentence_start:sentence_end].strip()
        return text

    def _find_sentence_start(self, text: str, index: int) -> int:
        for pos in range(index, 0, -1):
            if text[pos - 1] in ".!?\n\u0e2f\u0e46\u0e4c":
                return pos
        return 0

    def _find_sentence_end(self, text: str, index: int) -> int:
        length = len(text)
        for pos in range(index, length):
            if text[pos] in ".!?\n\u0e2f\u0e46\u0e4c":
                return pos + 1
        return length

    def _compute_similarity(self, sentence: str, passage: Passage) -> float:
        target_texts = [passage.original_text]
        if passage.thai_modernized:
            target_texts.append(passage.thai_modernized)

        sentence_clean = self._normalize(sentence)
        best_score = 0.0
        for target in target_texts:
            target_clean = self._normalize(target)
            if not target_clean:
                continue
            score = SequenceMatcher(None, sentence_clean, target_clean).ratio()
            best_score = max(best_score, score)
        return best_score

    def _normalize(self, text: str) -> str:
        cleaned = CITATION_PATTERN.sub("", text)
        cleaned = cleaned.replace("\n", " ")
        return " ".join(cleaned.lower().split())
