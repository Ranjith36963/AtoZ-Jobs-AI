const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://atozjobs.ai";

export function GET() {
  const body = `User-agent: *
Allow: /
Disallow: /api/
Disallow: /profile/

Sitemap: ${SITE_URL}/sitemap.xml
`;

  return new Response(body, {
    headers: {
      "Content-Type": "text/plain",
      "Cache-Control": "public, max-age=86400, s-maxage=86400",
    },
  });
}
