# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

---

## [0.1.0] - 2024-11-04

### Added

- **TrendScoutAgent:** Trend analysis with 15 ranked topics
- **LocalizationSubtitleAgent:** SRT subtitle generation with timing validation
- **CLI Interface:** Command-line interface with Rich formatting (trend-scout command)
- **CI/CD Pipeline:** GitHub Actions with pytest, ruff, mkdocs
- **Unit Tests:** 85%+ code coverage (src/)
- **Documentation:** MkDocs + Material theme, internal documentation
- **Web UI:** FastAPI-based dashboard for agent configuration
- **Scheduler & Queue:** File-based job queue and cron-friendly scheduler
- **Post Templates:** Configurable templates for social media content
- **Voiceover TTS:** Google TTS integration with content-addressed storage
- **Video Rendering:** FFmpeg-based video composition with audio/video sync
- **Quality Gate:** Automated quality checks for generated content
- **YouTube Upload:** OAuth-based YouTube video uploader
- **Guardrails:** Security & safety checks (port binding, secrets detection)
- **Contract Endpoints:** FlowBiz compliance (/healthz, /v1/meta)

### Project Governance

- **License:** MIT License
- **Repository:** GitHub (github.com/natbkgift/dhamma-channel-automation)
- **Target Revenue:** 100,000 THB/month from YouTube AdSense
- **Content Goal:** 20-30 videos/month

---

## Versioning Policy

### MAJOR Version (Breaking Changes)

Increment for:
- Pipeline output contract changes (schema breaks)
- API endpoint removals or signature changes
- Backwards-incompatible config file changes

**Release Process:**
- Deprecation warning in version N-1
- Migration guide included
- Release notes highlight breaking changes prominently

### MINOR Version (New Features)

Increment for:
- New agents or pipeline steps
- New API endpoints or features
- Enhanced capabilities (backwards compatible)

**Release Process:**
- Feature documentation in release notes
- Examples in samples/ directory
- No migration needed

### PATCH Version (Bug Fixes)

Increment for:
- Bug fixes and security patches
- Documentation corrections
- Test additions (no code behavior changes)

**Release Process:**
- Brief release notes listing fixes
- Can be hotfixed on main branch
- Recommended update for all users

---

## Release Timeline

| Version | Release Date | Support Until | Status |
|---------|--------------|---------------|--------|
| 0.1.x   | 2024-11-04   | 2025-12-31    | Current |
| 0.2.0   | TBD          | TBD           | Planned |

---

## Supported Versions

Only the latest MINOR version receives bug fixes and security patches.

| Version | Bug Fixes | Security | Notes |
|---------|-----------|----------|-------|
| 0.1.x   | ✅ Yes    | ✅ Yes   | Current active |
| < 0.1   | ❌ No     | ❌ No    | Pre-release, EOL |

---

## Known Issues

### v0.1.0

- TrendScout may return duplicates in edge cases (will fix in 0.1.1)
- Subtitle timing can drift >100ms on very long videos (documented workaround in docs)
- Web UI does not support custom branding (planned for 0.2.0)

---

## Contributing

To suggest changes or report bugs, please:

1. Check [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines
2. Search existing issues to avoid duplicates
3. Follow the issue template (bug report or feature request)
4. Include relevant logs/screenshots

See [GOVERNANCE.md](GOVERNANCE.md) for release decision-making process.

---

## Attribution

This changelog format follows [Keep a Changelog](https://keepachangelog.com/) best practices.

---

**Last Updated:** 2025-01-06  
**Next Review:** When version 0.2.0 is released
