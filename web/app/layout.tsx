import type { Metadata } from "next";
import "./globals.css";
import { SkipLink } from "@/components/layout/SkipLink";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { TRPCProvider } from "@/lib/trpc/provider";
import { PostHogProvider } from "@/lib/posthog";

export const metadata: Metadata = {
  title: "AtoZ Jobs AI — UK Job Search",
  description:
    "AI-powered UK job search engine. Find your next role with semantic search, skill matching, and personalised recommendations.",
};

export function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en-GB">
      <body className="antialiased flex min-h-screen flex-col font-sans">
        <PostHogProvider>
          <TRPCProvider>
            <SkipLink />
            <Header />
            {children}
            <Footer />
          </TRPCProvider>
        </PostHogProvider>
      </body>
    </html>
  );
}

export { RootLayout as default };
