import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Syllabot",
  description: "Turn a course syllabus into a chatbot your students can ask.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
