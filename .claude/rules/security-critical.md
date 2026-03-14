# Security Critical Rules

These rules are non-negotiable. Violations must be fixed before commit.

1. **No hardcoded secrets.** Always use .env files (gitignored). Never commit API keys, tokens, or passwords.
2. **Supabase RLS enforced on every table.** No exceptions. Anon key is browser-safe only because RLS restricts access.
3. **Service role key is server-only.** Never expose SUPABASE_SERVICE_ROLE_KEY to browser or frontend code.
4. **Parameterized queries only.** All SQL queries use parameterized statements (Supabase client handles this). No string concatenation in queries.
5. **OWASP Top 10 review** after writing any auth, input handling, or data processing code.
6. **Input validation at boundaries.** Zod (TypeScript) or Pydantic (Python) at every external input point.
7. **No raw HTML rendering** of user input or API response data without sanitization.
8. **Rate limiting** on all public-facing endpoints to prevent abuse.
