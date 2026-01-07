---
policy_version: "1.0.0"
effective_date: "2026-01-08"
last_reviewed: "2026-01-08"
next_review_due: "2026-04-08"
document_owner: "Repository Owner (natbkgift)"
backup_owner: "[ชื่อผู้รับผิดชอบสำรอง]"
language: "th-TH"
audit_classification: "SOC2-relevant"
---

# นโยบายการสร้างเนื้อหา YouTube ด้วย AI (Content Policy for YouTube AI Creator)

นโยบายอย่างเป็นทางการสำหรับการผลิต YouTube content ของช่อง **ธรรมะดีดี**  
เป็นไปตาม YouTube Partner Program policies และ ISO 27001 / SOC2 Type II controls

---

## A. วัตถุประสงค์และขอบเขต (Purpose & Scope)

### ✅ นโยบายนี้ครอบคลุม

- กระบวนการ Content ideation → Script → Voice → Video → Upload → Publish approval
- การใช้ AI เป็นเครื่องมือช่วยสร้างเนื้อหา (ไม่ใช่แทนที่มนุษย์)
- การบันทึกหลักฐานเพื่อ audit trail

### ❌ นโยบายนี้ไม่ครอบคลุม

- Platform migration หรือ multi-platform distribution
- Mass uploading automation
- Features ที่ยังไม่ได้ implement (soft-live, auto-publish)

### Target Channel

ช่อง **ธรรมะดีดี** — แต่ใช้เป็น template สำหรับ repository policy ทั่วไปได้

---

## B. คำนิยาม (Definitions)

| คำศัพท์ | คำนิยาม | เกณฑ์วัด |
|--------|---------|----------|
| **Original Content** | เนื้อหาที่สร้างขึ้นใหม่ทั้งหมดสำหรับช่องนี้ | 100% ของ script/visual ไม่ซ้ำกับแหล่งอื่น |
| **Reused Content** | เนื้อหาที่นำมาจากแหล่งอื่นโดยไม่มีการเปลี่ยนแปลงสาระสำคัญ | >30% ซ้ำกับ source เดิม |
| **AI-Assisted** | ใช้ AI เป็นเครื่องมือในการสร้าง แต่มี Human oversight | AI ทำได้ ≤60% ของ content |
| **Human-in-the-Loop** | มนุษย์มีส่วนร่วมตัดสินใจในทุกขั้นตอนสำคัญ | ≥2 human touchpoints ก่อน publish |
| **Low-effort Content** | เนื้อหาที่ใช้ effort น้อยมาก ไม่มี unique value | <2 ชั่วโมง human effort ต่อวิดีโอ |
| **Mass-produced** | ผลิตจำนวนมากแบบ template-based | >2 videos/วัน หรือ <4 ชั่วโมง gap |

---

## C. Non-negotiables — กฎเหล็ก (Hard Rules)

### C.1 Anti-Reuse (ห้ามนำเนื้อหาซ้ำ)

| # | กฎ |
|---|-----|
| 1 | SHALL NOT ใช้ third-party clips/audio โดยไม่มีสิทธิ์เป็นลายลักษณ์อักษร |
| 2 | SHALL NOT narrate Reddit/Wikipedia/news verbatim (>3 ประโยคติดต่อกัน) |
| 3 | SHALL NOT ใช้ footage ของ creator อื่นโดยไม่มี license |

### C.2 Anti-Deception (ห้ามหลอกลวง)

| # | กฎ |
|---|-----|
| 4 | SHALL NOT ใช้ metadata ที่ misleading (title ไม่ตรง content) |
| 5 | SHALL NOT อ้างว่าเป็น official/authority ที่ไม่ใช่ |
| 6 | SHALL NOT ใช้ fake thumbnails (ภาพไม่เกี่ยวกับเนื้อหา) |

### C.3 Anti-Spam (ห้าม spam)

| # | กฎ |
|---|-----|
| 7 | SHALL NOT upload >2 videos ใน 24 ชั่วโมง |
| 8 | SHALL NOT ใช้ loop videos หรือ wallpaper + music แบบซ้ำๆ |
| 9 | SHALL NOT ใช้ template เดิมซ้ำ >3 ครั้งต่อเดือน |

### C.4 Anti-AI Slop (ห้ามเนื้อหา AI คุณภาพต่ำ)

| # | กฎ |
|---|-----|
| 10 | SHALL NOT publish AI-generated content โดยไม่ผ่าน human review |
| 11 | SHALL NOT ใช้ monotone AI voice ตลอดทั้งวิดีโอ (ต้องมี variation) |
| 12 | SHALL NOT ใช้ AI visuals 100% โดยไม่มี human curation |

---

## D. Human-in-the-Loop Requirements (ข้อกำหนดการมีส่วนร่วมของมนุษย์)

> **Minimum Requirement: ≥2 จาก 5 ข้อต่อไปนี้ (บันทึกหลักฐานทุกข้อ)**

| # | Human Contribution | หลักฐานที่ต้องบันทึก | ที่เก็บ |
|---|-------------------|---------------------|--------|
| 1 | Human Outline/Angle | ไฟล์ outline ที่มี timestamp + author | artifacts/ หรือ Git commit |
| 2 | Human Script Review | Review comment/approval record | PR comment หรือ review log |
| 3 | Human Commentary (≥20% ของ script) | Highlight ส่วนที่เขียนเอง | ใน script file |
| 4 | Human Visual Curation | รายการ assets ที่เลือก + เหตุผล | decision log |
| 5 | Human Final Approval | Explicit approval record ก่อน publish | quality_gate record |

### Approval Authority

| ลำดับ | ผู้รับผิดชอบ | หมายเหตุ |
|-------|-------------|---------|
| 1 | Primary: Repository Owner | ผู้อนุมัติหลัก |
| 2 | Backup: [ระบุใน YAML header] | ถ้า Primary ไม่ available |
| 3 | Escalation | ถ้าทั้ง 2 ไม่ available ภายใน 24 ชม. → hold publish |

---

## E. Content Risk Matrix (เมทริกซ์ความเสี่ยงของเนื้อหา)

| Risk Level | ประเภท Content | เงื่อนไขเพิ่มเติม | Required Human % |
|------------|---------------|------------------|------------------|
| 🟢 GREEN | Educational original | Script เขียนใหม่ 100% | ≥40% |
| 🟢 GREEN | Dhamma reflection/meditation | Original insight required | ≥50% |
| 🟢 GREEN | Storytelling original | Plot + dialogue ใหม่ทั้งหมด | ≥40% |
| 🟡 YELLOW | News recap | ต้อง rewrite ≥70% + unique analysis | ≥60% |
| 🟡 YELLOW | Facts/Top10 | ต้อง unique angle + original research | ≥50% |
| 🟡 YELLOW | Commentary on trends | ต้องมี personal opinion ≥30% | ≥50% |
| 🔴 RED | Reused shorts | ❌ ห้ามเด็ดขาด | N/A |
| 🔴 RED | AI voice over others' videos | ❌ ห้ามเด็ดขาด | N/A |
| 🔴 RED | Template mass content | ❌ ห้ามเด็ดขาด | N/A |
| 🔴 RED | Compilation without commentary | ❌ ห้ามเด็ดขาด | N/A |

### การดำเนินการตามระดับความเสี่ยง

- 🟢 **GREEN**: Publish ได้หลัง standard review
- 🟡 **YELLOW**: ต้อง additional review + documentation เพิ่ม
- 🔴 **RED**: ห้าม publish ไม่มี exception

---

## F. Script Structure Standard — มาตรฐานโครงสร้างสคริปต์ (5-Part)

| Part | ชื่อ | ช่วงเวลา | Requirement | AI Allowed % |
|------|------|----------|-------------|--------------|
| 1 | Hook | 0:00-0:30 | Unique angle, human-written | ≤20% |
| 2 | Context | 0:30-2:00 | Human framing + background | ≤40% |
| 3 | Core | 2:00-8:00 | Main content, AI-assist OK | ≤70% |
| 4 | Reflection | 8:00-9:00 | Human interpretation/insight | ≤10% |
| 5 | Closing | 9:00-10:00 | Human CTA + disclaimer | 0% (human only) |

> **Total Script AI Limit: ≤60%**

---

## G. Voice & Visual Guidelines (แนวทางเสียงและภาพ)

### Voice (เสียง)

| Attribute | Requirement |
|-----------|-------------|
| AI Voice | ✅ Allowed แต่ต้อง: |
| | • ไม่ monotone (ต้องมี pitch variation) |
| | • Original script เท่านั้น |
| | • ระบุในคำอธิบายว่า AI-assisted |
| Human Voice | ✅ Preferred สำหรับ Hook/Closing |
| Mix | ✅ Best practice: Human intro/outro + AI core |

### Visual (ภาพ)

| Type | Requirement | หลักฐานที่ต้องเก็บ |
|------|-------------|-------------------|
| AI-Generated | ✅ Allowed | Prompt + generation record |
| Stock Media | ✅ Allowed + license required | License file/receipt |
| Self-Created | ✅ Preferred | Creation timestamp |
| Others' Footage | ❌ FORBIDDEN ยกเว้นมี written permission | License agreement |

### License Retention

> **MUST เก็บหลักฐาน license ไว้ ≥3 ปี ใน assets/ หรือ external archive**

---

## H. Metadata Integrity (ความถูกต้องของ Metadata)

| Element | Requirement |
|---------|-------------|
| Title | MUST reflect actual content (accuracy ≥90%) |
| Description | MUST include: topic summary, disclaimer if AI-assisted |
| Tags | MUST be relevant (≥80% match content) |
| Thumbnail | MUST represent content (no clickbait) |
| Disclaimer | SHOULD include: "เนื้อหาต้นฉบับ สร้างด้วยความช่วยเหลือจาก AI" |

---

## I. Upload Pattern — Anti-Spam (รูปแบบการอัปโหลด)

### Default Limits (SHOULD NOT เกิน)

| Metric | Default Limit | เหตุผล |
|--------|---------------|--------|
| Max videos/day | 2 | ป้องกัน spam flag |
| Min gap between uploads | 4 ชั่วโมง | ป้องกัน bulk upload detection |
| Max videos/week | 7 | Quality over quantity |
| Min video length (long-form) | 8 นาที | YouTube recommendation algorithm |
| Shorts | ต้อง original script + unique visual | ไม่ใช่ clip จาก long-form |
| Template reuse | ≤3 ครั้ง/เดือน ต่อ template | ป้องกัน repetitive content flag |

### Override Policy

> **MAY exceed default limits** เมื่อมี:
>
> 1. Human approval record (ระบุ Approval ID ใน checklist)
> 2. Justification บันทึกไว้ใน decision log
> 3. Primary หรือ Backup owner อนุมัติเป็นลายลักษณ์อักษร

---

## J. Pre-Publish Checklist (รายการตรวจสอบก่อน Publish)

> **คัดลอกและใช้ checklist นี้ก่อน publish ทุกครั้ง**

```markdown
## Pre-Publish Checklist — [Video Title] — [Date]

### A. Ownership & Rights
- [ ] Script เขียนใหม่ 100% สำหรับช่องนี้
- [ ] ไม่มี third-party content ที่ไม่มีสิทธิ์
- [ ] Stock assets มี license (แนบหลักฐาน: _______)
- [ ] AI-generated assets มี prompt record

### B. Human Value
- [ ] Human contribution ≥40% ของ script
- [ ] Human touchpoints ≥2 จุด (ระบุ: _______)
- [ ] Hook และ Closing เขียนโดยมนุษย์
- [ ] มี unique insight/interpretation

### C. Anti-Reuse Check
- [ ] ไม่มี verbatim copy >3 ประโยค จาก source ใดๆ
- [ ] ไม่ใช้ footage ของ creator อื่น
- [ ] ไม่ใช้ template ซ้ำ >3 ครั้ง/เดือน

### D. Metadata Integrity
- [ ] Title ตรงกับเนื้อหา
- [ ] Description ครบถ้วน
- [ ] Thumbnail ไม่ clickbait
- [ ] Tags relevant ≥80%

### E. Upload Pattern
- [ ] ห่างจาก upload ก่อนหน้า ≥4 ชั่วโมง
- [ ] ไม่เกิน 2 videos/วัน
- [ ] Video length ≥8 นาที (ถ้า long-form)

### F. Final Approval
- [ ] Reviewed by: _______________ (ชื่อ)
- [ ] Approved at: _______________ (timestamp)
- [ ] Quality Gate: PASS / FAIL

---
Signature: _______________
Date: _______________
```

---

## K. Enforcement & Violation Handling (การบังคับใช้และการจัดการการละเมิด)

### Violation Classification (การแบ่งระดับการละเมิด)

| Level | Description | Examples | Action |
|-------|-------------|----------|--------|
| **CRITICAL** | ละเมิด YouTube TOS หรือ Red category | Reused content, Deceptive metadata | Immediate block, ลบ content ภายใน 24 ชม. |
| **MAJOR** | ละเมิด Hard rules | Missing human review, Template overuse | Hold publish, Review ภายใน 48 ชม. |
| **MINOR** | ไม่ครบ checklist | Missing documentation, Incomplete records | Fix before next publish |

### Escalation Path (ขั้นตอนการ escalate)

| Step | Action | Timeline |
|------|--------|----------|
| 1 | พบ violation → Flag ใน quality_gate | ทันที |
| 2 | Primary owner review | ≤24 ชม. |
| 3 | ถ้า Primary ไม่ response → Backup owner review | >24 ชม. |
| 4 | ถ้าทั้ง 2 ไม่ response → Auto-hold ทุก pending publish | >48 ชม. |

### Exception Request Process (การขอ exception)

| Step | Action |
|------|--------|
| 1 | สร้าง Issue ใน repo พร้อม justification |
| 2 | ต้องมี approval จากทั้ง Primary + Backup owner |
| 3 | Document exception ใน exception_log.md |
| 4 | Exception มีอายุ max 30 วัน แล้วต้อง renew |

---

## L. Audit Trail & Evidence Mapping (การบันทึก Audit และ Mapping หลักฐาน)

### Policy Requirement → Evidence Source Mapping

| Policy Requirement | Evidence Source | ดูจาก |
|--------------------|-----------------|-------|
| Human approval record | quality_gate_summary.json | decision/status field ใน artifact |
| Content risk assessment | decision_support_summary.json | decision/recommendation field ใน artifact |
| Upload pattern compliance | kpi_summary.json | upload frequency metrics ใน artifact |
| Notification/alert record | notify_summary.json | notification records ใน artifact |
| Script ownership | Git commit history | Author + timestamp |
| License records | assets/ หรือ external archive | License files |

> **NOTE:**
>
> - ตารางนี้เป็น documentation เท่านั้น ไม่ได้เปลี่ยนแปลง schema หรือ code ใดๆ
> - Field names อาจแตกต่างตาม schema version ของแต่ละ artifact — ให้ดู contract docs ประกอบ

### Retention Policy (นโยบายการเก็บรักษา)

| ประเภทข้อมูล | ระยะเวลาเก็บ |
|-------------|-------------|
| Audit records | ≥3 ปี |
| License proof | ≥3 ปี หลัง content ถูกลบ |
| Exception logs | ≥2 ปี |

---

## M. Demonetization Response (แผนรับมือการถูก Demonetize)

| Situation | Immediate Action | Timeline |
|-----------|------------------|----------|
| Content ID claim | Review + dispute ถ้ามี rights | ภายใน 48 ชม. |
| Yellow $ (limited ads) | Review content, fix if needed | ภายใน 24 ชม. |
| Video removed | Assess violation, document lesson | ภายใน 24 ชม. |
| Channel demonetized | Full audit, remediation plan | ภายใน 7 วัน |

---

## N. Policy Maintenance (การบำรุงรักษานโยบาย)

### Review Schedule

| Activity | Frequency | Responsible |
|----------|-----------|-------------|
| Regular review | ทุก 90 วัน | Document Owner |
| YouTube policy update check | ทุก 30 วัน | Document Owner |
| Policy update | ผ่าน PR + ≥1 reviewer approval | Anyone → Owner approve |
| Version bump | Major: breaking change, Minor: clarification | Owner |
| Contributor acknowledgment | ก่อน first contribution | All contributors |

### Versioning Scheme

- **Major version** (x.0.0): Breaking changes ที่กระทบ workflow
- **Minor version** (0.x.0): เพิ่มเติมหรือแก้ไข clarification
- **Patch version** (0.0.x): แก้ไข typo หรือ formatting

---

## O. Changelog

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2026-01-08 | Initial release | natbkgift |

---

## สรุป

นโยบายนี้เป็น **"policy anchor"** สำหรับการผลิต YouTube content ที่:

1. ✅ Monetization-safe ตาม YouTube Partner Program
2. ✅ เป็นไปตาม ISO 27001 / SOC2 audit requirements
3. ✅ บังคับ Human-in-the-Loop ทุกขั้นตอน
4. ✅ มี deterministic checklists และ enforcement ที่ชัดเจน
5. ✅ มี audit trail mapping กับ existing artifacts

> **การอัปเดตนโยบายต้องผ่าน PR และได้รับ approval จาก Document Owner**
