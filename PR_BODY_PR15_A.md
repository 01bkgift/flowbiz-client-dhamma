# PR15.A: Runbook for Soft-Live (Unlisted) Verification on VPS

## Summary

เพิ่ม runbook สำหรับ verify Soft-Live "unlisted" mode บน production VPS

**เป็น docs-only PR** ไม่มีการเปลี่ยนแปลง code, pipeline order, หรือ runtime semantics

---

## What Was Added

### 1. New Runbook

- `docs/RUNBOOK_SOFT_LIVE_UNLISTED_VERIFY.md`
  - Safety guardrails
  - Pre-flight checks (health, credentials, port binding)
  - Configure unlisted mode
  - Run pipeline with explicit run_id
  - Approval gate handling (timeout-based auto-approve)
  - Success criteria และ evidence collection
  - Rollback กลับ dry_run
  - Troubleshooting section

### 2. Updated Docs (Links Only)

- `docs/RUNBOOK_VPS_PRODUCTION.md` - เพิ่มลิงก์ใน Related Docs
- `docs/DEPLOYMENT.md` - เพิ่มลิงก์ใน VPS Production Docs table

---

## Explicit Non-Goals

| ❌ ไม่ทำ | เหตุผล |
|---------|--------|
| เปลี่ยน pipeline order | Out of scope |
| เปลี่ยน code behavior | Docs-only PR |
| เพิ่ม CI/CD automation | Not in this PR |
| เพิ่ม secrets ลง repo | Security policy |
| เพิ่ม external tooling | Ops-safe constraint |

---

## Verification Checklist

### Runbook Completeness

- [x] Safety guardrails (A)
- [x] Pre-checks with STOP conditions (B)
- [x] Configure procedure (C)
- [x] Run pipeline procedure (D)
- [x] Approval gate handling (E)
- [x] Success criteria (F)
- [x] Evidence collection (G)
- [x] Rollback procedure (H)
- [x] Troubleshooting (I)

### Technical Accuracy

- [x] Uses correct path: `/opt/flowbiz-client-dhamma`
- [x] Uses correct artifact names: `approval_gate_summary.json`, `soft_live_summary.json`, `youtube_upload_summary.json`
- [x] Uses correct pipeline: `pipelines/youtube_upload_smoke_requires_quality.yaml`
- [x] Uses correct approval mechanism: timeout-based (2 ชม.)
- [x] Uses correct cancel file path: `output/<run_id>/control/cancel_publish.json`

### Security

- [x] ไม่มี secrets ใน runbook
- [x] ไม่มี credentials placeholders
- [x] มีคำเตือนห้ามใช้ `public` mode
- [x] ตรวจสอบ port binding `127.0.0.1`

### Documentation Links

- [x] Links ใน RUNBOOK_VPS_PRODUCTION.md ถูกต้อง
- [x] Links ใน DEPLOYMENT.md ถูกต้อง
- [x] Related docs ใน runbook ใหม่ถูกต้อง
