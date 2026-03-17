# ADR 0004: Modal for Serverless Compute

**Status:** Accepted
**Date:** 2026-03-01 (Phase 1)
**Deciders:** Project lead

## Context

The pipeline needs to run 6 scheduled functions (job collection, queue processing, maintenance) plus on-demand tasks (ESCO seeding, backfills, salary training, search endpoint). Options considered:

1. **AWS Lambda** — mature, complex IAM/VPC setup, cold starts, 15-min timeout
2. **Google Cloud Run** — container-based, good for long tasks, requires GCP setup
3. **Modal** — Python-native serverless, $30/month free credit, simple decorator-based API

## Decision

Use **Modal** for all pipeline compute. Functions are defined with Python decorators (`@app.function`, `@modal.Cron`) in a single file (`pipeline/src/modal_app.py`).

### Why Modal

| Factor | Modal | AWS Lambda | Cloud Run |
|--------|-------|-----------|-----------|
| Setup | `pip install modal` + decorator | IAM, VPC, layers, SAM/CDK | Dockerfile, GCP project |
| Cron | `@modal.Cron("*/30 * * * *")` | EventBridge rule | Cloud Scheduler |
| Timeout | Up to 86400s | 900s max | 3600s max |
| Cold start | ~2-5s | ~1-10s | ~5-15s |
| Cost at our scale | $0 ($30 free credit > ~$8-10 usage) | ~$5-10/month | ~$5-10/month |
| Python DX | Native (decorators, type hints) | Zip packages, layers | Dockerfile |

## Consequences

### Positive
- **$0 cost** at current scale (free credit covers usage)
- **Single file deployment:** `modal deploy src/modal_app.py`
- **Built-in cron:** No external scheduler needed
- **Long timeouts:** daily_maintenance runs up to 1200s
- **Secrets management:** `modal.Secret.from_name("atoz-env")`

### Negative
- **Vendor lock-in:** Modal-specific decorators and API
- **Smaller ecosystem:** Less community support vs AWS/GCP
- **No local emulation:** Must use `modal serve` for local testing
- **Free tier dependency:** If pricing changes, need to migrate

### Migration Path
If Modal becomes unavailable: refactor decorators to standard async functions, deploy as Cloud Run containers or AWS Lambda with longer timeout configurations.

## References
- `pipeline/src/modal_app.py` (all Modal functions)
- `DEPENDENCIES.md` (Modal cron schedules and timeouts)
- `.github/workflows/modal-deploy.yml` (CI/CD)
