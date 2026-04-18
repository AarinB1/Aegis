import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
  axes: ["opsz", "SOFT"],
  style: ["normal", "italic"],
});

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
  weight: ["300", "400", "500", "600"],
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "AEGIS — A shield of perception for those who shield others.",
  description:
    "AI-Enhanced Guidance for Integrated Survival. An edge-deployable AI copilot that extends one combat medic's perception across dozens of casualties during Mass Casualty events.",
  metadataBase: new URL("http://localhost:3000"),
  openGraph: {
    title: "AEGIS — AI-Enhanced Guidance for Integrated Survival",
    description:
      "An edge-deployable AI copilot that extends one combat medic's perception across dozens of casualties during MASCAL events.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${plexSans.variable} ${plexMono.variable}`}
    >
      <body className="min-h-screen bg-paper text-ink antialiased">
        {children}
      </body>
    </html>
  );
}
