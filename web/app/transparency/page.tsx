import type { Metadata } from "next";
import { AIDisclosure } from "@/components/ui/AIDisclosure";

export const revalidate = 86400; // ISR: 24 hours

export const metadata: Metadata = {
  title: "AI Transparency | AtoZ Jobs",
  description:
    "How AtoZ Jobs uses artificial intelligence in job search, matching, and recommendations. EU AI Act compliance.",
};

export function TransparencyPage() {
  return (
    <main id="main-content" className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="text-3xl font-bold text-gray-900">
        AI Transparency Statement
      </h1>
      <p className="mt-4 text-gray-600">
        AtoZ Jobs uses artificial intelligence to help you find relevant job
        opportunities. This page explains how AI is used across our platform, in
        compliance with the EU AI Act (Articles 12, 13, 14, and 50).
      </p>

      {/* Section 1: How AI Powers AtoZ Jobs */}
      <section className="mt-10" aria-labelledby="how-ai-powers">
        <h2 id="how-ai-powers" className="text-xl font-semibold text-gray-900">
          1. How AI Powers AtoZ Jobs
        </h2>
        <div className="mt-4 space-y-3 text-sm text-gray-700">
          <p>
            Our platform employs several AI systems to improve your job search
            experience. We use semantic search to understand the meaning behind
            your queries, re-ranking models to surface the most relevant results,
            machine learning to predict salary ranges when employers do not
            disclose them, and natural language processing to extract skills from
            job descriptions.
          </p>
          <p>
            Every AI-generated output on our platform is clearly labelled so you
            always know when AI is involved. Here are the disclosure styles we
            use:
          </p>
          <div className="mt-4 space-y-4 rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <AIDisclosure variant="inline" />
              <span className="text-gray-500">— Inline text label</span>
            </div>
            <div className="flex items-center gap-3">
              <AIDisclosure variant="badge" />
              <span className="text-gray-500">— Badge with icon</span>
            </div>
            <div>
              <AIDisclosure variant="section" />
              <span className="mt-2 block text-gray-500">
                — Section-level warning banner
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: Models Used */}
      <section className="mt-10" aria-labelledby="models-used">
        <h2 id="models-used" className="text-xl font-semibold text-gray-900">
          2. Models Used
        </h2>
        <div className="mt-4 text-sm text-gray-700">
          <ul className="list-disc space-y-2 pl-6">
            <li>
              <strong>Gemini embedding-001</strong> — Converts search queries
              and job descriptions into 768-dimensional vectors for semantic
              search.
            </li>
            <li>
              <strong>ms-marco-MiniLM-L-6-v2</strong> — Cross-encoder model
              that re-scores the top search results for query-document relevance.
            </li>
            <li>
              <strong>GPT-4o-mini</strong> — Generates brief explanations of
              why a job matches your search query.
            </li>
            <li>
              <strong>XGBoost</strong> — Predicts salary ranges when employers
              do not disclose them, using job title, location, category, and
              seniority as features.
            </li>
            <li>
              <strong>SpaCy NLP</strong> — Extracts skills from job
              descriptions using ESCO taxonomy matching.
            </li>
          </ul>
        </div>
      </section>

      {/* Section 3: What AI Decides */}
      <section className="mt-10" aria-labelledby="what-ai-decides">
        <h2
          id="what-ai-decides"
          className="text-xl font-semibold text-gray-900"
        >
          3. What AI Decides
        </h2>
        <div className="mt-4 space-y-3 text-sm text-gray-700">
          <p>AI is used to determine the following on our platform:</p>
          <ul className="list-disc space-y-2 pl-6">
            <li>
              <strong>Search result ordering</strong> — Our hybrid ranking
              combines full-text search scores, semantic similarity scores, and
              geographic relevance using Reciprocal Rank Fusion (RRF). The
              cross-encoder then re-ranks the top results.
            </li>
            <li>
              <strong>Match explanations</strong> — AI generates brief
              explanations of why a job matches your search query.
            </li>
            <li>
              <strong>Predicted salaries</strong> — When employers do not
              disclose salary information, our model predicts a salary range
              based on similar jobs.
            </li>
          </ul>
        </div>
      </section>

      {/* Section 4: What AI Does NOT Decide */}
      <section className="mt-10" aria-labelledby="what-ai-does-not-decide">
        <h2
          id="what-ai-does-not-decide"
          className="text-xl font-semibold text-gray-900"
        >
          4. What AI Does NOT Decide
        </h2>
        <div className="mt-4 space-y-3 text-sm text-gray-700">
          <p>
            AI on AtoZ Jobs is strictly advisory. The following decisions are
            never made by AI:
          </p>
          <ul className="list-disc space-y-2 pl-6">
            <li>
              <strong>Hiring decisions</strong> — We do not influence or
              participate in any employer&apos;s hiring process.
            </li>
            <li>
              <strong>Shortlisting</strong> — We do not shortlist or filter out
              candidates on behalf of employers.
            </li>
            <li>
              <strong>Application success</strong> — Your application outcomes
              are entirely between you and the employer.
            </li>
          </ul>
          <p>
            You always have full control over which jobs you view and apply to.
            AI results are recommendations, not decisions.
          </p>
        </div>
      </section>

      {/* Section 5: Known Limitations */}
      <section className="mt-10" aria-labelledby="known-limitations">
        <h2
          id="known-limitations"
          className="text-xl font-semibold text-gray-900"
        >
          5. Known Limitations
        </h2>
        <div className="mt-4 space-y-3 text-sm text-gray-700">
          <ul className="list-disc space-y-2 pl-6">
            <li>
              <strong>Search quality</strong> depends on the quality and
              completeness of job descriptions provided by employers. Poorly
              written descriptions may not match relevant searches.
            </li>
            <li>
              <strong>Salary predictions</strong> have a Mean Absolute Error
              (MAE) of approximately ±£5,000–£8,000. Predicted salaries are
              always clearly marked as estimates.
            </li>
            <li>
              <strong>Match explanations</strong> may occasionally be generic or
              miss specific nuances of your search intent.
            </li>
          </ul>
        </div>
      </section>

      {/* Section 6: How to Contest */}
      <section className="mt-10" aria-labelledby="how-to-contest">
        <h2
          id="how-to-contest"
          className="text-xl font-semibold text-gray-900"
        >
          6. How to Contest
        </h2>
        <div className="mt-4 text-sm text-gray-700">
          <p>
            If you believe an AI-generated result is incorrect, misleading, or
            harmful, you can contest it. Please contact us at{" "}
            <a
              href="mailto:feedback@atozjobs.ai"
              className="text-teal-600 underline hover:text-teal-700"
            >
              feedback@atozjobs.ai
            </a>{" "}
            with details of the issue. We review all feedback and use it to
            improve our systems.
          </p>
          <p className="mt-3">
            In accordance with EU AI Act Article 12, all AI decisions are logged
            in our audit system. This includes search rankings, match
            explanations, salary predictions, skill extractions, and
            deduplication decisions. Each log entry records the model provider,
            model version, a hash of the input, and the decision output.
          </p>
        </div>
      </section>

      {/* Section 7: Last Updated */}
      <section className="mt-10" aria-labelledby="last-updated">
        <h2
          id="last-updated"
          className="text-xl font-semibold text-gray-900"
        >
          7. Last Updated
        </h2>
        <div className="mt-4 text-sm text-gray-700">
          <p>This transparency statement was last updated in March 2026.</p>
        </div>
      </section>

      <div className="mt-12 border-t border-gray-200 pt-6 text-xs text-gray-400">
        <p>Last updated: March 2026</p>
      </div>
    </main>
  );
}

export { TransparencyPage as default };
