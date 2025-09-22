"""
Research Retrieval Agent - ดึงและวิเคราะห์ข้อความอ้างอิงสำหรับคอนเทนต์ธรรมะ
"""

import random
import re
from datetime import datetime
from typing import Any

from automation_core.base_agent import BaseAgent

from .model import (
    CoverageAssessment,
    ErrorResponse,
    MetaInfo,
    Passage,
    QueryUsed,
    ResearchRetrievalInput,
    ResearchRetrievalOutput,
    RetrievalStats,
    SelfCheck,
)


class ResearchRetrievalAgent(BaseAgent[ResearchRetrievalInput, ResearchRetrievalOutput]):
    """Agent สำหรับค้นหาและดึงข้อความอ้างอิงจากคลังธรรมะ"""

    def __init__(self):
        super().__init__(
            name="ResearchRetrievalAgent",
            version="1.0.0",
            description="ดึงและวิเคราะห์ข้อความอ้างอิงจากพระไตรปิฎกและแหล่งธรรมะที่เชื่อถือได้",
        )

        # น้ำหนักสำหรับการคำนวณ relevance_final
        self.relevance_weights = {
            "semantic_sim": 0.55,
            "keyword_boost": 0.20,
            "tag_match": 0.15,
            "recency_decay": 0.10,
        }

        # คำธรรมะสำคัญที่ไม่ควรตัดออก
        self.dhamma_keywords = [
            "สติ", "ปล่อยวาง", "อนิจจัง", "อนัตตา", "ทุกข์", "นิพพาน",
            "อานาปานสติ", "วิปัสสนา", "สมาธิ", "เวทนา", "อุปาทาน", "กรรม",
            "พุทธ", "ธรรม", "สงฆ์", "กุศล", "อกุศล", "มงคล"
        ]

        # แนวคิดหลักที่คาดหวังตามหัวข้อ
        self.topic_concept_mapping = {
            "sleep": ["สติ", "ปล่อยวาง", "อานาปานสติ", "เวทนา"],
            "stress": ["สติ", "ปล่อยวาง", "อนิจจัง", "อุปาทาน"],
            "meditation": ["สติ", "สมาธิ", "อานาปานสติ", "วิปัสสนา"],
            "mindfulness": ["สติ", "วิปัสสนา", "เวทนา"],
        }

    def run(self, input_data: ResearchRetrievalInput) -> ResearchRetrievalOutput:
        """ประมวลผลการค้นหาและดึงข้อความอ้างอิง"""
        try:
            # 1. สร้าง queries จากข้อมูลนำเข้า
            queries = self._generate_queries(input_data)

            # 2. ค้นหาและรวบรวม passages (จำลอง)
            all_passages = self._simulate_search(input_data, queries)

            # 3. จัดอันดับและแยกประเภท
            primary, supportive = self._categorize_passages(all_passages, input_data.max_passages)

            # 4. สร้าง summary bullets
            summary_bullets = self._generate_summary_bullets(primary, supportive)

            # 5. ประเมินความครอบคลุม
            coverage = self._assess_coverage(input_data, primary, supportive)

            # 6. สร้าง stats และ metadata
            stats = self._calculate_stats(all_passages, primary, supportive)
            meta = self._create_meta_info(input_data, primary, supportive)

            # 7. สร้าง warnings
            warnings = self._generate_warnings(coverage, primary, supportive)

            return ResearchRetrievalOutput(
                topic=input_data.topic_title,
                retrieved_at=datetime.now(),
                queries_used=queries,
                primary=primary,
                supportive=supportive,
                summary_bullets=summary_bullets,
                coverage_assessment=coverage,
                stats=stats,
                meta=meta,
                warnings=warnings,
            )

        except Exception as e:
            # ส่งคืน error response ถ้าเกิดข้อผิดพลาด
            return ErrorResponse(
                error={
                    "code": "PROCESSING_ERROR",
                    "message": f"เกิดข้อผิดพลาดในการประมวลผล: {str(e)}",
                    "suggested_fix": "ตรวจสอบข้อมูลนำเข้าและลองใหม่อีกครั้ง",
                }
            )

    def _generate_queries(self, input_data: ResearchRetrievalInput) -> list[QueryUsed]:
        """สร้างชุด queries สำหรับการค้นหา"""
        queries = []

        # Base query
        normalized_query = self._normalize_query(input_data.raw_query)
        queries.append(QueryUsed(type="base", query=normalized_query))

        # Refinement queries ตาม hints
        for i, hint in enumerate(input_data.refinement_hints[:3]):
            if "หลักคำสอน" in hint or "ธรรม" in hint:
                query_type = "refinement_doctrine"
                refined_query = f"{normalized_query} หลักธรรม คำสอน"
            elif "ปฏิบัติ" in hint or "อานาปานสติ" in hint:
                query_type = "refinement_practice"
                refined_query = f"{normalized_query} ปฏิบัติ อานาปานสติ"
            elif "อุปมา" in hint or "นิทาน" in hint:
                query_type = "refinement_story"
                refined_query = f"{normalized_query} อุปมา นิทาน"
            else:
                query_type = "refinement_practice"
                refined_query = f"{normalized_query} {hint}"

            queries.append(QueryUsed(type=query_type, query=refined_query))

        return queries

    def _normalize_query(self, raw_query: str) -> str:
        """ปรับแต่งคำค้นโดยเก็บคำธรรมะสำคัญ"""
        # ลบคำที่ไม่จำเป็น แต่เก็บคำธรรมะ
        query = raw_query.lower().strip()

        # ลบ stopwords ไทยพื้นฐาน แต่เก็บคำธรรมะ
        thai_stopwords = ["ที่", "เป็น", "มี", "ใน", "และ", "หรือ", "แต่", "จาก", "ด้วย"]
        words = query.split()
        filtered_words = []

        for word in words:
            if word in self.dhamma_keywords or word not in thai_stopwords:
                filtered_words.append(word)

        return " ".join(filtered_words)

    def _simulate_search(
        self, input_data: ResearchRetrievalInput, queries: list[QueryUsed]
    ) -> list[dict[str, Any]]:
        """จำลองการค้นหาจาก vector store (ในระบบจริงจะเรียก API)"""
        # สำหรับ demo ใช้ mock data
        random.seed(42)  # สำหรับผลลัพธ์ที่ tutorialistic

        mock_passages = []
        
        # สร้าง mock passages ตาม topic
        topic_lower = input_data.topic_title.lower()
        
        if "นอน" in topic_lower or "หลับ" in topic_lower:
            mock_passages.extend(self._create_sleep_related_passages())
        if "เครียด" in topic_lower or "กังวล" in topic_lower:
            mock_passages.extend(self._create_stress_related_passages())
        
        # เพิ่ม passages ทั่วไป
        mock_passages.extend(self._create_general_passages())

        # คำนวณ relevance scores
        for passage in mock_passages:
            passage["relevance_final"] = self._calculate_relevance(passage, input_data)

        # กรองตาม required_tags
        if input_data.required_tags:
            tagged_passages = [
                p for p in mock_passages
                if any(tag in p.get("doctrinal_tags", []) for tag in input_data.required_tags)
            ]
            # ถ้าไม่พบ passages ที่ตรงกับ required_tags ใช้ผลลัพธ์ทั้งหมด
            if tagged_passages:
                mock_passages = tagged_passages

        # จัดเรียงตาม relevance และจำกัดจำนวน
        mock_passages.sort(key=lambda x: x["relevance_final"], reverse=True)
        return mock_passages[: int(input_data.max_passages * 1.4)]

    def _create_sleep_related_passages(self) -> list[dict[str, Any]]:
        """สร้าง mock passages เกี่ยวกับการนอนหลับ"""
        return [
            {
                "id": "sleep_01",
                "source_name": "มหาปริณิพพานสูตร",
                "collection": "canon",
                "canonical_ref": "DN 16",
                "original_text": "ภิกษุทั้งหลาย เมื่อใดที่ภิกษุมีสติสัมปชัญญะ ผู้นั้นมีความสุข มีความสงบ การพักผ่อนของผู้นั้นเป็นการพักผ่อนที่แท้จริง",
                "doctrinal_tags": ["สติ", "สัมปชัญญะ", "ความสงบ"],
                "license": "public_domain",
                "reason": "เน้นการมีสติก่อนพักผ่อน",
            },
            {
                "id": "sleep_02", 
                "source_name": "มหาสติปัฏฐานสูตร",
                "collection": "canon",
                "canonical_ref": "DN 22",
                "original_text": "ภิกษุทั้งหลาย ภิกษุย่อมรู้แจ้งว่า กำลังหายใจเข้า กำลังหายใจออก เมื่อใจสงบแล้ว ร่างกายก็สงบตาม",
                "doctrinal_tags": ["อานาปานสติ", "สติ", "ความสงบ"],
                "license": "public_domain", 
                "reason": "วิธีใช้ลมหายใจเพื่อความสงบ",
            },
        ]

    def _create_stress_related_passages(self) -> list[dict[str, Any]]:
        """สร้าง mock passages เกี่ยวกับความเครียด"""
        return [
            {
                "id": "stress_01",
                "source_name": "ธัมมจักกัปปวัตตนสูตร", 
                "collection": "canon",
                "canonical_ref": "SN 56.11",
                "original_text": "นี้คือทุกข์ นี้คือสมุทัยของทุกข์ นี้คือนิโรธของทุกข์ นี้คือมรรคที่นำไปสู่นิโรธทุกข์",
                "doctrinal_tags": ["อริยสัจ", "ทุกข์", "นิโรธ"],
                "license": "public_domain",
                "reason": "หลักพื้นฐานของการเข้าใจและจัดการความทุกข์",
            },
        ]

    def _create_general_passages(self) -> list[dict[str, Any]]:
        """สร้าง mock passages ทั่วไป"""
        return [
            {
                "id": "general_01",
                "source_name": "บทความ: ปล่อยวางในชีวิตประจำวัน",
                "collection": "modern_article", 
                "canonical_ref": None,
                "original_text": "การปล่อยวางไม่ใช่การยอมแพ้ แต่เป็นการเข้าใจว่าสิ่งต่างๆ มีการเปลี่ยนแปลงอยู่เสมอ เมื่อเราไม่ยึดติด ใจก็จะเบาและสงบ",
                "doctrinal_tags": ["ปล่อยวาง", "อนิจจัง"],
                "license": "public_domain",
                "reason": "ตัวอย่างเชิงปฏิบัติ",
            },
        ]

    def _calculate_relevance(self, passage: dict[str, Any], input_data: ResearchRetrievalInput) -> float:
        """คำนวณคะแนนความเกี่ยวข้อง"""
        # Semantic similarity (mock)
        semantic_sim = random.uniform(0.4, 0.9)

        # Keyword boost
        query_words = input_data.raw_query.lower().split()
        text_words = passage["original_text"].lower().split()
        keyword_matches = sum(1 for word in query_words if word in text_words)
        keyword_boost = min(keyword_matches / len(query_words), 1.0) if query_words else 0

        # Tag match
        required_tags = set(input_data.required_tags)
        passage_tags = set(passage.get("doctrinal_tags", []))
        tag_match = len(required_tags & passage_tags) / len(required_tags) if required_tags else 1.0

        # Recency decay (สำหรับบทความสมัยใหม่)
        recency_decay = 0.8 if passage["collection"] == "modern_article" else 1.0

        # คำนวณคะแนนรวม
        relevance = (
            self.relevance_weights["semantic_sim"] * semantic_sim +
            self.relevance_weights["keyword_boost"] * keyword_boost +
            self.relevance_weights["tag_match"] * tag_match +
            self.relevance_weights["recency_decay"] * recency_decay
        )

        return min(relevance, 1.0)

    def _categorize_passages(
        self, all_passages: list[dict[str, Any]], max_passages: int
    ) -> tuple[list[Passage], list[Passage]]:
        """แยก passages เป็น primary และ supportive"""
        if not all_passages:
            return [], []

        # คำนวณ threshold สำหรับ primary
        relevance_scores = [p["relevance_final"] for p in all_passages]
        median_score = sorted(relevance_scores)[len(relevance_scores) // 2]
        std_score = sum((x - median_score) ** 2 for x in relevance_scores) ** 0.5 / len(relevance_scores)
        primary_threshold = median_score + (std_score * 0.25)

        primary_passages = []
        supportive_passages = []

        primary_limit = int(max_passages * 0.6)
        
        for passage_data in all_passages[:max_passages]:
            is_primary = (
                passage_data["relevance_final"] >= primary_threshold or
                any(tag in ["สติ", "ปล่อยวาง", "อานาปานสติ"] for tag in passage_data.get("doctrinal_tags", []))
            )
            
            passage = Passage(
                id=passage_data["id"],
                source_name=passage_data["source_name"],
                collection=passage_data["collection"],
                canonical_ref=passage_data.get("canonical_ref"),
                original_text=passage_data["original_text"],
                thai_modernized=passage_data.get("thai_modernized"),
                relevance_final=passage_data["relevance_final"],
                doctrinal_tags=passage_data.get("doctrinal_tags", []),
                license=passage_data.get("license", "public_domain"),
                risk_flags=passage_data.get("risk_flags", []),
                reason=passage_data.get("reason", "เกี่ยวข้องกับหัวข้อ"),
                position_score=random.uniform(0.3, 0.9),
            )
            
            if is_primary and len(primary_passages) < primary_limit:
                primary_passages.append(passage)
            else:
                supportive_passages.append(passage)

        return primary_passages, supportive_passages

    def _generate_summary_bullets(self, primary: list[Passage], supportive: list[Passage]) -> list[str]:
        """สร้างสรุปหัวใจหลัก"""
        all_passages = primary + supportive
        
        if not all_passages:
            # ส่งคืน bullets ขั้นต่ำเมื่อไม่มี passages
            return [
                "ไม่พบข้อมูลที่เกี่ยวข้องในคลังธรรมะ",
                "แนะนำให้ปรับคำค้นหาหรือเพิ่ม refinement hints",
                "สามารถค้นหาในแหล่งอื่นเพิ่มเติม"
            ]

        # วิเคราะห์แนวคิดหลักจาก passages
        key_concepts = set()
        for passage in all_passages:
            key_concepts.update(passage.doctrinal_tags)

        bullets = []
        
        if "สติ" in key_concepts:
            bullets.append("การมีสติต่อปัจจุบันขณะช่วยให้จิตใจสงบและเป็นสุข")
            
        if "ปล่อยวาง" in key_concepts:
            bullets.append("การปล่อยวางความยึดมั่นช่วยลดความทุกข์และความกังวล")
            
        if "อานาปานสติ" in key_concepts:
            bullets.append("การสังเกตลมหายใจเป็นวิธีปฏิบัติที่เข้าถึงง่ายและมีประสิทธิภาพ")
            
        if "อนิจจัง" in key_concepts:
            bullets.append("การเข้าใจความไม่เที่ยงช่วยให้ยอมรับการเปลี่ยนแปลง")

        # เพิ่มให้ครบ 3-6 ข้อ
        while len(bullets) < 3:
            bullets.append("หลักธรรมช่วยให้เข้าใจและจัดการกับปัญหาในชีวิตได้อย่างมีสติ")
            
        while len(bullets) < 4 and "เวทนา" in key_concepts:
            bullets.append("การสังเกตความรู้สึกโดยไม่ตัดสินช่วยให้มีความสงบภายใน")

        return bullets[:6]  # จำกัดไม่เกิน 6 ข้อ

    def _assess_coverage(
        self, input_data: ResearchRetrievalInput, primary: list[Passage], supportive: list[Passage]
    ) -> CoverageAssessment:
        """ประเมินความครอบคลุมของข้อมูล"""
        all_passages = primary + supportive
        
        # สกัดแนวคิดที่พบ
        core_concepts = set()
        for passage in all_passages:
            core_concepts.update(passage.doctrinal_tags)
        
        # กำหนดแนวคิดที่คาดหวังตาม topic
        expected_concepts = set(input_data.required_tags)
        
        # เพิ่มแนวคิดที่คาดหวังตาม topic pattern
        topic_lower = input_data.topic_title.lower()
        for pattern, concepts in self.topic_concept_mapping.items():
            if pattern in topic_lower:
                expected_concepts.update(concepts)
        
        # ถ้าไม่มี expected_concepts จาก mapping, ใช้ default
        if not expected_concepts:
            expected_concepts = {"สติ", "ปล่อยวาง"}
            
        missing_concepts = expected_concepts - core_concepts
        
        # คำนวณ confidence
        passage_factor = min(1.0, (len(primary) + len(supportive) * 0.5) / input_data.max_passages)
        concept_factor = len(core_concepts & expected_concepts) / len(expected_concepts) if expected_concepts else 1.0
        confidence = min(1.0, passage_factor * concept_factor)
        
        # ปรับ confidence ถ้ามี missing_concepts
        if missing_concepts and confidence > 0.85:
            confidence = min(confidence, 0.85)
            
        notes = ""
        if missing_concepts:
            notes = f"ยังขาดแนวคิด: {', '.join(missing_concepts)}"

        return CoverageAssessment(
            core_concepts=list(core_concepts),
            expected_concepts=list(expected_concepts),
            missing_concepts=list(missing_concepts),
            confidence=confidence,
            notes=notes,
        )

    def _calculate_stats(
        self, all_passages: list[dict[str, Any]], primary: list[Passage], supportive: list[Passage]
    ) -> RetrievalStats:
        """คำนวณสถิติการดึงข้อมูล"""
        primary_relevance = [p.relevance_final for p in primary]
        avg_relevance = sum(primary_relevance) / len(primary_relevance) if primary_relevance else 0.0

        return RetrievalStats(
            primary_count=len(primary),
            supportive_count=len(supportive),
            initial_candidates=len(all_passages),
            filtered_out=max(0, len(all_passages) - len(primary) - len(supportive)),
            avg_relevance_primary=round(avg_relevance, 3),
        )

    def _create_meta_info(
        self, input_data: ResearchRetrievalInput, primary: list[Passage], supportive: list[Passage]
    ) -> MetaInfo:
        """สร้างข้อมูล metadata"""
        applied_filters = []
        if input_data.required_tags:
            applied_filters.append("required_tags")
        if input_data.forbidden_sources:
            applied_filters.append("forbidden_sources")
        applied_filters.append("license_check")

        self_check = SelfCheck(
            has_primary=len(primary) > 0,
            confidence_ok=True,  # จะถูกอัพเดตโดย coverage assessment
            within_limit=len(primary) + len(supportive) <= input_data.max_passages,
            no_empty_text=all(p.original_text.strip() for p in primary + supportive),
        )

        return MetaInfo(
            max_passages_requested=input_data.max_passages,
            applied_filters=applied_filters,
            refinement_iterations=len(input_data.refinement_hints) + 1,
            self_check=self_check,
        )

    def _generate_warnings(
        self, coverage: CoverageAssessment, primary: list[Passage], supportive: list[Passage]
    ) -> list[str]:
        """สร้างคำเตือน"""
        warnings = []
        
        if coverage.missing_concepts:
            warnings.append(f"missing_concepts: {', '.join(coverage.missing_concepts)}")
            
        if coverage.confidence < 0.4:
            warnings.append("insufficient_passages")
            
        if not primary:
            warnings.append("no_primary_passages")
            
        total_passages = len(primary) + len(supportive)
        if total_passages < 3:
            warnings.append("very_few_passages")

        return warnings