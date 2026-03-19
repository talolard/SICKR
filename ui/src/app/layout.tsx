import type { Metadata } from "next";
import { Geist_Mono, Noto_Serif, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";

import { CopilotKitProviders } from "./CopilotKitProviders";

const editorialSans = Plus_Jakarta_Sans({
  variable: "--font-editorial-sans",
  subsets: ["latin"],
});

const editorialSerif = Noto_Serif({
  variable: "--font-editorial-serif",
  subsets: ["latin"],
});

const mono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "The Curated Home | IKEA Studio",
  description: "Editorial IKEA workspace for room planning, product curation, and design guidance.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${editorialSans.variable} ${editorialSerif.variable} ${mono.variable} min-h-screen antialiased`}
      >
        <CopilotKitProviders>{children}</CopilotKitProviders>
      </body>
    </html>
  );
}
