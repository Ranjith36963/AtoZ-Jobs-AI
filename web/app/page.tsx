import Link from "next/link";
import { HomeSearchBar } from "@/components/search/HomeSearchBar";

export const revalidate = 3600; // ISR: 1 hour

const FEATURED_CATEGORIES = [
  {
    name: "Technology",
    slug: "technology",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25A2.25 2.25 0 0 1 5.25 3h13.5A2.25 2.25 0 0 1 21 5.25Z" />
      </svg>
    ),
    description: "Software, data, and IT roles",
  },
  {
    name: "Healthcare",
    slug: "healthcare",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12Z" />
      </svg>
    ),
    description: "NHS, medical, and care jobs",
  },
  {
    name: "Finance",
    slug: "finance",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
      </svg>
    ),
    description: "Banking, accounting, and fintech",
  },
  {
    name: "Education",
    slug: "education",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a23.838 23.838 0 0 0-1.012 5.434c3.218.81 6.584 1.245 10.003 1.245 3.42 0 6.786-.434 10.003-1.245a23.838 23.838 0 0 0-1.012-5.434m-15.482 0A23.94 23.94 0 0 1 12 3.75a23.94 23.94 0 0 1 8.232 3.897M12 20.904v-7.539" />
      </svg>
    ),
    description: "Teaching and academic positions",
  },
  {
    name: "Engineering",
    slug: "engineering",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437 1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008Z" />
      </svg>
    ),
    description: "Civil, mechanical, and electrical",
  },
  {
    name: "Marketing",
    slug: "marketing",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 1 1 0-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 0 1-1.44-4.282m3.102.069a18.03 18.03 0 0 1-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 0 1 8.835 2.535M10.34 6.66a23.847 23.847 0 0 0 8.835-2.535m0 0A23.74 23.74 0 0 0 18.795 3m.38 1.125a23.91 23.91 0 0 1 1.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 0 0 1.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 0 1 0 3.46" />
      </svg>
    ),
    description: "Digital, brand, and content roles",
  },
] as const;

const TRUST_SIGNALS = [
  { label: "4 UK job boards", description: "Aggregated daily" },
  { label: "AI-powered matching", description: "Semantic search + skills" },
  { label: "Salary insights", description: "Real data + ML estimates" },
  { label: "100% transparent", description: "EU AI Act compliant" },
] as const;

export function HomePage() {
  return (
    <main id="main-content" className="flex-1">
      {/* Hero section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 px-4 py-20 sm:py-28">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0djJIMjR2LTJoMTJ6bTAtMzB2MkgyNFYyaDEyem0wIDMwdjJIMjR2LTJoMTJ6Ii8+PC9nPjwvZz48L3N2Zz4=')] opacity-20" />
        <div className="relative mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-6xl">
            Find your next role
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg text-blue-100">
            AI-powered UK job search with semantic matching, skill analysis, and
            salary insights.
          </p>
          <div className="mx-auto mt-8 max-w-xl">
            <HomeSearchBar />
          </div>
        </div>
      </section>

      {/* Trust signals */}
      <section className="border-b border-gray-100 bg-gray-50 px-4 py-8">
        <div className="mx-auto grid max-w-5xl grid-cols-2 gap-6 sm:grid-cols-4">
          {TRUST_SIGNALS.map((signal) => (
            <div key={signal.label} className="text-center">
              <p className="text-sm font-semibold text-gray-900">{signal.label}</p>
              <p className="mt-0.5 text-xs text-gray-500">{signal.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Featured categories */}
      <section className="bg-white px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900 sm:text-3xl">
              Browse by category
            </h2>
            <p className="mt-2 text-gray-600">
              Explore thousands of UK jobs across industries
            </p>
          </div>
          <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-3">
            {FEATURED_CATEGORIES.map((cat) => (
              <Link
                key={cat.slug}
                href={`/search?category=${cat.slug}`}
                className="group rounded-xl border border-gray-200 bg-white p-5 transition-all hover:border-blue-200 hover:shadow-lg"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-600 group-hover:text-white">
                  {cat.icon}
                </div>
                <h3 className="mt-3 font-semibold text-gray-900">
                  {cat.name}
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  {cat.description}
                </p>
              </Link>
            ))}
          </div>
          <div className="mt-8 text-center">
            <Link
              href="/search"
              className="text-sm font-medium text-blue-600 hover:text-blue-800"
            >
              View all categories &rarr;
            </Link>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="bg-gray-50 px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-2xl font-bold text-gray-900 sm:text-3xl">
            How it works
          </h2>
          <div className="mt-10 grid gap-8 sm:grid-cols-3">
            <div className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-600">
                <span className="text-lg font-bold">1</span>
              </div>
              <h3 className="mt-4 font-semibold text-gray-900">Search naturally</h3>
              <p className="mt-2 text-sm text-gray-600">
                Type what you&apos;re looking for in plain English. Our AI understands intent, not just keywords.
              </p>
            </div>
            <div className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-600">
                <span className="text-lg font-bold">2</span>
              </div>
              <h3 className="mt-4 font-semibold text-gray-900">Smart matching</h3>
              <p className="mt-2 text-sm text-gray-600">
                Semantic search + skill analysis finds relevant roles even if the job title differs.
              </p>
            </div>
            <div className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-600">
                <span className="text-lg font-bold">3</span>
              </div>
              <h3 className="mt-4 font-semibold text-gray-900">Apply with confidence</h3>
              <p className="mt-2 text-sm text-gray-600">
                See salary insights, required skills, and company info before you apply.
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

export { HomePage as default };
