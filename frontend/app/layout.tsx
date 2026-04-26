import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Web Scraper — n8n",
  description:
    "Extract structured data from any website using natural language field definitions.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-bg text-text font-sans min-h-screen flex flex-col items-center px-5 py-10 pb-20">
        {children}
      </body>
    </html>
  );
}
