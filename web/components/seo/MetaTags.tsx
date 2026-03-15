import type { Metadata } from "next";

interface MetaTagsInput {
  title: string;
  description: string;
  path: string;
  image?: string;
}

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://atozjobs.ai";

export function generatePageMetadata({ title, description, path, image }: MetaTagsInput): Metadata {
  const url = `${SITE_URL}${path}`;

  return {
    title: `${title} | AtoZ Jobs`,
    description,
    openGraph: {
      title,
      description,
      url,
      siteName: "AtoZ Jobs AI",
      type: "website",
      ...(image ? { images: [{ url: image }] } : {}),
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
    alternates: {
      canonical: url,
    },
  };
}
