import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "PM Agent",
  description: "Project Manager Agent Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="dark">
      <body className="min-h-screen antialiased">
        <nav className="bg-gray-900 border-b border-gray-800">
          <div className="max-w-7xl mx-auto px-4 py-3 flex gap-4">
            <Link
              href="/projects"
              className="text-gray-300 hover:text-white transition font-medium"
            >
              Projects
            </Link>
            <Link
              href="/graphs"
              className="text-gray-300 hover:text-white transition font-medium"
            >
              Graphs
            </Link>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
