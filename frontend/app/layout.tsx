import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import { LogCapture } from "../components/LogCapture";
import { AsciiBackdrop } from "../components/AsciiBackdrop";
import { RoleMenu } from "../components/RoleMenu";
import { Sidebar } from "../components/Sidebar";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const serif = Source_Serif_4({ variable: "--font-serif-display", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Handover · Northgate Bank",
  description: "Hand over how you run the bank's money. Whoever takes your desk can ask it.",
};

// Apply the stored (or system) theme before first paint.
const THEME_SCRIPT = `try{var t=localStorage.getItem("handover_theme");if(t!=="light"&&t!=="dark")t="dark";document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme="light"}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${serif.variable} antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="font-sans">
        <LogCapture />
        <AsciiBackdrop />
        <RoleMenu />
        <div className="relative flex h-dvh overflow-hidden">
          <Sidebar />
          <main className="relative min-w-0 flex-1 overflow-hidden">{children}</main>
        </div>
      </body>
    </html>
  );
}
