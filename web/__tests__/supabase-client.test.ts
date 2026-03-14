import { describe, it, expect, vi, beforeAll } from "vitest";

// Set env vars before any imports
beforeAll(() => {
  process.env.NEXT_PUBLIC_SUPABASE_URL = "https://test.supabase.co";
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-anon-key";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "test-service-role-key";
});

// Mock next/headers for server client
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve({
      getAll: () => [],
      set: vi.fn(),
    }),
  ),
}));

describe("Supabase clients", () => {
  it("browser client creates without error", async () => {
    const { createClient } = await import("@/lib/supabase/browser");
    const client = createClient();
    expect(client).toBeDefined();
    expect(client.from).toBeDefined();
  });

  it("server client creates without error", async () => {
    const { createClient } = await import("@/lib/supabase/server");
    const client = await createClient();
    expect(client).toBeDefined();
    expect(client.from).toBeDefined();
  });

  it("admin client throws without service role key", async () => {
    const original = process.env.SUPABASE_SERVICE_ROLE_KEY;
    delete process.env.SUPABASE_SERVICE_ROLE_KEY;

    // Dynamic import to avoid module caching issues
    const { createAdminClient } = await import("@/lib/supabase/admin");
    expect(() => createAdminClient()).toThrow(
      "Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY",
    );

    process.env.SUPABASE_SERVICE_ROLE_KEY = original;
  });

  it("admin client creates with service role key", async () => {
    process.env.SUPABASE_SERVICE_ROLE_KEY = "test-service-role-key";
    const { createAdminClient } = await import("@/lib/supabase/admin");
    const client = createAdminClient();
    expect(client).toBeDefined();
    expect(client.from).toBeDefined();
  });
});
