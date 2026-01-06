## Summary

<!-- Provide a clear and concise description of your changes -->

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Test coverage improvement
## Why

## Testing

### Manual Testing

<!-- Describe the manual testing you performed -->

- [ ] Tested locally
- [ ] Tested in Docker container
- [ ] Tested contract endpoints (/healthz, /v1/meta)
- [ ] Tested existing functionality (no regressions)

### Automated Testing

- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Test coverage maintained or improved

### Test Commands

```bash
# Commands used to test this PR
pytest -xvs
bash scripts/guardrails.sh
curl http://127.0.0.1:3007/healthz
curl http://127.0.0.1:3007/v1/meta
```

## FlowBiz Compliance Checklist

- [ ] No breaking changes to existing functionality
- [ ] Contract endpoints operational (if applicable)
- [ ] Environment variables documented in .env.example
- [ ] Port binding uses localhost only (127.0.0.1)
- [ ] Documentation updated (if needed)
- [ ] Guardrails pass (warnings documented below)
- [ ] No security vulnerabilities introduced
- [ ] Agent baseline updated (if behavior changed)

## Documentation

- [ ] README updated (if needed)
- [ ] API documentation updated (if needed)
- [ ] Configuration documentation updated (if needed)
- [ ] Migration guide provided (if breaking changes)

## Code Quality

- [ ] Code follows project style guidelines
- [ ] Comments added for complex logic
- [ ] No console.log or debug code left
- [ ] No TODO/FIXME comments without context
- [ ] Linter passes (ruff check)
- [ ] Formatter passes (ruff format)
- [ ] Type checking passes (mypy)
- [ ] ruff format --check .
- [ ] ruff check .
- [ ] pytest -q

## Security

- [ ] No secrets or credentials committed
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Input validation implemented
- [ ] Authentication/authorization preserved
- [ ] CORS configured correctly

## Deployment Considerations

- [ ] No database migrations required
- [ ] No environment variable changes required
- [ ] No infrastructure changes required
- [ ] Backwards compatible with existing deployments
- [ ] Rollback plan documented (if needed)

## Smoke Test Commands

<!-- Provide commands to quickly verify this PR works -->

```bash
# Start service
docker-compose up -d

# Test health
curl http://127.0.0.1:3007/healthz

# Test metadata
curl http://127.0.0.1:3007/v1/meta

# Run tests
pytest tests/test_flowbiz_endpoints.py -xvs

# Run guardrails
bash scripts/guardrails.sh

# Cleanup
docker-compose down
```

## Guardrail Warnings

<!-- If guardrails produced warnings, document them here -->

- None

## Related Issues

<!-- Link to related issues -->

Closes #<!-- issue number -->

## Screenshots

<!-- If applicable, add screenshots to show UI changes -->

## Checklist

- [ ] I have performed a self-review of my code
- [ ] I have commented my code where necessary
- [ ] I have updated the documentation accordingly
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published
- [ ] No secrets committed
## Evidence (optional)

<!-- Provide any screenshots, logs, or other evidence to support your changes. -->
