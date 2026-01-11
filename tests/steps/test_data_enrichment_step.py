"""
Integration tests for DataEnrichmentStep
"""

import json
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from steps.data_enrichment import DataEnrichmentStep


class TestDataEnrichmentStep:
    """Test suite for DataEnrichmentStep"""
    
    def test_step_initialization(self):
        """Test step can be instantiated"""
        step = DataEnrichmentStep()
        assert step.step_id == "data_enrichment"
        assert step.step_type == "DataEnrichment"
        assert step.version == "1.0.0"
    
    def test_execute_with_direct_items(self, tmp_path):
        """Test execution with direct items input"""
        step = DataEnrichmentStep()
        result = step.execute({
            "items": [
                {"id": "V001", "title": "ปล่อยวางก่อนนอน", "description": "สมาธิก่อนนอน"},
                {"id": "V002", "title": "สมาธิสั้นในวัยรุ่น", "description": "แก้ปัญหาสมาธิสั้น"},
            ],
            "output_dir": str(tmp_path),
            "enrichment_schema": ["keyword", "entity", "context"],
        })
        
        assert result["status"] == "success"
        assert "output_file" in result
        assert Path(result["output_file"]).exists()
        assert result["enriched_count"] == 2
    
    def test_execute_with_example_file(self, tmp_path):
        """Test with existing examples/data_enrichment_input.json"""
        example_file = Path("examples/data_enrichment_input.json")
        if not example_file.exists():
            pytest.skip("Example file not found")
        
        # Load example and convert format
        with open(example_file, encoding="utf-8") as f:
            data = json.load(f)
        
        items = [
            {"id": item["id"], "title": item["title"], "description": ""}
            for item in data.get("items", [])
        ]
        
        step = DataEnrichmentStep()
        result = step.execute({
            "items": items,
            "output_dir": str(tmp_path),
            "enrichment_schema": data.get("schema", ["keyword", "entity", "context"]),
        })
        
        assert result["status"] == "success"
        assert result["enriched_count"] > 0
    
    def test_execute_with_input_file(self, tmp_path):
        """Test execution with input_file (simulating input_from)"""
        # Create mock research_bundle.json
        mock_data = {
            "topic": "สมาธิภาวนา",
            "passages": [
                {
                    "title": "การฝึกสมาธิเบื้องต้น",
                    "snippet": "วิธีฝึกสมาธิสำหรับผู้เริ่มต้น",
                    "content": "การนั่งสมาธิเริ่มจากการกำหนดลมหายใจ",
                },
            ],
        }
        
        input_file = tmp_path / "research_bundle.json"
        input_file.write_text(json.dumps(mock_data, ensure_ascii=False), encoding="utf-8")
        
        step = DataEnrichmentStep()
        result = step.execute({
            "input_file": str(input_file),
            "output_dir": str(tmp_path),
        })
        
        assert result["status"] == "success"
        assert result["enriched_count"] >= 1
    
    def test_all_enrichment_types(self, tmp_path):
        """Test all enrichment schema types"""
        step = DataEnrichmentStep()
        result = step.execute({
            "items": [
                {"id": "T001", "title": "สมาธิสำหรับวัยรุ่น", "description": "วิธีฝึกสมาธิ"}
            ],
            "output_dir": str(tmp_path),
            "enrichment_schema": ["keyword", "entity", "external_reference", "context"],
        })
        
        assert result["status"] == "success"
        
        # Check field counts
        counts = result.get("field_counts", {})
        assert counts.get("keyword", 0) >= 1
        assert counts.get("context", 0) >= 1
    
    def test_low_confidence_threshold(self, tmp_path):
        """Test low confidence detection"""
        step = DataEnrichmentStep()
        result = step.execute({
            "items": [{"id": "X001", "title": "Test", "description": ""}],
            "output_dir": str(tmp_path),
            "min_confidence_pct": 95,  # High threshold
        })
        
        assert result["status"] == "success"
        # With high threshold, some fields might be low confidence
    
    def test_empty_items(self, tmp_path):
        """Test error handling for empty items"""
        step = DataEnrichmentStep()
        result = step.execute({
            "items": [],
            "output_dir": str(tmp_path),
        })
        
        assert result["status"] == "error"
    
    def test_missing_input(self, tmp_path):
        """Test error handling for missing input"""
        step = DataEnrichmentStep()
        result = step.execute({
            "input_file": str(tmp_path / "nonexistent.json"),
            "output_dir": str(tmp_path),
        })
        
        assert result["status"] == "error"
