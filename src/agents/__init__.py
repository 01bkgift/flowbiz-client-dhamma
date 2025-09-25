"""
agents - โมดูลรวม AI Agents ทั้งหมด

ปัจจุบันมี:
- TrendScoutAgent: วิเคราะห์เทรนด์และสร้างหัวข้อคอนเทนต์
- TopicPrioritizerAgent: จัดลำดับความสำคัญของหัวข้อ
- ResearchRetrievalAgent: ค้นหาและดึงข้อความอ้างอิงจากคลังธรรมะ
- ScriptOutlineAgent: สร้างโครงร่างวิดีโอ Long-form
- ScriptWriterAgent: เรียบเรียงสคริปต์วิดีโอจากโครงร่างและข้อความอ้างอิง
"""

from .research_retrieval.agent import ResearchRetrievalAgent
from .research_retrieval.model import ResearchRetrievalInput, ResearchRetrievalOutput
from .script_outline.agent import ScriptOutlineAgent
from .script_outline.model import ScriptOutlineInput, ScriptOutlineOutput
from .script_writer.agent import ScriptWriterAgent
from .script_writer.model import ScriptWriterInput, ScriptWriterOutput
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
]
