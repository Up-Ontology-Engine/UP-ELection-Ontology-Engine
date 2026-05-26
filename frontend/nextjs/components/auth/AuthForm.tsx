"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/landing/Logo";
import { useRouter } from "next/navigation";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      router.push("/dashboard");
    }, 800);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <div className="px-6 py-5">
        <Link href="/"><Logo size="sm" /></Link>
      </div>
      <div className="flex-1 flex items-center justify-center px-6 pb-16">
        <div className="w-full max-w-md rounded-2xl border border-(--border-bright) bg-card p-8 shadow-[0_10px_40px_-20px_rgba(0,0,0,0.15)]">
          <div className="text-xs font-mono tracking-widest text-(--saffron)">
            {mode === "login" ? "WELCOME BACK" : "GET STARTED"}
          </div>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">
            {mode === "login" ? "Sign in to your account" : "Create your account"}
          </h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {mode === "login" ? "Continue your constituency analysis." : "Start mapping your electorate today."}
          </p>

          <Button type="button" variant="outline" className="mt-6 w-full rounded-lg gap-2 border-(--border-bright) text-(--saffron-dim) hover:bg-(--saffron-subtle)" onClick={() => {
            setLoading(true);
            setTimeout(() => {
              setLoading(false);
              router.push("/dashboard");
            }, 600);
          }} disabled={loading}>
            <GoogleIcon /> Continue with Google
          </Button>

          <div className="my-6 flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
            <div className="h-px flex-1 bg-border" /> OR <div className="h-px flex-1 bg-border" />
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1.5" />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" required minLength={6} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1.5" />
            </div>
            <Button type="submit" className="w-full rounded-lg bg-(--saffron) text-white hover:bg-(--saffron-dim)" disabled={loading}>
              {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            {mode === "login" ? (
              <>New here? <Link href="/signup" className="text-(--saffron) hover:underline">Create an account</Link></>
            ) : (
              <>Already have an account? <Link href="/login" className="text-(--saffron) hover:underline">Sign in</Link></>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.4 29.3 35.5 24 35.5c-6.4 0-11.5-5.1-11.5-11.5S17.6 12.5 24 12.5c2.9 0 5.6 1.1 7.6 2.9l5.7-5.7C33.7 6.3 29.1 4.5 24 4.5 13.2 4.5 4.5 13.2 4.5 24S13.2 43.5 24 43.5c10.8 0 19.5-8.7 19.5-19.5 0-1.2-.1-2.3-.4-3.5z"/>
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16 19 12.5 24 12.5c2.9 0 5.6 1.1 7.6 2.9l5.7-5.7C33.7 6.3 29.1 4.5 24 4.5 16.3 4.5 9.7 8.9 6.3 14.7z"/>
      <path fill="#4CAF50" d="M24 43.5c5 0 9.5-1.7 13-4.6l-6-5.1c-1.9 1.3-4.3 2.1-7 2.1-5.3 0-9.7-3.1-11.3-7.5l-6.5 5C9.6 39.5 16.2 43.5 24 43.5z"/>
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4 5.3l6 5.1c4.2-3.9 6.7-9.6 6.7-16.4 0-1.2-.1-2.3-.4-3.5z"/>
    </svg>
  );
}
