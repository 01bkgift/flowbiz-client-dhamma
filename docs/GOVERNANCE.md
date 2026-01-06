# Repository Governance

**Status:** Formal governance policy (effective 2025-01-06)  
**Scope:** dhamma-channel-automation project on GitHub  
**Audience:** Contributors, maintainers, FlowBiz stakeholders

---

## 1. Overview

This document defines governance rules for the `dhamma-channel-automation` repository, including decision-making processes, change control, code review, and repository maintenance.

The project is **internal-facing** with a single primary maintainer (@natbkgift) and optional contributor roles. All governance rules are designed to:
- Ensure code quality & backwards compatibility (CI/CD checks)
- Track changes & decisions (CHANGELOG, commit history)
- Protect sensitive operations (security policy, secrets management)
- Maintain deterministic outputs (BASELINE.md contracts)

---

## 2. Branch Protection Rules

### Main Branch (`main`)

**Enforcement:** ENABLED (non-bypassable except for maintainer force-push)

| Rule | Status | Details |
|------|--------|---------|
| Require pull request reviews | ✅ Yes | Minimum 1 approval required |
| Require status checks to pass | ✅ Yes | See section 3 (CI/CD) |
| Require code owner review | ✅ Yes | CODEOWNERS file enforced |
| Dismiss stale reviews | ✅ Yes | New commits reset approval state |
| Allow force pushes | ❌ No | Maintainer only, via manual bypass |
| Allow deletions | ❌ No | No branch deletion allowed |
| Require branches up-to-date | ✅ Yes | Rebase before merge |

### Feature Branches

**Naming Convention:**
- `feature/pr-{issue-number}-{description}` (new features, major changes)
- `fix/{description}` (bug fixes)
- `copilot/{description}` (Copilot-generated experimental branches)
- `docs/{description}` (documentation-only changes)

**Cleanup:** Automatic deletion after merge enabled

**Merge Strategy:** Squash or rebase preferred (no merge commits for history clarity)

---

## 3. CI/CD Checks & Validation Gates

All PRs to `main` must pass these automated checks (blocking):

| Job | Command | Purpose | Failure = Blocking |
|-----|---------|---------|---|
| **Lint** | `ruff check .` | Code style violations | ✅ Yes |
| **Format** | `ruff format --check .` | Formatting consistency | ✅ Yes |
| **Test** | `pytest -q` | Unit tests (min coverage = baseline) | ✅ Yes |
| **Coverage** | Coverage report XML | Regression detection | ✅ Yes (no decrease) |
| **Docs Build** | `mkdocs build --strict` | Documentation validity | ✅ Yes (main branch only) |
| **Preflight** | `bash scripts/preflight.sh` | System integrity checks | ✅ Yes (main branch only) |

**Coverage Policy:**
- Source path: `src/` only
- Minimum: No regression (must be >= baseline)
- Report format: XML + term-missing
- Artifacts: Uploaded to GitHub (retention = 90 days)

**Workflow Permissions:**
- `contents: read` (restrictive, no write access)
- Concurrency: Prevent duplicate runs (`cancel-in-progress`)
- Secrets: GitHub-managed only (no hardcoded credentials)

---

## 4. Pull Request Process

### Step 1: Create PR

1. Create feature branch from `main`: `git checkout -b feature/pr-{issue}-{title}`
2. Make changes (commit frequently with clear messages)
3. Push branch: `git push origin feature/pr-{issue}-{title}`
4. Open PR on GitHub with comprehensive description:
   - Type of change (bug fix, feature, docs, refactoring, etc.)
   - Description of changes (what, why, how)
   - Testing performed (manual + automated)
   - Screenshots/examples (if applicable)
   - Checklist items completed (see PR template)

### Step 2: Automated Checks

- GitHub Actions runs CI/CD (linting, tests, docs)
- All checks must pass (green checkmarks)
- Failed checks block merge (no bypass option)

### Step 3: Code Review

- Code owner reviews PR (see CODEOWNERS)
- Minimum 1 approval required
- Reviewers check:
  - Code quality (ruff standards met)
  - Test coverage (no regressions)
  - Breaking changes (documented if present)
  - Security (no credentials, proper isolation)
  - Backwards compatibility (migration guide if needed)
  - Documentation (guides, docstrings updated)
  - FlowBiz compliance (contract endpoints working)

### Step 4: Approval & Merge

- Once approved + all checks pass → merge enabled
- Merge strategy: Squash (single commit) or rebase (preserve history)
- NO merge commits (for clean history)
- Feature branch auto-deleted after merge

### Step 5: Post-Merge

- PR closes automatically
- Release notes updated (if applicable)
- Issue linked to PR auto-closes

---

## 5. Testing Requirements

### Unit Tests

**Command:** `pytest -q`  
**Coverage:** `--cov=src --cov-report=term-missing`  
**Requirements:**
- All existing tests must pass
- New features must include unit tests
- Coverage must not decrease from baseline
- Max fail: 1 (stops on first failure for faster feedback)

### Integration Tests

**Manual testing checklist (from PR template):**
- [ ] Tested locally
- [ ] Tested in Docker container (if applicable)
- [ ] Contract endpoints tested (/healthz, /v1/meta)
- [ ] No regressions in existing functionality

### Code Quality

**Linting:** `ruff check .`  
**Formatting:** `ruff format --check .` (or auto-format: `ruff format .`)  
**Type checking:** mypy (included in dev dependencies)

### Preflight Checks

**Command:** `bash scripts/preflight.sh`  
**Checks:**
- System integrity (Python version, dependencies)
- Port binding (localhost-only, no 0.0.0.0)
- Guardrails compliance (secrets not exposed, etc.)

---

## 6. Release Process & Versioning

### Versioning Scheme

**Semantic Versioning:** `MAJOR.MINOR.PATCH`

- **MAJOR:** Breaking changes to pipeline contracts or APIs
- **MINOR:** New features, additions (backwards compatible)
- **PATCH:** Bug fixes, documentation (no feature changes)

### Release Steps

1. **Update Version:** Bump `version` in `pyproject.toml`
2. **Update Changelog:** Document changes in `docs/CHANGELOG.md` (following Keep a Changelog format)
3. **Tag Release:** `git tag -a v{version} -m "Release {version}"`
4. **Push Tag:** `git push origin v{version}`
5. **Create GitHub Release:** Add release notes from changelog
6. **Announce:** Notify stakeholders via email/Slack

### Breaking Changes

If release includes breaking changes:

1. **Document fully:**
   - What changed (API, output schema, behavior)
   - Why it changed (rationale)
   - How to migrate (step-by-step guide)

2. **Deprecation timeline (if phased):**
   - Version N: Old way deprecated (warning messages)
   - Version N+1: New way only (breaking change)

3. **Major version bump:** MAJOR version increased
4. **Release notes:** Highlight breaking changes prominently

### Supported Versions

| Version | Status | Support until |
|---------|--------|---|
| 0.1.x   | Current | 2025-12-31 (1 year) |
| < 0.1   | EOL | No support |

---

## 7. Code Style & Standards

### Python Code

**Framework:** Python 3.11+  
**Formatter:** ruff (configured in `pyproject.toml`)  
**Linter:** ruff  
**Type hints:** mypy (required for new code)

**Style Rules:**
- Line length: 88 characters (ruff default)
- Imports: Organized (standard > third-party > local)
- Docstrings: Required for public functions/classes
  - English for technical code
  - Thai for business logic (where appropriate)
- Type hints: Required for function parameters & returns
- Comments: Clear, concise, explaining WHY not WHAT

### Documentation

**Format:** Markdown (.md files)  
**Location:** 
- User guides: `docs/`
- Internal docs: `docs/` (via .gitignore: docs never public)
- API docs: Docstrings in code
- Changelog: `docs/CHANGELOG.md`

**Style:**
- Clear headings (H1-H3)
- Code blocks with language specifier
- Tables for structured data
- Links to related docs
- Thai language for user-facing docs, English for technical reference

### Git Commits

**Format:** Conventional Commits

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `refactor:` Code restructuring (no behavior change)
- `perf:` Performance improvement
- `test:` Test addition/modification
- `chore:` Build, dependency, tooling updates

**Subject:** Max 50 characters, present tense, no period  
**Body:** Wrap at 72 characters, explain what & why  
**Footer:** Reference issue: `Fixes #123`

---

## 8. Change Control & Decision Making

### Minor Changes (Bug fixes, docs, refactoring)

**Process:**
1. Create PR with clear description
2. Automated checks must pass
3. Code owner review (1 approval)
4. Merge to main
5. Auto-included in next release

**Timeline:** Same-day (if unblocked)

### Major Changes (New features, breaking changes)

**Process:**
1. Open issue describing proposal + rationale
2. Discuss in issue (3-5 days for feedback)
3. Design document (if complex)
4. Code review (more detailed, may require multiple passes)
5. Merge to main
6. Included in next release

**Timeline:** 1-2 weeks (depending on complexity)

### Configuration Changes

**Process:**
1. Update `.env.example` (non-secret defaults)
2. Document in `docs/DEPLOYMENT.md` or relevant guide
3. Test locally + in CI
4. Include migration guide if breaking

### Emergency/Hotfix

**Process:**
1. Create hotfix branch from main
2. Minimal fix only (no refactoring/feature creep)
3. Test thoroughly locally + in CI
4. Single code owner approval (fast-tracked)
5. Merge to main
6. Immediate patch release (bump PATCH version)

**SLA:** 4 hours for critical security hotfixes

---

## 9. Governance Review & Updates

### Review Cadence

| Frequency | Items | Owner |
|-----------|-------|-------|
| Quarterly (every 3 months) | Governance rules, branch protection | Maintainer |
| Quarterly (every 3 months) | Supported versions, dependencies | Maintainer |
| Annually (every 12 months) | ISO/SOC2 compliance audit | Maintainer |
| As-needed | Process improvements, exceptions | Maintainer |

### Update Process

1. Open issue with proposed change + rationale
2. Discuss (1 week comment period)
3. Update governance document (this file)
4. Tag new version in document header
5. Create PR with changes
6. Merge and announce

### Exception Handling

**When to request exception:**
- Governance rules block necessary work
- Security incident requires emergency bypass
- Performance/reliability crisis needs quick fix

**Exception process:**
1. Describe exception + rationale in issue
2. Get explicit maintainer approval
3. Document exception in PR (reason + date)
4. Schedule review post-incident

---

## 10. Compliance & Audit Trail

### Audit Logging

Maintained for:
- Code changes (git commit history)
- PR approvals (GitHub PR audit trail)
- CI/CD results (GitHub Actions logs)
- Releases (GitHub Releases)
- Governance updates (this file + git history)

### Artifact Retention

| Artifact | Retention | Location |
|----------|-----------|----------|
| CI/CD logs | 90 days | GitHub Actions |
| Coverage reports | 90 days | GitHub Actions artifacts |
| Documentation builds | 30 days | GitHub Actions artifacts |
| Release notes | Indefinite | GitHub Releases |

### Policy Compliance

- **ISO/SOC2 baseline:** SECURITY.md, CODEOWNERS, testing, code review
- **Data protection:** Environment variables only (no hardcoded secrets)
- **Security:** Network isolation (localhost-only), dependency audits
- **Determinism:** BASELINE.md contracts (output stability tracking)

---

## 11. Governance Contacts & Escalation

| Role | Contact | Responsibility |
|------|---------|-----------------|
| **Maintainer** | @natbkgift | Merge approval, releases, governance |
| **Code Owners** | See CODEOWNERS | PR review, code quality |

### Escalation Path

1. **Code review question** → Ask in PR comments
2. **Process question** → Open issue with "governance" label
3. **Urgent blocker** → Ping maintainer directly (Slack/email)
4. **Security issue** → See SECURITY.md (private reporting)

---

## Appendix A: Related Documents

- **PR Template:** `.github/pull_request_template.md`
- **Security Policy:** `.github/SECURITY.md`
- **Code Owners:** `.github/CODEOWNERS`
- **Baseline Contracts:** `docs/BASELINE.md`
- **Asset Policy:** `docs/ASSETS_POLICY.md`
- **Changelog:** `docs/CHANGELOG.md`
- **Copilot Instructions:** `.github/copilot-instructions.md`

---

**Document Version:** 1.0  
**Effective Date:** 2025-01-06  
**Last Updated:** 2025-01-06  
**Next Review:** 2025-04-06 (quarterly)  
**Status:** APPROVED & ENFORCEABLE
