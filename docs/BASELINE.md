# Baseline Documentation

## Purpose

This document defines the **baseline behavior** of the Dhamma Channel Automation pipeline in **Client Product mode** (single-channel optimized). The baseline serves as a reference for detecting unintended behavior changes (drift) over time.

## Why Baseline Matters

In a production system, code changes, dependency updates, or external API changes can subtly alter system behavior. A baseline:

1. **Detects Drift:** Identifies unintended changes in output structure, format, tone, or content quality
2. **Ensures Consistency:** Maintains predictable behavior for the single-channel client product
3. **Facilitates Testing:** Provides reference artifacts for regression testing
4. **Documents Intent:** Captures what "correct" behavior looks like at a point in time

## What Must Stay Stable (Client Product Mode)

The following aspects of pipeline output must remain stable unless intentionally changed:

### 1. Output Structure
- **JSON Schema:** All JSON outputs must maintain consistent field names and types
- **File Naming:** Output files follow predictable naming conventions (e.g., `metadata.json`, `topics_ranked.json`, `outline.md`)
- **Directory Structure:** Pipeline creates `output/{run_id}/` with expected files
- **Voiceover Artifacts:** Deterministic TTS outputs live under `data/voiceovers/<run_id>/` with filenames like `<slug>_<sha256[:12]>.wav` and `<slug>_<sha256[:12]>.json`

### 2. Content Format
- **Metadata Format:** YouTube metadata follows established structure (title, description, tags, SEO keywords)
- **Topic Ranking Format:** Topics include rank, title, scores (impact/feasibility/alignment), reason, difficulty, risk, audience
- **Outline Structure:** Script outlines follow Hook → Intro → Main Content → CTA format with timing estimates

### 3. Content Tone & Style
- **Tone:** Accessible, warm, friendly, non-preachy (เข้าถึงง่าย, เป็นกันเอง, มีความอบอุ่น)
- **Language Mix:** Thai primary with appropriate English terms (e.g., "mindfulness", "meditation")
- **Length Targets:** Titles 60-70 chars, descriptions 500-1000 chars, videos 5-10 minutes
- **Audience Focus:** General audience interested in practical Buddhism and mindfulness

### 4. Business Logic
- **Topic Scoring:** Uses impact × feasibility × alignment formula
- **SEO Optimization:** Generates searchable keywords, thumbnail suggestions, hashtags
- **Compliance:** Content adheres to Buddhist doctrine and YouTube policies
- **Single-Channel Focus:** All outputs optimized for one Thai Buddhist mindfulness channel

### 5. Voiceover Metadata (TTS)
- **Location:** `data/voiceovers/<run_id>/<slug>_<sha256[:12]>.json`
- **Required fields (stable):**
  - `run_id` (string)
  - `slug` (string)
  - `input_sha256` (string, 64 hex chars)
  - `output_wav_path` (string, relative path)
  - `duration_seconds` (number)
  - `engine_name` (string)
- **Optional fields (informational only):**
  - `voice` (string)
  - `style` (string)
  - `created_utc` (string, not used for naming)

## Included Reference Items

The `samples/reference/` directory contains 3 baseline artifacts:

### 1. `metadata.json` (SEO Metadata)
- **Represents:** Final YouTube metadata output
- **Key Stability Points:**
  - Title format: engaging question/benefit + specifics (60-70 chars)
  - Description sections: emoji hook, overview, table of contents, benefits, hashtags
  - Tag mix: 8-15 tags, Thai/English blend, topically relevant
  - Thumbnail suggestions: 3 creative ideas with specific visual elements
  - SEO keywords: 4-7 audience-focused search terms

### 2. `topics_ranked.json` (Topic Prioritization)
- **Represents:** Ranked topic list from TrendScout/TopicPrioritizer
- **Key Stability Points:**
  - Score structure: impact (1-10), feasibility (1-10), alignment (1-10), total (calculated)
  - Ranking order: descending by total score
  - Reasoning: trend awareness, audience fit, timing considerations
  - Risk assessment: difficulty level, risk level, target audience

### 3. `outline_sample.md` (Script Outline)
- **Represents:** Structured content outline for scriptwriting
- **Key Stability Points:**
  - Section flow: Hook (0-0.5min) → Intro (0.5-1.5min) → Main (3-4min) → CTA (0.5min)
  - Timing estimates: Realistic for 5-7 minute video
  - Tone guidance: Accessible, warm, friendly
  - Content depth: Practical, actionable, doctrinally sound

## Comparison Procedure

### Step 1: Run the Pipeline

Run the pipeline locally with a test configuration:

```bash
# Using orchestrator (full pipeline)
python orchestrator.py --pipeline pipeline.web.yml --run-id baseline_check_$(date +%Y%m%d)

# Or using CLI (specific agent)
python -m cli.main trend-scout --input data/mock_input.json --out output/test_topics.json
```

### Step 2: Locate New Outputs

```bash
cd output/baseline_check_YYYYMMDD/
ls -la
```

Expected files: `metadata.json`, `topics_ranked.json`, `outline.md`, `script.md`, etc.

### Step 3: Compare Against Baseline

**Option A: Manual Visual Diff**
```bash
# JSON files
diff -u samples/reference/metadata.json output/baseline_check_YYYYMMDD/metadata.json

# Markdown files
diff -u samples/reference/outline_sample.md output/baseline_check_YYYYMMDD/outline.md
```

**Option B: Structured JSON Comparison**
```bash
# Normalize and compare JSON
jq -S . samples/reference/topics_ranked.json > /tmp/baseline.json
jq -S . output/baseline_check_YYYYMMDD/topics_ranked.json > /tmp/current.json
diff -u /tmp/baseline.json /tmp/current.json
```

**Option C: Field-by-Field Validation (Python)**
```python
import json

# Load files
with open('samples/reference/metadata.json') as f:
    baseline = json.load(f)
with open('output/baseline_check_YYYYMMDD/metadata.json') as f:
    current = json.load(f)

# Check structure
assert set(baseline.keys()) == set(current.keys()), "Top-level keys changed"
assert isinstance(current['tags'], list), "Tags should be a list"
assert 60 <= len(current['title']) <= 80, "Title length out of range"
# Add more checks as needed
```

### Step 4: Evaluate Differences

**Acceptable Differences:**
- Dynamic values: `generated_at`, `prioritized_at`, `run_id`, timestamps
- Content specifics: Actual topic titles, specific trends, current events
- Ordering: Minor variations in list ordering (if not explicitly ranked)

**Investigate These:**
- Missing or extra top-level fields
- Type changes (string → number, list → dict)
- Format shifts (title length, description structure)
- Tone changes (formal → casual, clinical → warm)
- Logic changes (scoring formula, ranking criteria)

**Immediate Action Required:**
- Security issues (exposed credentials, PII leaks)
- Schema breaking changes (downstream systems broken)
- Compliance violations (doctrine errors, policy violations)

### Step 5: Document and Decide

If drift is detected:
1. **Document:** Record what changed, when, and potential cause
2. **Classify:** Intentional change vs. accidental drift
3. **Decide:**
   - **Intentional:** Update baseline references, document in CHANGELOG
   - **Accidental:** Fix the code, re-test, validate baseline still holds
   - **Acceptable:** Note in comments, monitor for future occurrences

## Updating the Baseline

The baseline should be updated when:
- **Intentional changes:** New features, improved algorithms, strategic pivots
- **Format improvements:** Better output structure, enhanced metadata
- **Periodic refresh:** Quarterly review to reflect evolved standards

**Update Process:**
1. Verify changes are intentional and reviewed
2. Run pipeline to generate new reference outputs
3. Copy new outputs to `samples/reference/` (trimmed if needed)
4. Update `samples/reference/README.md` to explain changes
5. Update this document (`docs/BASELINE.md`) if stability guarantees change
6. Commit with clear message: "Update baseline: [reason]"

## Testing Strategy

### Manual Testing (Current)
- Run pipeline before major releases
- Compare outputs against `samples/reference/`
- Visual inspection of key fields

### Future Automated Testing
- **Schema validation:** JSON Schema tests for all outputs
- **Structure tests:** Pytest assertions on field presence/types
- **Tone analysis:** NLP-based consistency checks (future)
- **Regression suite:** Golden file tests comparing current vs. baseline

## Relationship to Global Kill Switch

The baseline and kill switch serve complementary purposes:

- **Baseline:** Detects *what* changed (drift detection)
- **Kill Switch:** Controls *when* pipeline runs (operational safety)

When the kill switch is enabled (`PIPELINE_ENABLED=false`), the pipeline stops before producing outputs, ensuring no drift can occur during maintenance or policy pauses.

## Notes for Developers

- **Do not modify baseline files casually:** They represent agreed-upon behavior
- **Test changes against baseline:** Before merging, validate no unintended drift
- **Update docs with code:** If output format changes, update baseline documentation
- **Keep samples small:** Trim reference files to essential structure (non-PII)
- **Version baselines:** Track baseline changes in git for auditability
- **AGENTS.md:** Repo has no AGENTS.md; followed existing conventions instead

## Contact

Questions about baseline behavior or drift detection:
- Repository maintainer
- Review `samples/reference/README.md` for detailed comparison guidance

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-26  
**Applies to:** Dhamma Channel Automation v1.x (Client Product Mode)
