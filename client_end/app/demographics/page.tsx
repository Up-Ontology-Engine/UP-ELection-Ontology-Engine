import { api } from "@/lib/api";
import DemographicsCharts from "./DemographicsCharts";
import { Users } from "lucide-react";

const AC_ID = "GKP_URBAN";

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toLocaleString("en-IN");
}

export default async function DemographicsPage() {
  const [boothsRes, qualityRes] = await Promise.allSettled([
    api.booths(AC_ID),
    api.quality(AC_ID),
  ]);

  const booths = boothsRes.status === "fulfilled" ? boothsRes.value.booths : [];
  const quality = qualityRes.status === "fulfilled" ? qualityRes.value : null;

  const totalVoters = booths.reduce((s, b) => s + (b.total_voters ?? 0), 0);
  const totalMale   = booths.reduce((s, b) => s + (b.male_voters ?? 0), 0);
  const totalFemale = booths.reduce((s, b) => s + (b.female_voters ?? 0), 0);
  const genderRatio = totalFemale > 0 ? (totalFemale / totalMale * 1000) : null;

  // Derived segments
  const highFemale = booths.filter((b) => {
    if (!b.female_voters || !b.male_voters) return false;
    return (b.female_voters / (b.male_voters + b.female_voters)) > 0.48;
  });
  const lowConfidence = booths.filter((b) => b.confidence_label?.toUpperCase() === "LOW");
  const bjpStrong = booths.filter((b) => b.digital_lean_label?.toUpperCase() === "STRONG_BJP");
  const oppStrong = booths.filter((b) => b.digital_lean_label?.toUpperCase() === "STRONG_OPP");
  const highEventCount = booths.filter((b) => (b.event_count ?? 0) > 10);
  const noData = booths.filter((b) => b.bjp_pulse_score == null);

  // Locality distribution
  const localityDist: Record<string, number> = {};
  booths.forEach((b) => {
    const loc = b.locality_hint ?? "Unknown";
    localityDist[loc] = (localityDist[loc] ?? 0) + (b.total_voters ?? 0);
  });
  const localityRows = Object.entries(localityDist)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const segments = [
    { label: "Women-Priority Booths", count: highFemale.length, desc: ">48% female voters", color: "#ec4899" },
    { label: "Strong BJP Booths", count: bjpStrong.length, desc: "Digital lean: STRONG_BJP", color: "#f97316" },
    { label: "Strong Opp Booths", count: oppStrong.length, desc: "Digital lean: STRONG_OPP", color: "#3b82f6" },
    { label: "High-Activity Booths", count: highEventCount.length, desc: ">10 pulse events", color: "#10b981" },
    { label: "Data-Poor Booths", count: lowConfidence.length, desc: "LOW confidence label", color: "#ef4444" },
    { label: "No Pulse Data", count: noData.length, desc: "No digital signal yet", color: "#475569" },
  ];

  // Per-booth voter data for charts
  const boothData = booths
    .filter((b) => b.total_voters && b.total_voters > 0)
    .map((b) => ({
      name: `B${b.booth_number}`,
      voters: b.total_voters!,
      male: b.male_voters ?? 0,
      female: b.female_voters ?? 0,
    }))
    .sort((a, b) => b.voters - a.voters)
    .slice(0, 20);

  return (
    <div className="min-h-screen p-6" style={{ background: "#0a0e1a" }}>
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-2 h-6 rounded-full" style={{ background: "#10b981" }} />
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Users size={20} style={{ color: "#10b981" }} /> Demographic Insights
          </h1>
        </div>
        <p className="text-sm ml-5" style={{ color: "#94a3b8" }}>
          Voter composition, gender distribution, and booth segmentation · Gorakhpur Urban AC
        </p>
      </div>

      {/* Top KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="rounded-xl p-4" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "#94a3b8" }}>Total Voters</p>
          <p className="text-2xl font-bold text-white">{fmt(totalVoters)}</p>
        </div>
        <div className="rounded-xl p-4" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "#94a3b8" }}>Male Voters</p>
          <p className="text-2xl font-bold" style={{ color: "#3b82f6" }}>{fmt(totalMale)}</p>
          <p className="text-xs mt-1" style={{ color: "#475569" }}>
            {totalVoters > 0 ? ((totalMale / totalVoters) * 100).toFixed(1) : "—"}%
          </p>
        </div>
        <div className="rounded-xl p-4" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "#94a3b8" }}>Female Voters</p>
          <p className="text-2xl font-bold" style={{ color: "#ec4899" }}>{fmt(totalFemale)}</p>
          <p className="text-xs mt-1" style={{ color: "#475569" }}>
            {totalVoters > 0 ? ((totalFemale / totalVoters) * 100).toFixed(1) : "—"}%
          </p>
        </div>
        <div className="rounded-xl p-4" style={{ background: "#111827", border: "1px solid #1e2d45" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "#94a3b8" }}>Gender Ratio</p>
          <p className="text-2xl font-bold text-white">
            {genderRatio != null ? genderRatio.toFixed(0) : "—"}
          </p>
          <p className="text-xs mt-1" style={{ color: "#475569" }}>females per 1000 males</p>
        </div>
      </div>

      {/* Segments */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        {segments.map((s) => (
          <div key={s.label} className="rounded-xl p-4 flex flex-col gap-2"
            style={{ background: "#111827", border: `1px solid ${s.color}33` }}>
            <p className="text-xs" style={{ color: s.color }}>{s.desc}</p>
            <div className="flex items-end justify-between">
              <p className="text-2xl font-bold text-white">{s.count}</p>
              <p className="text-xs" style={{ color: "#94a3b8" }}>booths</p>
            </div>
            <p className="text-sm font-medium text-white">{s.label}</p>
            <div className="h-1 rounded-full" style={{ background: "#1e2d45" }}>
              <div className="h-1 rounded-full" style={{
                width: `${booths.length > 0 ? (s.count / booths.length) * 100 : 0}%`,
                background: s.color
              }} />
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <DemographicsCharts boothData={boothData} localityRows={localityRows} totalMale={totalMale} totalFemale={totalFemale} />

      {/* Booth table */}
      <div className="rounded-xl overflow-hidden mt-6" style={{ border: "1px solid #1e2d45" }}>
        <div className="px-4 py-3" style={{ background: "#090d18", borderBottom: "1px solid #1e2d45" }}>
          <h3 className="text-sm font-semibold text-white">Booth-Level Voter Composition</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr style={{ background: "#0d1525", borderBottom: "1px solid #1e2d45" }}>
                {["Booth #", "Name", "Total", "Male", "Female", "% Female", "Lean"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left font-medium uppercase tracking-wider"
                    style={{ color: "#475569" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {booths.map((b, i) => {
                const fPct = (b.total_voters && b.female_voters)
                  ? ((b.female_voters / b.total_voters) * 100).toFixed(1)
                  : "—";
                return (
                  <tr key={b.booth_id}
                    style={{ background: i % 2 === 0 ? "#111827" : "#0d1525", borderBottom: "1px solid #1e2d4520" }}>
                    <td className="px-3 py-2 font-mono" style={{ color: "#475569" }}>{b.booth_number}</td>
                    <td className="px-3 py-2 text-white max-w-48 truncate">{b.name}</td>
                    <td className="px-3 py-2" style={{ color: "#f1f5f9" }}>{fmt(b.total_voters)}</td>
                    <td className="px-3 py-2" style={{ color: "#3b82f6" }}>{fmt(b.male_voters)}</td>
                    <td className="px-3 py-2" style={{ color: "#ec4899" }}>{fmt(b.female_voters)}</td>
                    <td className="px-3 py-2" style={{ color: "#94a3b8" }}>{fPct}%</td>
                    <td className="px-3 py-2" style={{ color: "#94a3b8" }}>{b.digital_lean_label ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
