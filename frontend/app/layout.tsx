import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import { Header } from "../components/Header";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const serif = Source_Serif_4({ variable: "--font-serif-display", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Handover",
  description: "Exit interviews that become governed, inheritable memory.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${serif.variable} antialiased`}>
      <body className="min-h-screen font-sans">
        <Header />
        <main className="mx-auto w-full max-w-6xl px-4 pb-16 pt-8 sm:px-6">{children}</main>
      </body>
    </html>
  );
}
