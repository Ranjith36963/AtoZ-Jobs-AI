import Link from "next/link";

export function NotFoundPage() {
  return (
    <main id="main-content" className="mx-auto max-w-2xl px-4 py-24 text-center">
      <h1 className="text-2xl font-bold text-gray-900">Page not found</h1>
      <p className="mt-4 text-gray-600">
        The page you are looking for does not exist or has been removed.
      </p>
      <div className="mt-8 flex justify-center gap-4">
        <Link
          href="/"
          className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          Go home
        </Link>
        <Link
          href="/search"
          className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Search jobs
        </Link>
      </div>
    </main>
  );
}

export { NotFoundPage as default };
