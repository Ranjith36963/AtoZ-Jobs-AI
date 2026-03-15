import { createClient } from "@/lib/supabase/server";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://atozjobs.ai";

export async function GET() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("jobs")
    .select("id, date_posted")
    .eq("status", "ready")
    .or("is_duplicate.is.null,is_duplicate.eq.false")
    .order("date_posted", { ascending: false })
    .limit(10000);

  const jobs = (data ?? []) as Array<{ id: number; date_posted: string }>;

  const staticPages = [
    { loc: "/", lastmod: new Date().toISOString().split("T")[0], priority: "1.0", changefreq: "daily" },
    { loc: "/search", lastmod: new Date().toISOString().split("T")[0], priority: "0.9", changefreq: "daily" },
    { loc: "/transparency", lastmod: "2026-03-01", priority: "0.5", changefreq: "monthly" },
  ];

  const jobPages = jobs.map((job) => ({
    loc: `/jobs/${job.id}`,
    lastmod: job.date_posted.split("T")[0],
    priority: "0.7",
    changefreq: "weekly",
  }));

  const urls = [...staticPages, ...jobPages];

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(
    (u) => `  <url>
    <loc>${SITE_URL}${u.loc}</loc>
    <lastmod>${u.lastmod}</lastmod>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`,
  )
  .join("\n")}
</urlset>`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/xml",
      "Cache-Control": "public, max-age=3600, s-maxage=3600",
    },
  });
}
