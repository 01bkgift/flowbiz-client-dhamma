# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it **privately** to:

- **Email:** [maintainer-contact]@example.com
- **Subject:** `[SECURITY] Vulnerability Report - <brief description>`
- **Do NOT open a public GitHub issue**

We will respond to your report within **72 hours** and coordinate a fix with you.

## Supported Versions

| Version | Supported     | Notes |
|---------|---------------|-------|
| 0.1.x   | ✅ Yes (main) | Current active version |
| < 0.1   | ❌ No         | Pre-release, no security support |

## Security Considerations

This project handles sensitive operations including YouTube OAuth credentials and automated content distribution. The following security practices MUST be observed:

### Secrets Management
- ✅ All secrets (YouTube OAuth tokens, API keys, credentials) **must** be passed via environment variables
- ✅ NO secrets hardcoded in source code, configuration files, or documentation
- ✅ NO secrets in commit history or Git logs
- ✅ Use `.env.example` for non-secret defaults only

### Network Security
- ✅ Port binding **must** use localhost only (127.0.0.1 or ::1)
- ✅ NO listening on 0.0.0.0 (all interfaces) in production
- ✅ Enforced via `scripts/guardrails.sh` checks

### Dependency Security
- ✅ Pin all dependencies to specific versions in `pyproject.toml`
- ✅ Regularly audit dependencies: `pip-audit` (recommended)
- ✅ Update dependencies quarterly or on security alerts
- ✅ Verify checksums for critical dependencies

### Code Review & Testing
- ✅ All PRs require code owner review before merge
- ✅ Automated tests must pass (pytest with coverage)
- ✅ Linting must pass (ruff format + check)
- ✅ Preflight checks must pass (guardrails validation)

### Incident Response Process

1. **Discovery:** Vulnerability reported (see "Reporting a Vulnerability" above)
2. **Acknowledgment:** Maintainer confirms receipt within 72 hours
3. **Investigation:** Assess scope, severity, affected versions (within 5 business days)
4. **Fix:** Develop and test patch (within 2 weeks for critical issues)
5. **Release:** Publish patch release with security advisory
6. **Notification:** Inform reporter and document in GitHub Security Advisories

### Severity Classification

- **Critical:** Remote code execution, credential theft, data loss → patch within 1 week
- **High:** Authentication bypass, information disclosure → patch within 2 weeks
- **Medium:** Denial of service, privilege escalation → patch within 4 weeks
- **Low:** Best practice improvements, defense-in-depth → patch within 8 weeks

## Contact & Attribution

- **Security Contact:** [maintainer-email]@example.com
- **Coordinated Disclosure:** We credit researchers who responsibly disclose vulnerabilities
- **Policy Version:** 1.0 (adopted 2025-01-06)

## Additional Resources

- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security/getting-started/best-practices-for-repository-security)
- [Python Security Documentation](https://python.readthedocs.io/en/stable/library/security_warnings.html)

---

**Last Updated:** 2025-01-06  
**Status:** Effective  
**Next Review:** 2025-04-06 (quarterly)
