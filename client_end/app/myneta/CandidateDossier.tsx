"use client";

import { useEffect } from "react";
import {
  X, ExternalLink, User, GraduationCap, MapPin, Milestone, Vote,
  AtSign, Megaphone, Briefcase, Wallet, Landmark, Scale, Sparkles,
  ShieldCheck, AlertTriangle, FileText,
} from "lucide-react";

// ── Curated intel layer ───────────────────────────────────────────────────────
// MyNeta gives us affidavit data (assets, education, criminal, income); the
// extended profile (DOB, social media, controversies, vote metrics, summary) is
// hand-verified per candidate. Keyed by candidate_id; missing entries fall back
// to "—" so the dossier renders honestly for every neta.

interface Curated {
  fullName?: string; alias?: string; dob?: string; placeOfBirth?: string;
  father?: string; mother?: string; spouse?: string; spouseProfession?: string;
  degree?: string; institution?: string; educationDetail?: string;
  currentSeat?: string; demographics?: string; pastSeats?: string;
  currentRole?: string; joinDate?: string; partySwitches?: string;
  election?: string; votes?: string; margin?: string; voteShare?: string;
  twitter?: string; twitterFollowers?: string; facebook?: string; socialNote?: string;
  policyStance?: string; policyContext?: string; controversy?: string; controversyVerdict?: string;
  career?: string; selfIncome?: string; spouseIncome?: string;
  netWorth?: string; movable?: string; vehicle?: string; immovable?: string; immovableDetail?: string;
  debt?: string; creditors?: string; legalSummary?: string;
  viralFame?: string; awards?: string; philanthropy?: string; publicPerception?: string; localIssues?: string;
  execStanding?: string; execFinancial?: string; execLegal?: string; execInternet?: string;
  sources?: Record<string, string>;
}

const CURATED: Record<string, Curated> = {
  ADITYANATH_2022: {
    fullName: "Ajay Mohan Singh Bisht",
    alias: "Yogi Adityanath",
    dob: "05 Jun 1972",
    placeOfBirth: "Panchur, Pauri Garhwal (now Uttarakhand)",
    father: "Anand Singh Bisht (Late) / Late Avedyanath (spiritual guru)",
    mother: "Savitri Devi",
    spouse: "NA",
    degree: "B.Sc.",
    institution: "H. N. Bahuguna University, Shrinagar Paurigarhwal (1992)",
    educationDetail: "Graduated with a Bachelor's degree in Science in 1992.",
    currentSeat: "Gorakhpur Urban (Uttar Pradesh)",
    demographics: "Flat alluvial plains, flood-vulnerable; 464,077 total voters in Gorakhpur Urban.",
    pastSeats: "Gorakhpur (Lok Sabha — 1998, 1999, 2004, 2009, 2014)",
    currentRole: "Chief Minister of Uttar Pradesh",
    joinDate: "1998 (first term as MP)",
    election: "2022 · Gorakhpur Urban · Won",
    votes: "165,499", margin: "103,390", voteShare: "66.18%",
    twitter: "@myogiadityanath", twitterFollowers: "25,000,000+",
    socialNote: "Surpassed 25 million followers on X (Twitter) in June 2023.",
    policyStance: "Strict law & order enforcement and state development.",
    policyContext: "Popularity rose on major law-and-order changes.",
    controversy: "Past charges incl. rioting (IPC 147) & criminal intimidation (IPC 506); declared 3 cases in 2014, 0 in 2022.",
    controversyVerdict: "True",
    career: "Hindu Monk / Salary & allowances as a People's Representative.",
    selfIncome: "₹13,20,653 (FY 2020-21)",
    netWorth: "₹1,54,94,054",
    movable: "₹1,54,94,054",
    vehicle: "Nil in his name (2022); previously a Toyota Fortuner & Innova.",
    immovable: "₹0",
    immovableDetail: "No agricultural or non-agricultural property.",
    debt: "₹0",
    legalSummary: "0 pending cases (2022).",
    viralFame: "Crossed 25 million followers on Twitter.",
    publicPerception: "Strong regional dominance; 66.18% vote share in 2022.",
    localIssues: "Frequent flooding affecting health & livelihoods.",
    execStanding: "Chief Minister of UP, elected from Gorakhpur Urban with an overwhelming majority.",
    execFinancial: "Debt-free; declared assets over ₹1.54 crore, largely movable.",
    execLegal: "Zero pending criminal cases declared in the 2022 affidavit.",
    execInternet: "Massive social presence — 25M+ followers on X.",
    sources: {
      bio: "https://en.wikipedia.org/wiki/Yogi_Adityanath",
      myneta: "https://www.myneta.info/uttarpradesh2022/candidate.php?candidate_id=3801",
      election: "https://en.wikipedia.org/wiki/Gorakhpur_Urban_Assembly_constituency",
      social: "https://ddnews.gov.in/en/yogis-twitter-following-surpasses-25-million-mark/",
    },
  },
};

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmtRs(n: number | null | undefined): string {
  if (!n || n <= 0) return "₹0";
  return "₹" + Math.round(n).toLocaleString("en-IN");
}

const DASH = "—";

export default function CandidateDossier({ node, onClose }: {
  node: { id: string; label: string; properties: Record<string, unknown> };
  onClose: () => void;
}) {
  const p = node.properties;
  const aff = (p.affidavit as Record<string, unknown>) ?? {};
  const cid = p.candidate_id as string;
  const cur = CURATED[cid] ?? {};

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const name = (p.name as string) ?? node.label;
  const party = (p.party as string) ?? "IND";
  const criminal = (p.criminal_cases as number) ?? 0;
  const itr = (aff.itr_income as { relation: string; year: string; total_income_rs: number }[]) ?? [];
  const liabilities = (aff.liabilities as { item: string; total_rs: number }[]) ?? [];
  const crimDetail = (aff.criminal_cases_detail as Record<string, string>[]) ?? [];
  const selfItr = itr.filter((r) => (r.relation || "").includes("self")).sort((a, b) => b.year.localeCompare(a.year))[0];
  const sourceUrl = (aff.source_url as string) ?? (p.detail_url as string);

  const S = {
    card: "var(--bg-card)", surface: "var(--bg-surface)", border: "var(--border)",
    t1: "var(--text-1)", t2: "var(--text-2)", t3: "var(--text-3)", t4: "var(--text-4)",
    saffron: "var(--saffron)",
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center p-4 md:p-8 overflow-y-auto"
      style={{ background: "rgba(20,14,6,0.55)", backdropFilter: "blur(3px)" }}
      onClick={onClose}>
      <div className="w-full max-w-3xl rounded-xl my-4"
        style={{ background: S.card, border: `1px solid ${S.border}`, boxShadow: "var(--shadow-lg)" }}
        onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div className="sticky top-0 z-10 px-5 py-4 flex items-start justify-between rounded-t-xl"
          style={{ background: S.card, borderBottom: `1px solid ${S.border}` }}>
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-11 h-11 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0"
              style={{ background: S.saffron, color: "#fff" }}>{party.slice(0, 3)}</div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base font-bold" style={{ color: S.t1 }}>{cur.fullName ?? name}</h2>
                {cur.alias && <span className="text-xs" style={{ color: S.t3 }}>({cur.alias})</span>}
                {p.winner ? (
                  <span className="pill" style={{ borderColor: "rgba(16,185,129,0.3)", background: "rgba(16,185,129,0.1)", color: "var(--green)" }}>
                    <ShieldCheck size={10} /> Won
                  </span>
                ) : null}
              </div>
              <p className="text-xs mt-0.5" style={{ color: S.t3 }}>
                {party} · {p.ac_name as string} · {p.election_year as number}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-md flex-shrink-0"
            style={{ color: S.t3 }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4">

          <Section icon={User} title="1 · Personal Vitals" S={S}>
            <Field label="Full Legal Name" value={cur.fullName ?? name} context={cur.alias ? `Alias: ${cur.alias}` : undefined} verdict={cur.fullName ? "Verified" : undefined} S={S} />
            <Field label="Date of Birth" value={cur.dob ?? DASH} S={S} />
            <Field label="Place of Birth" value={cur.placeOfBirth ?? DASH} S={S} />
          </Section>

          <Section icon={GraduationCap} title="2 · Family & Education" S={S}>
            <Field label="Father" value={cur.father ?? DASH} S={S} />
            <Field label="Mother" value={cur.mother ?? DASH} S={S} />
            <Field label="Spouse" value={cur.spouse ?? (aff.spouse_name as string) ?? DASH} S={S} />
            <Field label="Highest Degree" value={cur.degree ?? (p.education as string) ?? DASH}
              context={cur.institution ?? (aff.education_detail as string)} verdict={cur.degree ? "Verified" : undefined} S={S} />
          </Section>

          <Section icon={MapPin} title="3 · Constituency Data" S={S}>
            <Field label="Current Seat" value={cur.currentSeat ?? `${p.ac_name as string} (Uttar Pradesh)`} S={S} />
            <Field label="Demographics" value={cur.demographics ?? DASH} S={S} />
            <Field label="Past Seats" value={cur.pastSeats ?? DASH} S={S} />
          </Section>

          <Section icon={Milestone} title="4 · Political Trajectory" S={S}>
            <Field label="Current Role" value={cur.currentRole ?? DASH} S={S} />
            <Field label="Join Date" value={cur.joinDate ?? DASH} S={S} />
            <Field label="Party Switches" value={cur.partySwitches ?? DASH} S={S} />
          </Section>

          <Section icon={Vote} title="5 · Electoral Record" S={S}>
            <Field label={`${p.election_year as number} Election`} value={cur.election ?? `${p.ac_name as string} · ${p.winner ? "Won" : "Contested"}`} S={S} />
            {(cur.votes || cur.margin) && (
              <Field label="Metrics" value={`${cur.votes ?? DASH} votes · margin ${cur.margin ?? DASH}${cur.voteShare ? ` · ${cur.voteShare} share` : ""}`} S={S} />
            )}
          </Section>

          <Section icon={AtSign} title="6 · Social Media Audit" S={S}>
            <Field label="X (Twitter)" value={cur.twitter ?? DASH}
              context={cur.twitterFollowers ? `${cur.twitterFollowers} followers` : undefined} S={S} />
            <Field label="Facebook" value={cur.facebook ?? DASH} S={S} />
            <Field label="Notable" value={cur.socialNote ?? DASH} S={S} />
          </Section>

          <Section icon={Megaphone} title="7 · Public Presence & Policy" S={S}>
            <Field label="Key Policy Stance" value={cur.policyStance ?? DASH} context={cur.policyContext} S={S} />
            <Field label="Controversies (Fact-Check)" value={cur.controversy ?? (criminal > 0 ? `${criminal} criminal case(s) declared in affidavit.` : "No criminal cases declared.")}
              verdict={cur.controversyVerdict} S={S} />
          </Section>

          <Section icon={Briefcase} title="8 · Professional History" S={S}>
            <Field label="Non-Political Career" value={cur.career ?? (aff.self_profession as string) ?? (p.profession as string) ?? DASH} S={S} />
          </Section>

          <Section icon={Wallet} title="9 · Income Profile" S={S}>
            <Field label="Self Income (ITR)" value={cur.selfIncome ?? (selfItr ? `${fmtRs(selfItr.total_income_rs)} (${selfItr.year})` : DASH)} S={S} />
            <Field label="Spouse Income" value={cur.spouseIncome ?? DASH} S={S} />
            {itr.length > 0 && (
              <div className="mt-1 rounded-md p-2.5" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                <p className="text-xs mb-1" style={{ color: S.t4, fontSize: 10 }}>ITR HISTORY</p>
                <div className="space-y-0.5">
                  {itr.slice(0, 6).map((r, i) => (
                    <div key={i} className="flex justify-between text-xs">
                      <span style={{ color: S.t3 }}>{r.relation} · {r.year}</span>
                      <span className="mono tabular-nums" style={{ color: S.t2 }}>{fmtRs(r.total_income_rs)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>

          <Section icon={Landmark} title="10 · Asset Portfolio" S={S}>
            <Field label="Net Worth" value={cur.netWorth ?? fmtRs(p.assets_rs as number)} S={S} />
            <Field label="Movable Assets" value={cur.movable ?? fmtRs(aff.movable_assets_rs as number)} context={cur.vehicle} S={S} />
            <Field label="Immovable Assets" value={cur.immovable ?? fmtRs(aff.immovable_assets_rs as number)} context={cur.immovableDetail} S={S} />
          </Section>

          <Section icon={Scale} title="11 · Liabilities & Legal History" S={S}>
            <Field label="Total Debt" value={cur.debt ?? fmtRs(p.liabilities_rs as number)} S={S} />
            <Field label="Legal Summary" value={cur.legalSummary ?? `${criminal} pending case(s) declared.`} S={S} />
            {crimDetail.length > 0 && (
              <div className="mt-1 rounded-md p-2.5" style={{ background: "rgba(220,38,38,0.05)", border: "1px solid rgba(220,38,38,0.2)" }}>
                <div className="flex items-center gap-1.5 mb-1">
                  <AlertTriangle size={11} style={{ color: "#dc2626" }} />
                  <p className="text-xs font-semibold" style={{ color: "#dc2626" }}>Declared Cases</p>
                </div>
                {crimDetail.slice(0, 4).map((c, i) => (
                  <p key={i} className="text-xs leading-relaxed" style={{ color: S.t3 }}>
                    {Object.values(c).join(" · ").slice(0, 200)}
                  </p>
                ))}
              </div>
            )}
            {liabilities.length > 0 && (
              <div className="mt-1 rounded-md p-2.5" style={{ background: S.surface, border: `1px solid ${S.border}` }}>
                <p className="text-xs mb-1" style={{ color: S.t4, fontSize: 10 }}>LIABILITY BREAKDOWN</p>
                {liabilities.slice(0, 5).map((l, i) => (
                  <div key={i} className="flex justify-between text-xs">
                    <span className="truncate mr-2" style={{ color: S.t3 }}>{l.item}</span>
                    <span className="mono tabular-nums flex-shrink-0" style={{ color: S.t2 }}>{fmtRs(l.total_rs)}</span>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section icon={Sparkles} title="12 · Additional Intel" S={S}>
            <Field label="Viral / Internet Fame" value={cur.viralFame ?? DASH} S={S} />
            <Field label="Awards & Recognition" value={cur.awards ?? DASH} S={S} />
            <Field label="Public Perception" value={cur.publicPerception ?? DASH} S={S} />
            <Field label="Key Local Issues" value={cur.localIssues ?? DASH} S={S} />
          </Section>

          {/* Executive summary */}
          {(cur.execStanding || cur.execFinancial || cur.execLegal || cur.execInternet) && (
            <div className="rounded-lg p-4" style={{ background: "rgba(249,115,22,0.06)", border: "1px solid rgba(249,115,22,0.25)" }}>
              <p className="text-xs font-bold mb-2" style={{ color: S.saffron }}>EXECUTIVE SUMMARY</p>
              <div className="space-y-1.5 text-xs" style={{ color: S.t2 }}>
                {cur.execStanding && <p><b style={{ color: S.t1 }}>Political Standing:</b> {cur.execStanding}</p>}
                {cur.execFinancial && <p><b style={{ color: S.t1 }}>Financial Health:</b> {cur.execFinancial}</p>}
                {cur.execLegal && <p><b style={{ color: S.t1 }}>Legal Status:</b> {cur.execLegal}</p>}
                {cur.execInternet && <p><b style={{ color: S.t1 }}>Internet Footprint:</b> {cur.execInternet}</p>}
              </div>
            </div>
          )}

          {/* Sources */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            {sourceUrl && (
              <a href={sourceUrl} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs"
                style={{ background: "rgba(249,115,22,0.1)", border: "1px solid rgba(249,115,22,0.25)", color: S.saffron }}>
                <FileText size={11} /> MyNeta affidavit
              </a>
            )}
            {Object.entries(cur.sources ?? {}).map(([k, url]) => (
              <a key={k} href={url} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs"
                style={{ border: `1px solid ${S.border}`, color: S.t3 }}>
                <ExternalLink size={10} /> {k}
              </a>
            ))}
          </div>

          <p className="text-xs pt-1" style={{ color: S.t4, fontSize: 10 }}>
            Affidavit fields sourced from MyNeta. Extended profile is hand-verified per candidate; fields marked {DASH} are not yet on file.
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Section({ icon: Icon, title, children, S }: {
  icon: React.ElementType; title: string; children: React.ReactNode; S: Record<string, string>;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <Icon size={13} style={{ color: S.saffron }} />
        <h3 className="text-xs font-bold" style={{ color: S.t1, letterSpacing: "0.02em" }}>{title}</h3>
      </div>
      <div className="space-y-2 pl-1">{children}</div>
    </div>
  );
}

function Field({ label, value, context, verdict, S }: {
  label: string; value: string; context?: string; verdict?: string; S: Record<string, string>;
}) {
  const empty = value === "—" || value === "₹0" || !value;
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-baseline gap-2 flex-wrap">
        <span className="text-xs font-medium flex-shrink-0" style={{ color: S.t4, minWidth: 130 }}>{label}</span>
        <span className="text-xs flex-1" style={{ color: empty ? S.t4 : S.t1 }}>{value}</span>
        {verdict && (
          <span className="pill" style={{ borderColor: "rgba(16,185,129,0.3)", background: "rgba(16,185,129,0.1)", color: "var(--green)", fontSize: 9, padding: "1px 7px" }}>
            {verdict}
          </span>
        )}
      </div>
      {context && <span className="text-xs pl-[138px]" style={{ color: S.t3, fontSize: 11 }}>{context}</span>}
    </div>
  );
}
