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
    skills: z.array(z.string()).optional(),
    salary_annual_min: z.number().nullable().optional(),
    salary_annual_max: z.number().nullable().optional(),
  }),
  profile: z.string().optional(),
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

  const { query, job, profile } = parsed.data;

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

  // SPEC §6.1 exact prompt
  const salaryStr = job.salary_annual_min
    ? `£${job.salary_annual_min}–£${job.salary_annual_max}`
    : "Not disclosed";

  const prompt = `You are a UK careers advisor. Explain in 2-3 sentences why this job matches the user's search.

User searched for: "${query}"
${profile ? `User profile: ${profile}` : ""}

Job: ${job.title} at ${job.company_name}
Location: ${job.location_city || "Not specified"}
Skills required: ${job.skills?.join(", ") || "Not specified"}
Salary: ${salaryStr}

Be specific about skill matches and location relevance. Be honest about gaps. Keep it under 50 words.`;

  const result = streamText({
    model: openai("gpt-4o-mini"),
    prompt,
    maxOutputTokens: 100,
    temperature: 0.3,
  });

  // Fire-and-forget audit log (captures token_count after stream completes)
  Promise.resolve(result.usage)
    .then((usage) => logExplanationAudit(query, job.id, usage))
    .catch(() => {
      /* swallow */
    });

  return result.toTextStreamResponse();
}

async function logExplanationAudit(
  query: string,
  jobId: number,
  usage?: { inputTokens?: number; outputTokens?: number } | null,
): Promise<void> {
  try {
    const admin = createAdminClient();
    const tokenCount = usage
      ? (usage.inputTokens ?? 0) + (usage.outputTokens ?? 0)
      : null;
    const insertData = {
      decision_type: "match_explanation",
      model_provider: "openai",
      model_version: "gpt-4o-mini",
      input_hash: createHash("sha256").update(query).digest("hex"),
      input_summary: `query: ${query}, job_id: ${jobId}`,
      output_summary: "streamed explanation",
      job_id: jobId,
      cost_usd: 0.0005, // Approximate cost per explanation
      token_count: tokenCount,
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
