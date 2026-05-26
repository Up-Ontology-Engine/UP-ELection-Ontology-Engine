import { Nav } from "@/components/landing/Nav";
import { Hero } from "@/components/landing/Hero";
import { Features } from "@/components/landing/Features";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Insights } from "@/components/landing/Insights";
import { CtaBand } from "@/components/landing/CtaBand";
import { Footer } from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-(--bg-base)">
      <Nav />
      <Hero />
      <Features />
      <HowItWorks />
      <Insights />
      <CtaBand />
      <Footer />
    </div>
  );
}
