# PR Opening Message Templates

## ChatGPT 5.2 message
```
Repo: <org>/<repo>
Branch: <branch-name>
PR Title: <title>

Allowed files:
- <path>
- <path>

Summary:
- <what changed>

Testing:
- ran: <command> / not ran: <reason>

Security:
- No secrets
- No external calls
- No runtime changes

Post-merge UI checklist (text-only, no UI changes):
- [ ] Verified no UI changes required
- [ ] If UI changes were required, open a follow-up UI PR
```

## Antigravity/Codex message
```
Repo: <org>/<repo>
Branch: <branch-name>
PR Title: <title>

Allowed files (hard lock):
- <path>
- <path>

Summary:
- <what changed>

Testing:
- ran: <command> / not ran: <reason>

Security assertions:
- No secrets
- No external calls
- No runtime changes

Post-merge UI checklist (text-only, no UI changes):
- [ ] Verified no UI changes required
- [ ] If UI changes were required, open a follow-up UI PR
```
