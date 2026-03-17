# ADR 0005: Cloudflare Pages for Frontend Hosting

**Status:** Accepted
**Date:** 2026-03-10 (Phase 3)
**Deciders:** Project lead

## Context

Phase 3 adds a Next.js 16 frontend that needs to be hosted. Options considered:

1. **Vercel** — Built for Next.js, but Hobby plan prohibits commercial use. Pro costs $20/month.
2. **Netlify** — Good free tier, but less Next.js optimization.
3. **Cloudflare Pages** — Free tier allows commercial use, unlimited bandwidth, edge CDN.

## Decision

Use **Cloudflare Pages** (free tier) with the **OpenNext adapter** to deploy Next.js 16 as Cloudflare Workers.

### Why Cloudflare Pages

| Factor | Cloudflare Pages | Vercel Pro | Netlify |
|--------|-----------------|-----------|---------|
| Cost | $0 (free tier) | $20/month | $0 (free tier) |
| Commercial use | Allowed | Allowed (Pro only) | Allowed |
| Bandwidth | Unlimited | 1TB | 100GB |
| Build minutes | 500/month | 6000/month | 300/month |
| Worker bundle | 3 MiB (free), 10 MiB ($5/mo) | N/A | N/A |
| Edge CDN | Global | Global | Global |
| Next.js support | Via OpenNext adapter | Native | Via adapter |

### Constraints

- Worker bundle must be < 3 MiB on free tier
- 100K function requests/day (~3M/month)
- OpenNext adapter required for App Router, SSR, Server Actions, ISR

**Upgrade trigger:** If bundle exceeds 3 MiB, upgrade to Workers Paid ($5/month).

## Consequences

### Positive
- **$0 hosting cost** with unlimited bandwidth
- **Commercial use allowed** on free tier
- **Global edge CDN** for low TTFB
- **ISR support** via Cloudflare Cache API (OpenNext translates `revalidate` exports)

### Negative
- **OpenNext dependency:** Beta adapter, potential compatibility issues with new Next.js features
- **3 MiB bundle limit:** Requires careful bundle optimization (dynamic imports, tree-shaking)
- **Less Next.js-native** than Vercel (no Vercel-specific optimizations)
- **Fallback required:** If OpenNext breaks, need to switch to Netlify

### Fallback Plan
If Cloudflare Pages has issues: deploy to Netlify Free (`netlify deploy`), update DNS CNAME. Estimated switchover: < 1 hour.

## References
- Phase 3 SPEC §2.3 (Cloudflare Pages deployment details)
- `web/wrangler.toml` (Cloudflare configuration)
- `web/open-next.config.ts` (OpenNext adapter config)
- `.github/workflows/phase3-deploy-cf.yml` (CI/CD)
- `docs/workflows/deployment.md` (Deployment guide)
