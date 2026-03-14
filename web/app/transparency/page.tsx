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

      {/* Section 1: AI Systems Overview */}
      <section className="mt-10" aria-labelledby="ai-systems">
        <h2 id="ai-systems" className="text-xl font-semibold text-gray-900">
          1. AI Systems We Use
        </h2>
        <div className="mt-4 space-y-4 text-sm text-gray-700">
          <p>
            Our platform employs several AI systems to improve your job search
            experience:
          </p>
          <ul className="list-disc space-y-2 pl-6">
            <li>
              <strong>Semantic Search</strong> — We use Google Gemini
              embedding-001 to convert your search queries and job descriptions
              into 768-dimensional vectors, enabling meaning-based matching
              beyond simple keyword search.
            </li>
            <li>
              <strong>Re-ranking</strong> — A cross-encoder model
              (ms-marco-MiniLM-L-6-v2) re-scores the top search results for
              query-document relevance.
            </li>
            <li>
              <strong>Match Explanations</strong> — GPT-4o-mini generates brief
              explanations of why a job matches your search query.
            </li>
            <li>
              <strong>Salary Predictions</strong> — An XGBoost model predicts
              salary ranges when employers do not disclose them, using job
              title, location, category, and seniority as features.
            </li>
            <li>
              <strong>Skill Extraction</strong> — SpaCy NLP with ESCO taxonomy
              matching identifies skills mentioned in job descriptions.
            </li>
            <li>
              <strong>Deduplication</strong> — MinHash/LSH with fuzzy matching
              detects and removes duplicate job postings across sources.
            </li>
          </ul>
        </div>
      </section>

      {/* Section 2: How AI Affects Results */}
      <section className="mt-10" aria-labelledby="how-ai-affects">
        <h2
          id="how-ai-affects"
          className="text-xl font-semibold text-gray-900"
        >
          2. How AI Affects Your Results
        </h2>
        <div className="mt-4 space-y-3 text-sm text-gray-700">
          <p>
            AI influences the order in which jobs appear in your search results.
            Our hybrid ranking combines full-text search scores, semantic
            similarity scores, and geographic relevance using Reciprocal Rank
            Fusion (RRF). The cross-encoder then re-ranks the top results.
          </p>
          <p>
            <strong>Important:</strong> AI-generated results are recommendations,
            not decisions. You always have full control over which jobs you view
            and apply to.
          </p>
        </div>
      </section>

      {/* Section 3: AI Disclosure Labels */}
      <section className="mt-10" aria-labelledby="disclosure-labels">
        <h2
          id="disclosure-labels"
          className="text-xl font-semibold text-gray-900"
        >
          3. AI Disclosure Labels
        </h2>
        <div className="mt-4 space-y-4 text-sm text-gray-700">
          <p>
            Whenever AI-generated content appears on our platform, it is clearly
            labelled. Here are the disclosure styles we use:
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

      {/* Section 4: Data Sources */}
      <section className="mt-10" aria-labelledby="data-sources">
        <h2 id="data-sources" className="text-xl font-semibold text-gray-900">
          4. Data Sources
        </h2>
        <div className="mt-4 text-sm text-gray-700">
          <p>
            Job listings are collected from multiple UK job boards including
            Reed, Adzuna, and other aggregators. Company information is enriched
            via the Companies House API. Location data uses postcodes.io for
            geocoding.
          </p>
        </div>
      </section>

      {/* Section 5: Decision Logging (Article 12) */}
      <section className="mt-10" aria-labelledby="decision-logging">
        <h2
          id="decision-logging"
          className="text-xl font-semibold text-gray-900"
        >
          5. Decision Logging
        </h2>
        <div className="mt-4 text-sm text-gray-700">
          <p>
            In accordance with EU AI Act Article 12, all AI decisions are logged
            in our audit system. This includes search rankings, match
            explanations, salary predictions, skill extractions, and
            deduplication decisions. Each log entry records the model provider,
            model version, a hash of the input, and the decision output.
          </p>
        </div>
      </section>

      {/* Section 6: Human Oversight (Article 14) */}
      <section className="mt-10" aria-labelledby="human-oversight">
        <h2
          id="human-oversight"
          className="text-xl font-semibold text-gray-900"
        >
          6. Human Oversight
        </h2>
        <div className="mt-4 text-sm text-gray-700">
          <p>
            All AI outputs on this platform are advisory. Job search results are
            recommendations — you decide which jobs to explore and apply for.
            Predicted salaries are clearly marked as estimates. Match
            explanations are labelled as AI-generated and may contain errors.
          </p>
        </div>
      </section>

      {/* Section 7: Contact */}
      <section className="mt-10" aria-labelledby="contact">
        <h2 id="contact" className="text-xl font-semibold text-gray-900">
          7. Contact & Feedback
        </h2>
        <div className="mt-4 text-sm text-gray-700">
          <p>
            If you have questions about how AI is used on AtoZ Jobs, or if you
            believe an AI-generated result is incorrect or harmful, please
            contact us. We are committed to transparent and responsible AI use.
          </p>
        </div>
      </section>

      <div className="mt-12 border-t border-gray-200 pt-6 text-xs text-gray-400">
        <p>Last updated: March 2026</p>
      </div>
    </main>
  );
}

export { TransparencyPage as default };
