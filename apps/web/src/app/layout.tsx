import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Worktreee",
  description: "Worktreee - 업무나무우",
  manifest: "/manifest.json",
  themeColor: "#13161b",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Worktreee",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="dark">
      <head>
        <link rel="apple-touch-icon" href="/icon-192.png" />
      </head>
      <body className="min-h-screen antialiased">
        <script
          dangerouslySetInnerHTML={{
            __html: `if("serviceWorker"in navigator)navigator.serviceWorker.register("/sw.js")`,
          }}
        />
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
