import type { Metadata } from "next";
import { Noto_Sans, Noto_Sans_Devanagari, Geist_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import GovBanner from "@/components/GovBanner";
import GovHeader from "@/components/GovHeader";
import GovFooter from "@/components/GovFooter";

const notoSans = Noto_Sans({
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-noto-sans",
  display: "swap",
});

const notoDevanagari = Noto_Sans_Devanagari({
  weight: ["400", "500", "600", "700"],
  subsets: ["devanagari"],
  variable: "--font-noto-devanagari",
  display: "swap",
});

const geistMono = Geist_Mono({
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Booth-Level Political Intelligence | Gorakhpur Urban AC-322",
  description: "Data-backed booth intelligence for Gorakhpur Urban AC-322",
};

// Anti-flash: defaults to light for new visitors
const ANTI_FLASH = `(function(){try{var t=localStorage.getItem('theme')||'light';document.documentElement.setAttribute('data-theme',t);}catch(e){}})()`;

// Fixed layout heights in px — kept as constants to keep positioning consistent
const BANNER_H  = 36;   // GovBanner
const GOV_HDR_H = 80;   // GovHeader
const TOP_OFFSET = BANNER_H + GOV_HDR_H;  // 116px — sidebar & breadcrumb top
const SIDEBAR_W  = 224; // px (w-56 = 14rem at 16px base)
const BREADCRUMB_H = 44; // Header breadcrumb bar

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${notoSans.variable} ${notoDevanagari.variable} ${geistMono.variable} h-full`}
    >
      <body className="min-h-full flex flex-col" style={{ background: "var(--bg-base)" }}>
        <Script id="theme-init" strategy="beforeInteractive">{ANTI_FLASH}</Script>
        <ThemeProvider>
          {/* ── Fixed government headers ── */}
          <GovBanner />
          <GovHeader />

          {/* ── Fixed sidebar (below gov headers) ── */}
          <Sidebar />

          {/* ── Main area: right of sidebar, below gov headers ── */}
          <div
            style={{
              marginTop: TOP_OFFSET,
              marginLeft: SIDEBAR_W,
              display: "flex",
              flexDirection: "column",
              minHeight: `calc(100vh - ${TOP_OFFSET}px)`,
            }}
          >
            {/* Breadcrumb / page-level nav bar */}
            <Header topOffset={TOP_OFFSET} sidebarWidth={SIDEBAR_W} />

            {/* Page content */}
            <main
              id="main-content"
              tabIndex={-1}
              style={{ flex: 1, paddingTop: BREADCRUMB_H, outline: "none" }}
            >
              {children}
            </main>

            {/* Official footer */}
            <GovFooter />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
