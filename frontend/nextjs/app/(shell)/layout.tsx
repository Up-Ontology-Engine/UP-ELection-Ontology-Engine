import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex grid-bg">
      <Sidebar />
      <div className="flex-1 ml-56 flex flex-col min-h-screen relative z-[1]">
        <Header />
        <main className="flex-1 pt-14 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
