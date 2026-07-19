import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RFQ Analyzer — Procurement Intelligence",
  description: "3-agent RAG-powered RFQ extraction, normalization, and comparison tool for procurement teams.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
