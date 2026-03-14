import Link from "next/link";

const FEATURED_CATEGORIES = [
  { name: "Technology", slug: "technology", count: null },
  { name: "Healthcare", slug: "healthcare", count: null },
  { name: "Finance", slug: "finance", count: null },
  { name: "Education", slug: "education", count: null },
  { name: "Engineering", slug: "engineering", count: null },
  { name: "Marketing", slug: "marketing", count: null },
] as const;

export function HomePage() {
  return (
    <main id="main-content" className="flex-1">
      {/* Hero section */}
      <section className="bg-gradient-to-b from-blue-50 to-white px-4 py-16 sm:py-24">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            Find your next role
          </h1>
          <p className="mt-4 text-lg text-gray-600">
            AI-powered UK job search with semantic matching, skill analysis, and
            salary insights.
          </p>
          <div className="mt-8">
            <Link
              href="/search"
              className="inline-flex items-center rounded-lg bg-blue-600 px-6 py-3 text-base font-medium text-white shadow-sm hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              Start searching
            </Link>
          </div>
        </div>
      </section>

      {/* Featured categories */}
      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <h2 className="text-2xl font-bold text-gray-900">
          Browse by category
        </h2>
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {FEATURED_CATEGORIES.map((cat) => (
            <Link
              key={cat.slug}
              href={`/search?category=${cat.slug}`}
              className="rounded-lg border border-gray-200 p-4 text-center hover:border-blue-300 hover:bg-blue-50 transition-colors"
            >
              <span className="text-sm font-medium text-gray-900">
                {cat.name}
              </span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}

export { HomePage as default };
