# Baseline Reference Samples

This directory contains **baseline reference artifacts** that represent known-good outputs from the Dhamma Channel Automation pipeline. These samples serve as a reference point for detecting behavior drift over time.

## Purpose

The reference samples help detect unintended changes in:
- Output structure and format
- Content tone and style
- Metadata completeness
- JSON schema adherence

## Reference Items

### 1. `metadata.json`
**What it represents:** SEO metadata output from the pipeline  
**Key attributes to monitor:**
- Title format and length (should be 60-70 chars, engaging)
- Description structure (emoji, sections, hashtags)
- Tag selection (mix of Thai/English, relevant terms)
- Thumbnail suggestions (creative, actionable)
- SEO keywords (audience-focused, searchable)

**Why chosen:** Metadata is critical for YouTube discoverability and represents the pipeline's understanding of content optimization. Any drift here directly impacts channel performance.

### 2. `topics_ranked.json`
**What it represents:** Prioritized topic list from TrendScout/TopicPrioritizer agents  
**Key attributes to monitor:**
- Scoring structure (impact, feasibility, alignment scores)
- Ranking logic (total score calculation)
- Topic selection reasoning (trend awareness, audience fit)
- Risk assessment format (difficulty, risk level, audience)

**Why chosen:** Topic ranking reflects the pipeline's decision-making capability. Drift here indicates changes in content strategy logic, which should be intentional, not accidental.

### 3. `outline_sample.md`
**What it represents:** Script outline structure from ScriptOutline agent  
**Key attributes to monitor:**
- Section organization (Hook, Introduction, Main Content, CTA)
- Timing estimates (realistic for 5-7 min video)
- Tone description (accessible, warm, friendly)
- Content flow and storytelling approach

**Why chosen:** The outline represents the pipeline's content structuring capability and tone consistency. Changes here affect the final script quality and audience engagement.

### 4. `video/video_render_summary_v1_example.json`
**What it represents:** Stable contract for the `video_render_summary.json` artifact produced by `uses: video.render`.
**Key attributes to monitor:**
- Required fields remain present (`run_id`, `slug`, `text_sha256_12`, paths)
- All paths are relative (no absolute paths)
- `ffmpeg_cmd` is recorded with relative paths only

**Why chosen:** This summary is consumed downstream and is part of the deterministic pipeline contract; drift here can break video publishing/rendering automation.

### 5. `quality/quality_gate_summary_v1_example.json`
**What it represents:** Stable contract for the `quality_gate_summary.json` artifact produced by `uses: quality.gate`.
**Key attributes to monitor:**
- Required fields remain present (decision, reasons, checks)
- All paths are relative (no absolute paths)
- Reasons include stable `code`, `engine`, and `checked_at`

**Why chosen:** This summary gates downstream steps; drift can change pass/fail decisions or hide critical failures.

## What is "Drift"?

**Drift** means unintended changes in output characteristics:
- ✅ **Expected changes:** Intentional logic updates, new features, content strategy pivots
- ❌ **Drift (problematic):** Accidental format changes, tone shifts, missing fields, schema breaking

## How to Use These References

### Manual Comparison Procedure

1. **Run the pipeline locally:**
   ```bash
   # Example: Run orchestrator with a test pipeline
   python orchestrator.py --pipeline pipeline.web.yml --run-id baseline_test
   ```

2. **Locate the new outputs:**
   ```bash
   cd output/baseline_test/
   ls -la
   ```

3. **Compare against references:**
   ```bash
   # Visual diff for JSON files
   diff -u samples/reference/metadata.json output/baseline_test/metadata.json
   
   # Visual diff for markdown files
   diff -u samples/reference/outline_sample.md output/baseline_test/outline.md
   
   # Or use a JSON diff tool
   jq -S . samples/reference/topics_ranked.json > /tmp/ref.json
   jq -S . output/baseline_test/topics_ranked.json > /tmp/new.json
   diff -u /tmp/ref.json /tmp/new.json
   ```

4. **Evaluate differences:**
   - **Acceptable:** Dynamic values (timestamps, specific trends, run IDs)
   - **Investigate:** Structural changes, missing fields, format shifts, tone changes
   - **Report:** Any unexpected differences to the team

### Automated Comparison (Future Enhancement)

While manual comparison is acceptable for now, consider implementing:
- Schema validation scripts (e.g., with JSON Schema)
- Structural integrity tests (check for required fields)
- Tone analysis tools (NLP-based consistency checks)

## Maintenance

- **Update frequency:** Review baseline references quarterly or after major intentional changes
- **Version control:** Keep references in git to track intentional updates
- **Documentation:** Update this README when adding/removing reference items

## Notes

- These samples are **non-PII** and safe for version control
- Samples are **trimmed** for brevity while preserving structure
- Do **not** include API keys, credentials, or sensitive data in references
- If output formats change intentionally, update these references and document the change

---

**Last updated:** 2025-12-31  
**Baseline version:** v1.0  
**Contact:** Repository maintainer for questions about drift detection
