# เอกสาร Baseline

## วัตถุประสงค์

เอกสารนี้กำหนดพฤติกรรม **baseline** ของระบบ Dhamma Channel Automation ในโหมด **Client Product** (ปรับแต่งสำหรับช่องเดียว) โดยใช้เป็นจุดอ้างอิงเพื่อตรวจจับการเปลี่ยนแปลงที่ไม่ตั้งใจ (drift) เมื่อเวลาผ่านไป

## ทำไม Baseline สำคัญ

ในระบบโปรดักชัน การเปลี่ยนโค้ด อัปเดต dependency หรือการเปลี่ยนแปลงของ external API สามารถทำให้พฤติกรรมเปลี่ยนไปแบบไม่ตั้งใจได้ Baseline ช่วยให้:

1. **ตรวจจับ Drift:** ระบุความเปลี่ยนแปลงที่ไม่ตั้งใจในโครงสร้าง รูปแบบ โทน หรือคุณภาพของผลลัพธ์
2. **คงความสม่ำเสมอ:** รักษาพฤติกรรมให้คาดเดาได้สำหรับโปรดักต์ช่องเดียว
3. **ช่วยในการทดสอบ:** มีตัวอย่างอ้างอิงสำหรับ regression testing
4. **บันทึกเจตนา:** ระบุว่า “พฤติกรรมที่ถูกต้อง” ณ เวลาหนึ่งควรเป็นอย่างไร

## สิ่งที่ต้องคงที่ (Client Product Mode)

ด้านล่างคือสิ่งที่ต้องคงที่ เว้นแต่มีการเปลี่ยนแปลงโดยตั้งใจและมีการบันทึกไว้:

### 1. โครงสร้างผลลัพธ์
- **JSON Schema:** ฟิลด์และชนิดข้อมูลของ JSON ต้องคงที่
- **การตั้งชื่อไฟล์:** ชื่อไฟล์ต้องเป็นไปตามกติกาเดิม (เช่น `metadata.json`, `topics_ranked.json`, `outline.md`)
- **โครงสร้างไดเรกทอรี:** Pipeline ต้องสร้าง `output/{run_id}/` พร้อมไฟล์ที่คาดหวัง
- **Voiceover Artifacts:** ไฟล์เสียงและเมทาดาทาเก็บใน `data/voiceovers/<run_id>/` และชื่อไฟล์แบบ `<slug>_<sha256[:12]>.wav` และ `<slug>_<sha256[:12]>.json`
- **Video Render Artifacts:** ผลลัพธ์วิดีโอเก็บใน `output/<run_id>/artifacts/` โดยมีไฟล์ `video_render_summary.json` และไฟล์ MP4 แบบ `<slug>_<sha256[:12]>.mp4`
- **Quality Gate Artifacts:** ไฟล์สรุปคุณภาพเก็บใน `output/<run_id>/artifacts/quality_gate_summary.json`
- **Post Content Artifacts:** ไฟล์สรุปเนื้อหาโพสต์เก็บใน `output/<run_id>/artifacts/post_content_summary.json`
- **Dispatch Audit Artifacts:** ไฟล์ audit ของขั้น dispatch.v0 เก็บที่ `output/<run_id>/artifacts/dispatch_audit.json`
- **Publish Request Artifacts:** ไฟล์คำขอเผยแพร่แบบ deterministic เก็บที่ `output/<run_id>/artifacts/publish_request.json`
- **Preview Summary Artifacts:** ไฟล์สรุป preview เก็บที่ `output/<run_id>/artifacts/preview_summary.json`

### 2. รูปแบบเนื้อหา
- **Metadata Format:** เมทาดาทา YouTube ต้องมีโครงสร้างเดิม (title, description, tags, SEO keywords)
- **Topic Ranking Format:** หัวข้อต้องมีอันดับ ชื่อ คะแนน (impact/feasibility/alignment) เหตุผล ความยาก ความเสี่ยง และกลุ่มเป้าหมาย
- **Outline Structure:** โครงสร้างสคริปต์ต้องเป็น Hook → Intro → Main Content → CTA พร้อมเวลาประมาณการ

### 3. โทนและสไตล์ของเนื้อหา
- **โทน:** เข้าถึงง่าย เป็นกันเอง อบอุ่น ไม่เทศนา
- **ภาษา:** ไทยเป็นหลัก เสริมอังกฤษเท่าที่จำเป็น (เช่น “mindfulness”, “meditation”)
- **เป้าหมายความยาว:** Title 60-70 ตัวอักษร, Description 500-1000 ตัวอักษร, วิดีโอ 5-10 นาที
- **โฟกัสผู้ชม:** ผู้ชมทั่วไปที่สนใจพุทธเชิงปฏิบัติและการเจริญสติ

### 4. ตรรกะทางธุรกิจ
- **การให้คะแนนหัวข้อ:** สูตร impact × feasibility × alignment
- **SEO Optimization:** สร้างคำค้นหา hashtag และแนวทาง thumbnail
- **Compliance:** เนื้อหาสอดคล้องหลักธรรมและนโยบาย YouTube
- **Single-Channel Focus:** ทุกผลลัพธ์ปรับให้เหมาะกับช่องเดียว

### 5. เมทาดาทาเสียงบรรยาย (TTS)
- **ตำแหน่งไฟล์:** `data/voiceovers/<run_id>/<slug>_<sha256[:12]>.json`
- **การตั้งชื่อแบบ deterministic:** ใช้แฮชจากข้อความที่ normalize แล้วเท่านั้น (CRLF/LF → `\n`, ตัดช่องว่างท้ายบรรทัดแบบ deterministic)
- **พาธในเมทาดาทา:** ต้องเป็นพาธแบบ relative เท่านั้น
- **ตัวอย่างอ้างอิง:** ดูที่ `samples/reference/tts/voiceover_v1_example.json`

### 6. สัญญาเมทาดาทาเสียงบรรยาย (คงที่)

**สคีมาเมทาดาทานี้ถือว่า STABLE** และเป็นสัญญาหลักของระบบ TTS

**ฟิลด์ที่ต้องมี (required):**
- `schema_version` (string)
- `run_id` (string)
- `slug` (string)
- `input_sha256` (string, 64 hex)
- `output_wav_path` (string, relative path)
- `duration_seconds` (number)
- `engine_name` (string)

**ฟิลด์เสริม (optional):**
- `voice` (string)
- `style` (string)
- `created_utc` (string)

**นโยบาย schema_version:**
- การเปลี่ยนแปลงที่ **breaking** ต้อง bump `schema_version` และใส่ migration note
- การเพิ่มฟิลด์แบบ **additive** ทำได้ ถ้าคง backward compatibility
- การเปลี่ยนชื่อ/ลบฟิลด์แบบเงียบๆ **ห้ามทำ**

### 7. สัญญา Video Render Summary (คงที่)

**สคีมาไฟล์ `output/<run_id>/artifacts/video_render_summary.json` ถือว่า STABLE** สำหรับขั้น `uses: video.render`

**ฟิลด์ที่ต้องมี (required):**
- `schema_version` (string, ปัจจุบัน `v1`)
- `run_id` (string)
- `slug` (string)
- `text_sha256_12` (string, 12 chars)
- `input_voiceover_summary` (string, relative path)
- `input_wav_path` (string, relative path)
- `output_mp4_path` (string, relative path)
- `engine` (string)
- `ffmpeg_cmd` (list[string], ต้องไม่มี absolute paths)

**หมายเหตุ schema_version:**
- `data/voiceovers/<run_id>/<slug>_<sha12>.json` (TTS metadata) ใช้ `schema_version` แบบตัวเลข (เช่น `1`) ตามสัญญา TTS
- `output/<run_id>/artifacts/*_summary.json` (pipeline summaries) ใช้ `schema_version` แบบมี prefix (เช่น `v1`) เพื่อแยกชัดเจนว่าเป็น summary artifact

### 8. สัญญา Quality Gate Summary (คงที่)

**สคีมาไฟล์ `output/<run_id>/artifacts/quality_gate_summary.json` ถือว่า STABLE** สำหรับขั้น `uses: quality.gate`

**ฟิลด์ที่ต้องมี (required):**
- `schema_version` (string, ปัจจุบัน `v1`)
- `run_id` (string)
- `input_video_render_summary` (string, relative path)
- `output_mp4_path` (string, relative path)
- `decision` (`pass` หรือ `fail`)
- `reasons` (list[object], ลำดับต้องคงที่)
- `checked_at` (string, ISO8601)
- `engine` (string, ต้องเป็น `quality.gate`)
- `checks` (object, ค่า boolean/metrics ขั้นต่ำ)

**รูปแบบ reasons (คงที่):**
- `code` (string, one of: `mp4_missing`, `mp4_empty`, `ffprobe_failed`, `duration_zero_or_missing`, `audio_stream_missing`)
- `message` (string)
- `severity` (`error` | `warn`)
- `engine` (string, `quality.gate`)
- `checked_at` (string, ISO8601 เดียวกับด้านบน)

**กติกาตัดสินใจ:**
- ถ้ามี reason ที่ `severity` = `error` อย่างน้อยหนึ่งรายการ ให้ `decision` = `fail`
- ถ้าไม่พบ `error` ให้ `decision` = `pass`

**พาธ:** ทุกพาธต้องเป็น relative เท่านั้น (ห้าม absolute)

### 9. สัญญา Schedule Summary (คงที่)

**สคีมาไฟล์ `output/scheduler/artifacts/schedule_summary_<YYYYMMDD>.json` ถือว่า STABLE** สำหรับ scheduler v1

**ฟิลด์ที่ต้องมี (required):**
- `schema_version` (string, ปัจจุบัน `v1`)
- `engine` (string, ต้องเป็น `scheduler`)
- `checked_at` (string, ISO8601 UTC)
- `plan_path` (string, relative path)
- `now` (string, ISO8601 UTC)
- `window_minutes` (int)
- `enqueued_job_ids` (list[string], ลำดับต้องคงที่)
- `skipped_entries` (list[object], ลำดับต้องคงที่)
- `dry_run` (bool)

**หมายเหตุสำคัญ (ops/determinism):**
- `checked_at` คือเวลาที่รันจริง (audit time) จึงไม่ deterministic
- `plan_path` ต้องเป็น relative path เท่านั้น และ **ห้ามเป็น absolute**
  - ถ้า input ของ `--plan` ไม่ถูกต้อง (เช่น absolute path) ให้ `plan_path` เป็น `""` และ `skipped_entries[0].code = "plan_parse_error"`

**รูปแบบ skipped_entries (คงที่):**
- `publish_at` (string)
- `pipeline_path` (string)
- `run_id` (string)
- `code` (string, one of: `scheduler_disabled`, `entry_not_due`, `already_enqueued`, `plan_parse_error`, `job_invalid`)
- `message` (string)

### 10. สัญญา Worker Summary (คงที่)

**สคีมาไฟล์ `output/worker/artifacts/worker_summary_<job_id>.json` ถือว่า STABLE** สำหรับ worker v1

**ฟิลด์ที่ต้องมี (required):**
- `schema_version` (string, ปัจจุบัน `v1`)
- `engine` (string, ต้องเป็น `worker`)
- `checked_at` (string, ISO8601 UTC)
- `job_id` (string)
- `run_id` (string)
- `pipeline_path` (string)
- `decision` (`done` | `failed` | `skipped`)
- `error` (object|null)
- `dry_run` (bool)

**หมายเหตุสำคัญ:**
- ปกติ `pipeline_path` ต้องเป็น relative path (string)
- กรณีไม่มีงานในคิว (`job_id = "none"`) หรือ payload งานไม่สมบูรณ์ (`job_invalid`) อาจได้ `run_id = ""` และ `pipeline_path = ""`
- กรณีไม่มีงานในคิว จะสร้าง artifact เป็น `output/worker/artifacts/worker_summary_none.json` (ถือว่าเป็นเคสพิเศษของ `worker_summary_<job_id>.json`)

**รูปแบบ error (คงที่เมื่อไม่เป็น null):**
- `code` (string, one of: `worker_disabled`, `queue_empty`, `job_invalid`, `orchestrator_failed`)
- `message` (string)

### 11. สัญญา Post Content Summary (คงที่)

**สคีมาไฟล์ `output/<run_id>/artifacts/post_content_summary.json` ถือว่า STABLE** สำหรับ post_templates v1

**ฟิลด์ที่ต้องมี (required):**
- `schema_version` (string, ปัจจุบัน `v1`)
- `engine` (string, ต้องเป็น `post_templates`)
- `run_id` (string)
- `checked_at` (string, ISO8601 UTC)
- `inputs` (object)
  - `lang` (string)
  - `platform` (string)
  - `template_short` (string, relative path)
  - `template_long` (string, relative path)
  - `sources` (list[string], relative paths หรือ `env:PIPELINE_PARAMS_JSON`)
- `outputs` (object)
  - `short` (string, เนื้อหาโพสต์แบบสั้น)
  - `long` (string, เนื้อหาโพสต์แบบยาว)

**หมายเหตุสำคัญ:**
- ทุกพาธใน `inputs.template_*` และ `inputs.sources` ต้องเป็น relative เท่านั้น (ห้าม absolute)
- `checked_at` ยอมให้ไม่ deterministic (audit time)
- แฮชแท็กใน outputs ต้อง normalize แบบ deterministic (เช่น list ต้อง sorted)
- `inputs.sources` หมายถึง “แหล่งที่ถูกใช้เติมค่า (used)” เท่านั้น ไม่ใช่แหล่งที่ถูกอ่านเฉย ๆ
- `inputs.sources` อาจมีค่าพิเศษ `env:PIPELINE_PARAMS_JSON` ที่แทนการอ่านค่าจาก environment variable
- ตัวอย่างอ้างอิง: `samples/reference/post/post_content_summary_v1_example.json`

### 12. สัญญา Dispatch Audit Summary (คงที่)

**สคีมาไฟล์ `output/<run_id>/artifacts/dispatch_audit.json` (dispatch.v0) ถือว่า STABLE**

**ฟิลด์ที่ต้องมี (required):**
- `schema_version` (string, ปัจจุบัน `v1`)
- `engine` (string, ต้องเป็น `dispatch_v0`)
- `run_id` (string)
- `checked_at` (string, ISO8601 UTC) — ไม่ deterministic
- `inputs` (object)
  - `post_content_summary` (string, relative path)
  - `dispatch_enabled` (bool)
  - `dispatch_mode` (`dry_run` | `print_only`)
  - `target` (string)
  - `platform` (string)
- `result` (object)
  - `status` (`skipped` | `dry_run` | `printed` | `failed`)
  - `message` (string)
  - `actions` (list[object], อย่างน้อยมีรายการ print/long/short และ noop publish พร้อมเหตุผล)
- `errors` (list[object], ยอมให้ว่าง)

**กติกาสำคัญ:**
- ทุก path ต้องเป็น relative เท่านั้น (ห้าม absolute หรือมี `..`)
- `checked_at` คือเวลารันจริง (audit time) จึงไม่ deterministic
- การเปลี่ยนแปลงแบบ breaking ต้อง bump `schema_version` และอัปเดตไฟล์อ้างอิงใน `samples/reference/dispatch/`

### 13. สัญญา Publish Request (คงที่)

**สคีมาไฟล์ `output/<run_id>/artifacts/publish_request.json` (publish_request.v0) ถือว่า STABLE**

**ฟิลด์ที่ต้องมี (required):**
- `schema_version` (string, ปัจจุบัน `v1`)
- `engine` (string, ต้องเป็น `publish_request_v0`)
- `run_id` (string)
- `checked_at` (string, ISO8601 UTC) — ไม่ deterministic
- `inputs` (object)
  - `post_content_summary` (string, relative path)
  - `dispatch_audit` (string, relative path)
  - `platform` (string)
  - `target` (string)
- `request` (object)
  - `content_short` (string)
  - `content_long` (string)
  - `attachments` (list, ต้องเป็น `[]` ใน v1)
- `controls` (object)
  - `dry_run` (bool, ต้องเป็น `true`)
  - `allow_publish` (bool, ต้องเป็น `false`)
  - `idempotency_key` (string, sha256 hex 64)
- `policy` (object)
  - `status` (`pending`)
  - `reasons` (list[object])
- `errors` (list[object], ยอมให้ว่าง)

**กติกาสำคัญ:**
- ทุก path ต้องเป็น relative เท่านั้น (ห้าม absolute หรือมี `..`)
- `checked_at` คือเวลารันจริง (audit time) จึงไม่ deterministic
- `idempotency_key` ต้องคำนวณจาก `run_id|target|platform|sha256(content_long)` แบบ deterministic
- การเปลี่ยนแปลงแบบ breaking ต้อง bump `schema_version` และอัปเดตไฟล์อ้างอิงใน `samples/reference/publish/`

### 14. สัญญา Preview Summary (คงที่)

**สคีมาไฟล์ `output/<run_id>/artifacts/preview_summary.json` (preview_summary_v0) ถือว่า STABLE**

**ฟิลด์ที่ต้องมี (required):**
- `schema_version` (string, ปัจจุบัน `v1`)
- `engine` (string, ต้องเป็น `preview_summary_v0`)
- `run_id` (string)
- `checked_at` (string, ISO8601 UTC) — ไม่ deterministic
- `inputs` (object)
  - `publish_request` (string, relative path)
  - `post_content_summary` (string, relative path)
  - `dispatch_audit` (string, relative path)
  - `platform` (string)
  - `target` (string)
- `summary` (object)
  - `target` (string)
  - `platform` (string)
  - `mode` (`dry_run`)
  - `actions` (list[object], ต้องมี print/short, print/long, noop/publish ตามลำดับ)
- `policy` (object)
  - `status` (`preview_only`)
  - `reasons` (list[string], อาจว่าง)
- `errors` (list[object], ยอมให้ว่าง)

**กติกาสำคัญ (determinism):**
- `checked_at` คือเวลารันจริง (audit time) จึงไม่ deterministic
- ฟิลด์อื่นต้อง deterministic จาก `publish_request.json`
- ทุกพาธต้องเป็น relative เท่านั้น (ห้าม absolute หรือมี `..`)
- `summary.actions[*].preview` ต้องไม่เกิน 500 ตัวอักษร

**นโยบายการเปลี่ยนแปลง (breaking-change policy):**
- การเปลี่ยนแปลงแบบ breaking ต้อง bump `schema_version` และอัปเดตไฟล์อ้างอิงใน `samples/reference/preview/`
- การเพิ่มฟิลด์แบบ additive ทำได้ ถ้ายัง backward compatible

**ตัวอย่างอ้างอิง:** `samples/reference/preview/preview_summary_v1_example.json`

## Assets Baseline v1

นโยบาย assets เป็น baseline ที่ต้องคงที่สำหรับ repo สาธารณะ เพื่อความปลอดภัย
ด้านลิขสิทธิ์ ขนาดไฟล์ และความ deterministic ของพาธ

Policy source-of-truth: `docs/ASSETS_POLICY.md`

- ไบนารีฟอนต์ (font binaries) ถูกตั้งใจไม่ให้รวมอยู่ใน baseline
- การมีไฟล์ฟอนต์ที่ใช้นามสกุลต้องห้ามถือเป็นการละเมิดนโยบาย และต้องทำให้เทสต์ล้ม
- โฟลเดอร์ `assets/fonts/` ถูกล็อกให้มีได้เฉพาะไฟล์ `README.md` เท่านั้น
- โครงสร้าง assets/ ต้องตรงตาม skeleton ที่กำหนดใน policy และไฟล์ภายในต้องมีขนาดเล็ก

## รายการอ้างอิงที่รวมไว้ (samples/reference)

โฟลเดอร์ `samples/reference/` มี baseline artifacts สำหรับตรวจจับ drift:

### 12. `metadata.json` (SEO Metadata)
- **แทนอะไร:** เมทาดาทา YouTube ขั้นสุดท้าย
- **จุดที่ต้องคงที่:**
  - รูปแบบ title (60-70 ตัวอักษร มีประโยชน์ชัดเจน)
  - โครงสร้าง description (emoji hook, overview, สารบัญ, benefits, hashtags)
  - รายการ tags 8-15 รายการ ไทย/อังกฤษผสม
  - แนวคิด thumbnail 3 แบบพร้อมรายละเอียด
  - SEO keywords 4-7 คำที่ค้นหาได้จริง

### 13. `topics_ranked.json` (Topic Prioritization)
- **แทนอะไร:** รายการหัวข้อที่จัดอันดับจาก TrendScout/TopicPrioritizer
- **จุดที่ต้องคงที่:**
  - โครงสร้างคะแนน impact/feasibility/alignment/total
  - อันดับตาม total score
  - เหตุผลและความเสี่ยงที่ชัดเจน

### 14. `outline_sample.md` (Script Outline)
- **แทนอะไร:** โครงสร้าง outline สำหรับเขียนสคริปต์
- **จุดที่ต้องคงที่:**
  - Flow: Hook → Intro → Main → CTA
  - เวลาโดยรวมเหมาะกับวิดีโอ 5-7 นาที
  - โทนอบอุ่นและเป็นกันเอง

### 15. `samples/reference/tts/voiceover_v1_example.json`
- **แทนอะไร:** สัญญาเมทาดาทาเสียงบรรยายเวอร์ชัน 1
- **จุดที่ต้องคงที่:** ฟิลด์และชนิดข้อมูลตามสัญญาในหัวข้อ เมทาดาทาเสียงบรรยาย (คงที่)

### 16. `samples/reference/video/video_render_summary_v1_example.json`
- **แทนอะไร:** สัญญา video render summary เวอร์ชัน 1 (ไฟล์อ้างอิงสำหรับ `video_render_summary.json`)
- **จุดที่ต้องคงที่:** ฟิลด์สำคัญ + พาธแบบ relative เท่านั้น + `ffmpeg_cmd` ต้องไม่หลุด absolute path

### 17. `samples/reference/quality/quality_gate_summary_v1_example.json`
- **แทนอะไร:** สัญญา quality gate summary เวอร์ชัน 1 (ไฟล์อ้างอิงสำหรับ `quality_gate_summary.json`)
- **จุดที่ต้องคงที่:** ฟิลด์สำคัญ + พาธแบบ relative เท่านั้น + reasons ต้องมี `engine` และ `checked_at`

### 18. `samples/reference/youtube/youtube_upload_summary_v1_example.json`
- **แทนอะไร:** สัญญา YouTube upload summary เวอร์ชัน 1 (ไฟล์อ้างอิงสำหรับ `youtube_upload_summary.json`)
- **จุดที่ต้องคงที่:** ฟิลด์สำคัญ + พาธแบบ relative เท่านั้น + โครงสร้าง `error` และ `metadata` ต้องไม่ drift

### 19. `samples/reference/scheduler/schedule_summary_v1_example.json`
- **แทนอะไร:** สัญญา schedule summary เวอร์ชัน 1 (ไฟล์อ้างอิงสำหรับ `schedule_summary.json`)
- **จุดที่ต้องคงที่:** ฟิลด์สำคัญ + พาธแบบ relative เท่านั้น + โค้ดการข้ามต้องคงที่

### 20. `samples/reference/scheduler/worker_summary_v1_example.json`
- **แทนอะไร:** สัญญา worker summary เวอร์ชัน 1 (ไฟล์อ้างอิงสำหรับ `worker_summary.json`)
- **จุดที่ต้องคงที่:** ฟิลด์สำคัญ + พาธแบบ relative เท่านั้น + โครงสร้าง `error` ต้องไม่ drift

### 21. `samples/reference/post/post_content_summary_v1_example.json`
- **แทนอะไร:** สัญญา post content summary เวอร์ชัน 1 (ไฟล์อ้างอิงสำหรับ `post_content_summary.json`)
- **จุดที่ต้องคงที่:** ฟิลด์สำคัญ + พาธแบบ relative เท่านั้น + แฮชแท็กต้อง normalize แบบ deterministic + โครงสร้าง inputs/outputs ต้องไม่ drift + `inputs.sources` เป็นรายการ used sources เท่านั้น

### 22. `samples/reference/dispatch/dispatch_audit_v1_example.json`
- **แทนอะไร:** สัญญา dispatch audit เวอร์ชัน 1 (ไฟล์อ้างอิงสำหรับ `dispatch_audit.json`)
- **จุดที่ต้องคงที่:** ฟิลด์ inputs/result/errors ตามสัญญา + พาธต้องเป็น relative ทั้งหมด + status/target/mode ต้อง deterministic จากอินพุต + แม้ dispatch disabled ต้องมี action=print เพื่อ audit preview และ noop publish

### 23. `samples/reference/publish/publish_request_v1_example.json`
- **แทนอะไร:** สัญญา publish request เวอร์ชัน 1 (ไฟล์อ้างอิงสำหรับ `publish_request.json`)
- **จุดที่ต้องคงที่:** ฟิลด์ inputs/request/controls/policy/errors ตามสัญญา + ทุกพาธเป็น relative + `idempotency_key` deterministic

### 24. `samples/reference/preview/preview_summary_v1_example.json`
- **แทนอะไร:** สัญญา preview summary เวอร์ชัน 1 (ไฟล์อ้างอิงสำหรับ `preview_summary.json`)
- **จุดที่ต้องคงที่:** ฟิลด์ inputs/summary/policy/errors ตามสัญญา + ทุกพาธเป็น relative + `summary.actions` ต้องคงลำดับ

## ขั้นตอนเปรียบเทียบ (Comparison Procedure)

### ขั้นที่ 1: รัน Pipeline

```bash
# Using orchestrator (full pipeline)
python orchestrator.py --pipeline pipeline.web.yml --run-id baseline_check_$(date +%Y%m%d)

# Or using CLI (specific agent)
python -m cli.main trend-scout --input data/mock_input.json --out output/test_topics.json
```

### ขั้นที่ 2: ตรวจสอบผลลัพธ์

```bash
cd output/baseline_check_YYYYMMDD/
ls -la
```

ไฟล์ที่คาดหวัง: `metadata.json`, `topics_ranked.json`, `outline.md`, `script.md` ฯลฯ

### ขั้นที่ 3: เปรียบเทียบกับ Baseline

**ทางเลือก A: diff แบบ manual**
```bash
# JSON files
diff -u samples/reference/metadata.json output/baseline_check_YYYYMMDD/metadata.json

# Markdown files
diff -u samples/reference/outline_sample.md output/baseline_check_YYYYMMDD/outline.md
```

**ทางเลือก B: diff แบบโครงสร้าง JSON**
```bash
jq -S . samples/reference/topics_ranked.json > /tmp/baseline.json
jq -S . output/baseline_check_YYYYMMDD/topics_ranked.json > /tmp/current.json
diff -u /tmp/baseline.json /tmp/current.json
```

**ทางเลือก C: ตรวจสอบด้วย Python**
```python
import json

with open('samples/reference/metadata.json') as f:
    baseline = json.load(f)
with open('output/baseline_check_YYYYMMDD/metadata.json') as f:
    current = json.load(f)

assert set(baseline.keys()) == set(current.keys()), "Top-level keys changed"
assert isinstance(current['tags'], list), "Tags should be a list"
assert 60 <= len(current['title']) <= 80, "Title length out of range"
```

### ขั้นที่ 4: ประเมินความแตกต่าง

**ยอมรับได้:**
- ค่าที่เปลี่ยนตามเวลา เช่น `generated_at`, `prioritized_at`, `run_id`, timestamps
- เนื้อหาที่เปลี่ยนตามเหตุการณ์ เช่น หัวข้อเทรนด์จริง
- ลำดับรายการที่ต่างเล็กน้อย (ถ้าไม่มีกติกาจัดอันดับแน่ชัด)

**ต้องตรวจสอบ:**
- ฟิลด์หาย/เพิ่มแบบไม่ตั้งใจ
- ชนิดข้อมูลเปลี่ยน (string → number, list → dict)
- รูปแบบเปลี่ยน (title length, description structure)
- โทนเปลี่ยน (ทางการ → กันเอง หรือกลับกัน)
- กฎคำนวณเปลี่ยน (สูตรคะแนน, ranking)

**ต้องจัดการทันที:**
- ความเสี่ยงด้านความปลอดภัย (credentials/PII หลุด)
- Schema แตกจนระบบ downstream ใช้ไม่ได้
- ผิดหลักคำสอนหรือผิดนโยบายแพลตฟอร์ม

### ขั้นที่ 5: บันทึกและตัดสินใจ

ถ้าพบ drift:
1. **บันทึก:** อะไรเปลี่ยน เมื่อไร และสาเหตุที่เป็นไปได้
2. **จัดประเภท:** ตั้งใจเปลี่ยน vs เปลี่ยนโดยไม่ตั้งใจ
3. **ตัดสินใจ:**
   - **ตั้งใจ:** อัปเดต baseline references และบันทึกใน CHANGELOG
   - **ไม่ตั้งใจ:** แก้โค้ด ทดสอบใหม่ และยืนยัน baseline
   - **ยอมรับได้:** จดบันทึกและเฝ้าระวัง

## การอัปเดต Baseline

ควรอัปเดต baseline เมื่อ:
- มีฟีเจอร์ใหม่หรือเปลี่ยน logic แบบตั้งใจ
- ปรับปรุงโครงสร้างผลลัพธ์ให้ดีขึ้น
- รอบรีวิวรายไตรมาส

**ขั้นตอนอัปเดต:**
1. ยืนยันว่าการเปลี่ยนแปลงตั้งใจและผ่านการรีวิว
2. รัน pipeline เพื่อสร้างผลลัพธ์ใหม่
3. คัดลอกผลลัพธ์ไปไว้ที่ `samples/reference/` (ตัดให้เหลือส่วนจำเป็น)
4. อัปเดต `samples/reference/README.md` ให้สอดคล้อง
5. อัปเดตเอกสารนี้ถ้ามีการเปลี่ยนความเสถียรของ schema
6. Commit ด้วยข้อความที่ชัดเจน

## กลยุทธ์การทดสอบ

### การทดสอบด้วยมือ (ปัจจุบัน)
- รัน pipeline ก่อนปล่อยเวอร์ชันใหญ่
- เปรียบเทียบกับ `samples/reference/`
- ตรวจสอบด้วยสายตาในฟิลด์สำคัญ

### การทดสอบอัตโนมัติ (อนาคต)
- **Schema validation:** ทดสอบด้วย JSON Schema
- **Structure tests:** Pytest ตรวจฟิลด์และชนิดข้อมูล
- **Tone analysis:** ตรวจโทนด้วย NLP (อนาคต)
- **Regression suite:** Golden file tests

## ความสัมพันธ์กับ Global Kill Switch

Baseline และ Kill Switch มีหน้าที่ต่างกัน:

- **Baseline:** บอกว่า *อะไร* เปลี่ยน
- **Kill Switch:** บอกว่า *เมื่อไร* ให้หยุดรัน

เมื่อ Kill Switch ถูกปิด (`PIPELINE_ENABLED=false`) ระบบต้องหยุดก่อนสร้างผลลัพธ์ เพื่อป้องกัน side effects และ drift

## หมายเหตุสำหรับนักพัฒนา

- **อย่าแก้ baseline โดยไม่จำเป็น:** เพราะเป็นข้อตกลงร่วมของทีม
- **ทดสอบกับ baseline เสมอ:** เพื่อยืนยันว่าไม่มี drift โดยไม่ตั้งใจ
- **อัปเดตเอกสารควบคู่กับโค้ด:** เมื่อมีการเปลี่ยน format หรือ schema
- **เก็บตัวอย่างให้เล็ก:** ตัดเฉพาะโครงสร้างสำคัญและไม่ใช้ข้อมูลอ่อนไหว
- **ติดตามเวอร์ชัน baseline ใน git:** เพื่อ audit ได้
- **AGENTS.md:** Repo นี้ไม่มี AGENTS.md ให้ยึดตามข้อตกลงเดิมแทน

## ติดต่อ

หากมีคำถามเกี่ยวกับ baseline หรือ drift detection:
- ผู้ดูแล repository
- ดูรายละเอียดเพิ่มเติมใน `samples/reference/README.md`

---

## Governance & Code Quality Baseline

**ความเสถียรของ Baseline นี้ได้รับการคุ้มครองโดยนโยบายการปกครอง:**

### Code Review & Testing

- ✅ **PR Requirement:** ทุก PR ต้องผ่านการตรวจสอบโค้ดอย่างน้อย 1 คน
- ✅ **CI/CD Gate:** Ruff linting + pytest coverage ต้องผ่าน
- ✅ **Coverage Regression:** Test coverage ต้องเท่ากับหรือสูงกว่าเดิม
- ✅ **Documentation:** เอกสารต้องอัปเดตให้เป็นปัจจุบัน

### Breaking Changes

- ⚠️ **Breaking Change:** ต้องมี major version bump (semantic versioning)
- ⚠️ **CHANGELOG Update:** ต้องรายละเอียดผลกระทบ + migration guide
- ⚠️ **Schema Changes:** กำหนด `schema_version` ใหม่ + deprecation path

### Baseline Drift Detection

**ตรวจสอบ baseline drift ด้วย:**

```bash
# ทดสอบลักษณะ output format
pytest tests/test_baseline_contracts.py -v

# เปรียบเทียบกับ samples/reference/
python -m scripts/validate_baseline.py output/<run_id>/
```

### Governance Documents

- **SECURITY.md** - นโยบายการรายงานช่องโหว่
- **CODEOWNERS** - ผู้ดูแลโค้ดสำหรับ code review assignment
- **GOVERNANCE.md** - กฎการควบคุม PR, release, การเปลี่ยนแปลง
- **CONTRIBUTING.md** - แนวทางการมีส่วนร่วม
- **CODE_OF_CONDUCT.md** - สัญญาคุณธรรมชุมชน

ดูเพิ่มเติม: [docs/GOVERNANCE.md](GOVERNANCE.md)

---

**เวอร์ชันเอกสาร:** 1.1  
**อัปเดตล่าสุด:** 2025-01-06  
**ใช้กับ:** Dhamma Channel Automation v0.1.x (Client Product Mode)  
**สถานะ:** APPROVED & ENFORCED (governance audit PR #166)
