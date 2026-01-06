# Contributing to Dhamma Channel Automation

Thank you for your interest in contributing to this project! 🙏 This document provides guidelines and instructions for contributing.

---

## Getting Started

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/natbkgift/dhamma-channel-automation.git
   cd dhamma-channel-automation
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or: venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify setup:**
   ```bash
   python -c "import src.automation_core; print('✓ Setup OK')"
   ```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# From main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/pr-{issue-number}-{description}
# Example: feature/pr-123-add-tts-caching
```

### 2. Make Changes

Edit code in one of these directories:
- `src/` - Core automation framework
- `app/` - Web UI (FastAPI)
- `scripts/` - Helpers and runners
- `docs/` - Documentation
- `tests/` - Test files

**Do NOT modify:**
- `.github/workflows/*.yml` (CI/CD config) unless adding CI step
- `pyproject.toml` (dependencies) without discussion
- `orchestrator.py` (main orchestrator) without understanding AGENTS mapping

### 3. Run Local Validation

Before pushing, run:

```bash
# Format code
ruff format .

# Check linting
ruff check .

# Run tests
pytest -q

# Run preflight checks (if modifying runtime code)
bash scripts/preflight.sh
```

All must pass before commit.

### 4. Commit with Clear Messages

Use **Conventional Commits** format:

```bash
git add <files>
git commit -m "feat: add TTS caching for repeated segments

- Implement LRU cache for TTS requests
- Reduces API calls by ~30% for typical workflows
- Cache key: hash(text + voice + language)
- Expiry: 24 hours

Fixes #123"
```

**Commit types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `refactor:` Code restructuring (no behavior change)
- `perf:` Performance improvement
- `test:` Test addition/modification
- `chore:` Build/dependency updates

### 5. Push and Open PR

```bash
git push origin feature/pr-{issue}-{description}
```

Then open a Pull Request on GitHub with:
- **Title:** Concise description (matches commit message)
- **Description:** Use PR template (see .github/pull_request_template.md)
- **Testing:** Document manual + automated tests performed
- **Screenshots:** Add if visual changes
- **Checklist:** Complete all items

### 6. Address Feedback

- Push additional commits (don't amend shared history)
- Reply to review comments
- Re-run validation after changes
- Request re-review when ready

### 7. Merge

Once approved + all checks pass:
- Squash commits before merge (for clean history)
- Delete feature branch after merge
- Verify main CI/CD passes

---

## Code Style Guide

### Python Code

**Formatter:** ruff (see `pyproject.toml` for settings)

```bash
ruff format .           # Auto-format
ruff check .            # Linting checks
```

**Style Rules:**
- Line length: 88 characters max
- Imports: Standard → Third-party → Local (use `isort` logic)
- Docstrings: Required for public functions/classes
- Type hints: Use for new functions (mypy compatible)
- No trailing whitespace

**Example:**

```python
"""Module docstring in English."""

from typing import Optional
from pydantic import BaseModel


class TrendInput(BaseModel):
    """Trend analysis input schema (Thai docs in code comments)."""
    
    keywords: list[str]
    region: str = "TH"
    language: str = "th"
    
    def validate_keywords(self) -> bool:
        """Validate keyword list is not empty and contains valid terms."""
        if not self.keywords:
            raise ValueError("Keywords cannot be empty")
        return True


def analyze_trends(input_data: TrendInput) -> dict[str, any]:
    """Analyze trends from input.
    
    Args:
        input_data: Trend analysis parameters
        
    Returns:
        Dictionary with trend scores and recommendations
        
    Raises:
        ValueError: If input validation fails
    """
    # Validate
    if not input_data.validate_keywords():
        raise ValueError("Invalid keywords")
    
    # Process...
    return {"trends": [...]}
```

### Documentation

**Markdown format:**
- Clear headings (H1 for title, H2 for major sections)
- Code blocks with language identifier
- Tables for structured data
- Thai language for user guides, English for technical reference
- Links to related docs

**Example:**

```markdown
## การตั้งค่า TTS

> ℹ️ **บันทึก:** ตั้งค่าตัวแปรสภาพแวดล้อมก่อนจะเรียกใช้

### ขั้นตอน

1. สร้างไฟล์ `.env`:
   ```bash
   GOOGLE_TTS_KEY=your_key
   ```

2. ทดสอบการเชื่อมต่อ:
   ```bash
   python -c "from src.automation_core import tts; tts.test()"
   ```
```

---

## Testing Requirements

### Unit Tests

All changes to `src/` or `app/` should include unit tests:

```bash
# Run all tests
pytest -q

# Run specific test file
pytest tests/test_agents.py -v

# Run with coverage
pytest --cov=src --cov-report=term-missing
```

**Test file naming:** `tests/test_{module}.py`

**Example test:**

```python
import pytest
from src.agents.trend_scout import TrendScoutAgent, TrendScoutInput


def test_trend_scout_ranking():
    """Test trend ranking produces scores."""
    agent = TrendScoutAgent()
    input_data = TrendScoutInput(keywords=["mindfulness", "meditation"])
    result = agent.run(input_data)
    
    assert len(result.topics) == 15
    assert all(t.score >= 0 for t in result.topics)
    assert result.topics[0].score >= result.topics[-1].score  # Sorted


def test_trend_scout_empty_keywords():
    """Test error handling for empty keywords."""
    agent = TrendScoutAgent()
    input_data = TrendScoutInput(keywords=[])
    
    with pytest.raises(ValueError):
        agent.run(input_data)
```

### Manual Testing

For UI/integration changes:

```bash
# Start web server
python app/main.py

# Test endpoints
curl http://127.0.0.1:3007/healthz
curl http://127.0.0.1:3007/v1/meta

# Test in browser
# http://127.0.0.1:3007 (if frontend enabled)
```

### Coverage

- **Minimum:** Same or higher than existing (no decrease)
- **Target:** 80%+ for new code
- **Report:** `pytest --cov=src --cov-report=term-missing`

---

## Reporting Bugs

Found a bug? Open an issue using the **Bug Report** template:

```markdown
### Description
Brief description of the bug

### Steps to Reproduce
1. Run command X
2. Observe Y
3. Expected Z, but got W

### Environment
- OS: Windows 10 / macOS 14 / Ubuntu 22.04
- Python: 3.11.x
- Branch: main or feature/...

### Logs/Screenshots
Paste relevant error messages or screenshots
```

---

## Requesting Features

Want to suggest an improvement? Open an issue using the **Feature Request** template:

```markdown
### Description
What new feature would be helpful?

### Rationale
Why is this needed? What problem does it solve?

### Proposed Solution
How might this be implemented?

### Alternatives Considered
Any other approaches?
```

---

## Security

Found a security vulnerability? **Do NOT open a public issue.**

See [SECURITY.md](.github/SECURITY.md) for how to report privately.

---

## Documentation Changes

If modifying documentation:

1. Update `.md` files in `docs/`
2. Check rendering: `mkdocs serve` (view on http://127.0.0.1:8000)
3. Test links and code blocks
4. Test on multiple browsers if needed

**Docs build on main:** `mkdocs build --strict`

---

## Dependency Changes

Adding a new dependency? Before submitting PR:

1. ✅ Verify it's in PyPI (or GitHub)
2. ✅ Pin to specific version in `pyproject.toml`
3. ✅ Check for security issues (`pip-audit`)
4. ✅ Document why it's needed in PR
5. ✅ Update `requirements.web.txt` if needed

**Do NOT:**
- Use `*` or `>=` for version pinning (except for test dependencies)
- Add dependencies without justification

---

## Release Process (for Maintainers)

Only maintainers perform releases, but contributors should understand the process:

1. Update `version` in `pyproject.toml`
2. Update `docs/CHANGELOG.md`
3. Commit: `git commit -m "chore: bump version to 0.2.0"`
4. Tag: `git tag -a v0.2.0 -m "Release 0.2.0"`
5. Push: `git push origin main && git push origin v0.2.0`
6. Create GitHub Release with changelog

---

## Communication

- **Questions?** Open an issue with "question" label
- **Discussion?** Start a GitHub Discussion
- **Urgent?** Mention @natbkgift in PR or issue
- **Security?** Email security contact (see SECURITY.md)

---

## Code of Conduct

Please review [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - we're committed to maintaining a respectful, inclusive community.

---

## Recognition

Contributors will be recognized in:
- Release notes
- GitHub contributors page
- Project README (major contributions)

Thank you for contributing! 🙏

---

**Last Updated:** 2025-01-06  
**Questions?** Open an issue with "governance" label
