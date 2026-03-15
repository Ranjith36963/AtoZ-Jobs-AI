import Link from "next/link";

export function Footer() {
  return (
    <footer
      className="border-t border-gray-200 bg-white"
      role="contentinfo"
    >
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
          {/* Brand */}
          <div>
            <Link href="/" className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 text-xs font-bold text-white">
                Az
              </span>
              AtoZ Jobs
            </Link>
            <p className="mt-2 max-w-xs text-sm text-gray-500">
              AI-powered UK job search engine. Results ranked by AI.
            </p>
          </div>

          {/* Links */}
          <div className="flex gap-12">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Product</h3>
              <ul className="mt-3 space-y-2" role="list">
                <li>
                  <Link href="/search" className="text-sm text-gray-500 hover:text-gray-700">
                    Search jobs
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Legal</h3>
              <ul className="mt-3 space-y-2" role="list">
                <li>
                  <Link href="/transparency" className="text-sm text-gray-500 hover:text-gray-700">
                    AI Transparency
                  </Link>
                </li>
                <li>
                  <Link href="/transparency#accessibility" className="text-sm text-gray-500 hover:text-gray-700">
                    Accessibility
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-gray-100 pt-6">
          <p className="text-center text-xs text-gray-400">
            Results ranked by AI.{" "}
            <Link href="/transparency" className="underline hover:text-gray-600">
              Learn how
            </Link>
            . &copy; {new Date().getFullYear()} AtoZ Jobs.
          </p>
        </div>
      </div>
    </footer>
  );
}
