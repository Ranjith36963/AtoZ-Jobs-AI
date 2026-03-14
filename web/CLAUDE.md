# AtoZ Jobs AI — Web

Next.js frontend for UK job search.

## Commands
- pnpm dev: Start dev server
- pnpm test: Run vitest
- pnpm lint: ESLint check
- pnpm typecheck: TypeScript strict check
- pnpm build: Production build

## Code Style
- TypeScript strict mode, zero `any` types
- Named exports only, never default exports
- tRPC for complex logic (search, recommendations), direct Supabase client for simple reads
- Server Actions for simple form mutations ONLY
- Zod validation at every API boundary

## Testing
- TDD: Write tests first, confirm they fail, then implement
- vitest + @testing-library/react
- Coverage: 60% minimum

## Error Handling
- Zod validation → typed error response → user-friendly message

## Security
- NEVER hardcode secrets. Always .env files (gitignored)
- Supabase RLS enforced on every table — no exceptions
- Anon key only in browser (RLS restricts to status='ready' jobs)
