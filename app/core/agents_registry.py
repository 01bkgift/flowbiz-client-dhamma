# รายการเอเจนต์สำหรับเมนู UI (ครบตามที่ผู้ใช้ยืนยัน + งานระบบ)
AGENTS: list[dict[str, str]] = [
    {
        "key": "trend_scout",
        "name": "Trend Scout Agent",
        "desc": "วิเคราะห์เทรนด์และเสนอหัวข้อคอนเทนต์",
    },
    {
        "key": "topic_prioritizer",
        "name": "Topic Prioritizer Agent",
        "desc": "จัดลำดับความสำคัญของหัวข้อ",
    },
    {
        "key": "research_retrieval",
        "name": "Research Retrieval Agent",
        "desc": "ค้นคว้าข้อมูลสนับสนุน",
    },
    {"key": "script_outline", "name": "Script Outline Agent", "desc": "สร้างโครงสคริปต์"},
    {"key": "script_writer", "name": "Script Writer Agent", "desc": "เขียนสคริปต์วิดีโอ"},
    {
        "key": "doctrine_validator",
        "name": "Doctrine Validator Agent",
        "desc": "ตรวจความถูกต้องตามหลักธรรม",
    },
    {
        "key": "localization_subtitle",
        "name": "Localization & Subtitle Agent",
        "desc": "ทำซับไตเติล/โลคัลไลซ์",
    },
    {"key": "voiceover", "name": "Voiceover Agent", "desc": "สร้างเสียงบรรยาย"},
    {
        "key": "visual_asset",
        "name": "Visual Asset Agent",
        "desc": "สร้างภาพ/วิดีทัศน์ประกอบ",
    },
    {
        "key": "thumbnail_generator",
        "name": "Thumbnail Generator Agent",
        "desc": "ออกแบบภาพปก",
    },
    {
        "key": "seo_metadata",
        "name": "SEO & Metadata Agent",
        "desc": "ตั้งค่า SEO/Metadata",
    },
    {
        "key": "scheduling_publish",
        "name": "Scheduling & Publishing Agent",
        "desc": "ตั้งเวลาลงและเผยแพร่",
    },
    {
        "key": "analytics_retention",
        "name": "Analytics & Retention Agent",
        "desc": "วิเคราะห์ผลและการรักษาผู้ชม",
    },
    {
        "key": "experiment_orchestrator",
        "name": "Experiment Orchestrator Agent",
        "desc": "ทดลอง A/B และกลยุทธ์",
    },
    {
        "key": "growth_forecast",
        "name": "Growth Forecast Agent",
        "desc": "พยากรณ์การเติบโต",
    },
    {"key": "feedback_loop", "name": "Feedback Loop Agent", "desc": "ป้อนกลับเพื่อปรับปรุง"},
    {"key": "dashboard", "name": "Dashboard Agent", "desc": "ศูนย์รวมสถานะ/ตัวชี้วัด"},
    {"key": "error_flag", "name": "Error/Flag Agent", "desc": "แจ้งเตือน/ธงข้อผิดพลาด"},
    {
        "key": "legal_compliance",
        "name": "Legal/Compliance Agent",
        "desc": "ข้อกฎหมาย/ลิขสิทธิ์",
    },
    {"key": "notification", "name": "Notification Agent", "desc": "แจ้งเตือนระบบ"},
    {"key": "integration", "name": "Integration Agent", "desc": "เชื่อมต่อระบบภายนอก"},
    {"key": "monitoring", "name": "Monitoring Agent", "desc": "เฝ้าระวังระบบ"},
    {"key": "data_sync", "name": "Data Sync Agent", "desc": "ซิงก์ข้อมูล"},
    {
        "key": "prompt_pack",
        "name": "Prompt Pack/Workflow Diagram",
        "desc": "แพ็กพร็อมต์/ไดอะแกรม",
    },
    {"key": "agent_template", "name": "Agent Template", "desc": "แม่แบบสร้างเอเจนต์"},
    {
        "key": "multi_channel_publish",
        "name": "Multi-Channel Publish Agent",
        "desc": "เผยแพร่หลายแพลตฟอร์ม",
    },
    {"key": "security", "name": "Security Agent", "desc": "ความปลอดภัย"},
    {"key": "advanced_bi", "name": "Advanced BI Agent", "desc": "วิเคราะห์เชิงลึก"},
    {
        "key": "personalization",
        "name": "Personalization Agent",
        "desc": "ปรับเนื้อหาเฉพาะบุคคล",
    },
    {
        "key": "user_feedback_collector",
        "name": "User Feedback Collector Agent",
        "desc": "เก็บความเห็นผู้ใช้",
    },
    {
        "key": "community_insight",
        "name": "Community Insight Agent",
        "desc": "อินไซต์จากชุมชน",
    },
    {"key": "auto_labeling", "name": "Auto-Labeling Agent", "desc": "ติดป้ายกำกับอัตโนมัติ"},
    {
        "key": "training_data",
        "name": "Training Data Agent",
        "desc": "เตรียมชุดข้อมูลสำหรับเทรน/วิเคราะห์",
    },
    {
        "key": "format_conversion",
        "name": "Format Conversion Agent",
        "desc": "แปลงรูปแบบคอนเทนต์หลายแพลตฟอร์ม",
    },
    {
        "key": "backup_archive",
        "name": "Backup/Archive Agent",
        "desc": "สำรองและจัดเก็บข้อมูล",
    },
    {
        "key": "data_enrichment",
        "name": "Data Enrichment Agent",
        "desc": "เติม metadata/บริบท/อ้างอิง",
    },
    # งานระบบเพิ่มเติม
    {
        "key": "inventory_index",
        "name": "Inventory/Index Agent",
        "desc": "สแกนไฟล์เอเจนต์/พร็อมต์ บันทึกรายการและข้อมูลเบื้องต้น",
    },
    {
        "key": "orchestrator_pipeline",
        "name": "Orchestrator Pipeline",
        "desc": "รัน pipeline ตามไฟล์ YAML (เชนงานหลายขั้นตอน)",
    },
]
