import Link from "next/link";

export function Footer() {
  return (
    <footer
      className="border-t border-gray-200 bg-gray-50"
      role="contentinfo"
    >
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <ul className="flex gap-6 text-sm text-gray-600" role="list">
            <li>
              <Link href="/transparency" className="hover:text-gray-900">
                Transparency
              </Link>
            </li>
            <li>
              <Link href="/transparency#accessibility" className="hover:text-gray-900">
                Accessibility
              </Link>
            </li>
          </ul>
          <p className="text-sm text-gray-500">
            Results ranked by AI.{" "}
            <Link href="/transparency" className="underline hover:text-gray-700">
              Learn how
            </Link>
            .
          </p>
        </div>
      </div>
    </footer>
  );
}
