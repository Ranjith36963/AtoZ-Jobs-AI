import { streamText } from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import { z } from "zod";
import { isLLMBudgetExhausted } from "@/lib/llm/budget-guard";
import { createAdminClient } from "@/lib/supabase/admin";
import { createHash } from "crypto";

const requestSchema = z.object({
  query: z.string().min(1).max(500),
  job: z.object({
    id: z.number(),
    title: z.string(),
    company_name: z.string(),
    location_city: z.string().nullable(),
  }),
});

const FALLBACK_RESPONSE = JSON.stringify({
  explanation:
    "This job matches your search based on the title, required skills, and location. For detailed AI-generated explanations, please try again later.",
});

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return new Response(
      JSON.stringify({ error: "Invalid JSON body" }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    );
  }

  const parsed = requestSchema.safeParse(body);
  if (!parsed.success) {
    return new Response(
      JSON.stringify({ error: "Missing required fields", details: parsed.error.issues }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    );
  }

  const { query, job } = parsed.data;

  // Budget guard check
  try {
    const exhausted = await isLLMBudgetExhausted();
    if (exhausted) {
      return new Response(FALLBACK_RESPONSE, {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
  } catch {
    // If budget check fails, return fallback
    return new Response(FALLBACK_RESPONSE, {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Build the OpenAI client (with optional Helicone proxy)
  const baseURL = process.env.HELICONE_API_KEY
    ? "https://oai.helicone.ai/v1"
    : undefined;

  const openai = createOpenAI({
    apiKey: process.env.OPENAI_API_KEY,
    baseURL,
    headers: process.env.HELICONE_API_KEY
      ? { "Helicone-Auth": `Bearer ${process.env.HELICONE_API_KEY}` }
      : undefined,
  });

  const prompt = `You are a UK job search assistant. Given a user's search query and a job listing, explain in 2-3 sentences why this job is a good match. Be specific about matching skills, location, or requirements. Keep it concise and helpful.

User searched for: "${query}"

Job: ${job.title} at ${job.company_name}${job.location_city ? ` in ${job.location_city}` : ""}`;

  const result = streamText({
    model: openai("gpt-4o-mini"),
    prompt,
    maxOutputTokens: 100,
    temperature: 0.3,
  });

  // Fire-and-forget audit log
  logExplanationAudit(query, job.id).catch(() => {
    /* swallow */
  });

  return result.toTextStreamResponse();
}

async function logExplanationAudit(
  query: string,
  jobId: number,
): Promise<void> {
  try {
    const admin = createAdminClient();
    const insertData = {
      decision_type: "match_explanation",
      model_provider: "openai",
      model_version: "gpt-4o-mini",
      input_hash: createHash("sha256").update(query).digest("hex"),
      input_summary: `query: ${query}, job_id: ${jobId}`,
      output_summary: "streamed explanation",
      job_id: jobId,
      cost_usd: 0.0005, // Approximate cost per explanation
    };
    await (
      admin.from("ai_decision_audit_log") as unknown as {
        insert: (data: typeof insertData) => Promise<{ error: unknown }>;
      }
    ).insert(insertData);
  } catch {
    // Audit logging should never break the explanation
  }
}
