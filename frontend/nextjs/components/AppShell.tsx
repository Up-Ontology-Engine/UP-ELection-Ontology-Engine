"use client";

import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";

const MARKETING_ROUTES = new Set(["/", "/landing", "/login", "/signup"]);

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isMarketing = MARKETING_ROUTES.has(pathname);

  if (isMarketing) return <>{children}</>;

  return (
    <>
      <Sidebar />
      <div className="flex-1 ml-56 flex flex-col min-h-screen relative z-10">
        <Header />
        <main className="flex-1 pt-14 overflow-auto">{children}</main>
      </div>
    </>
  );
}
