import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import { Sidebar } from "../components/Sidebar";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const serif = Source_Serif_4({ variable: "--font-serif-display", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Handover",
  description: "Exit interviews that become knowledge the next person can ask.",
};

// Apply the stored (or system) theme before first paint.
const THEME_SCRIPT = `try{var t=localStorage.getItem("handover_theme");if(t!=="light"&&t!=="dark")t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme="light"}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${serif.variable} antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="font-sans">
        <div className="flex h-dvh overflow-hidden">
          <Sidebar />
          <main className="relative min-w-0 flex-1 overflow-hidden">{children}</main>
        </div>
      </body>
    </html>
  );
}
