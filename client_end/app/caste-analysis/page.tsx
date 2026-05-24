"use client"

import { useEffect, useState } from "react"
import { Users, BarChart3, Target, Activity } from "lucide-react"
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ZAxis } from 'recharts'
import { API_BASE } from "../../lib/api"

const PARTY_COLORS: Record<string, string> = {
  BJP: "#FF6B35",
  SP: "#E63946",
  BSP: "#2196F3",
  INC: "#4CAF50",
  IND: "#9E9E9E",
  NOTA: "#607D8B",
  OTHER: "#78909C"
}

export default function CasteAnalysisPage() {
  const [summary, setSummary] = useState<string>("Loading summary...")
  const [surnames, setSurnames] = useState<any[]>([])
  const [scatter, setScatter] = useState<any[]>([])
  const [influence, setInfluence] = useState<any>({})
  
  const [selectedCaste, setSelectedCaste] = useState<string>("caste_share_Ambiguous")
  const [selectedParty, setSelectedParty] = useState<string>("party_share_BJP")

  // Fetch initial data
  useEffect(() => {
    const fetchSurnames = async () => {
      try {
        const res = await fetch(`${API_BASE}/ac/GKP_322/caste/surnames`)
        setSurnames(await res.json())
      } catch (err) { console.error("Failed to load surnames", err) }
    }
    const fetchScatter = async () => {
      try {
        const res = await fetch(`${API_BASE}/ac/GKP_322/caste/scatter`)
        setScatter(await res.json())
      } catch (err) { console.error("Failed to load scatter", err) }
    }
    const fetchInfluence = async () => {
      try {
        const res = await fetch(`${API_BASE}/ac/GKP_322/caste/influence`)
        setInfluence(await res.json())
      } catch (err) { console.error("Failed to load influence", err) }
    }
    const fetchSummary = async () => {
      try {
        const res = await fetch(`${API_BASE}/ac/GKP_322/caste/summary`, { method: "POST" })
        const data = await res.json()
        setSummary(data.summary || "Summary generation failed.")
      } catch (err) { setSummary("Failed to generate AI summary.") }
    }
    
    fetchSurnames()
    fetchScatter()
    fetchInfluence()
    fetchSummary()
  }, [])

  const influenceEntries = Object.entries(influence || {}).map(([caste, data]: [string, any]) => ({ caste, ...data }))
    .sort((a, b) => (b.population_share || 0) - (a.population_share || 0))
    .slice(0, 15)

  // Filter valid data points for scatter plot
  const validScatter = Array.isArray(scatter) ? scatter : []
  const scatterData = validScatter.filter(d => d[selectedCaste] != null && d[selectedParty] != null)
                             .map(d => ({
                                x: d[selectedCaste] * 100,
                                y: d[selectedParty] * 100,
                                z: d.voter_roll_count,
                                winner: d.winner_party,
                                part: d.part_number
                             }))

  const casteCols = validScatter.length > 0 ? Object.keys(validScatter[0]).filter(k => k.startsWith("caste_share_")) : []
  const partyCols = validScatter.length > 0 ? Object.keys(validScatter[0]).filter(k => k.startsWith("party_share_")) : []

  return (
    <div className="flex h-screen bg-[#0F1117] text-slate-300 font-sans overflow-y-auto">
      <main className="flex-1 min-w-0 p-6 space-y-6 ml-56">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
              <Users className="text-blue-500" size={28} />
              Caste & Surname Electoral Influence Analysis
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Correlates voter surname distribution with booth-level election outcomes to surface which caste groups have the strongest electoral influence.
            </p>
          </div>
        </div>

        {/* AI Summary Box */}
        <div className="bg-[#13161F] border border-blue-900/50 rounded-xl p-5 shadow-lg relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-blue-500" />
          <h2 className="text-lg font-semibold text-slate-200 mb-3 flex items-center gap-2">
            <Activity className="text-blue-400" size={20} />
            AI Strategy Summary
          </h2>
          <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
            {summary}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Surnames Bar Chart Panel */}
          <div className="bg-[#13161F] border border-slate-800 rounded-xl p-5 shadow-lg">
            <h3 className="text-md font-semibold text-slate-200 mb-4 flex items-center gap-2">
              <BarChart3 className="text-emerald-500" size={18} />
              Top 25 Surnames in Voter Roll
            </h3>
            <div className="h-[400px] overflow-y-auto pr-2 custom-scrollbar">
              <div className="space-y-3">
                {Array.isArray(surnames) && surnames.map((item, idx) => {
                  const maxCount = Math.max(...surnames.map(s => s.count)) || 1
                  const width = `${(item.count / maxCount) * 100}%`
                  
                  let bg = "bg-slate-600"
                  if (item.category === "OBC" || item.category === "OBC_Baniya") bg = "bg-orange-500"
                  if (item.category === "SC") bg = "bg-purple-500"
                  if (item.category === "General") bg = "bg-blue-500"
                  if (item.category === "Muslim") bg = "bg-emerald-500"
                  if (item.category === "Ambiguous") bg = "bg-slate-500"

                  return (
                    <div key={idx} className="relative">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-medium text-slate-300">{item.surname} <span className="text-slate-500 ml-1">({item.category})</span></span>
                        <span className="text-slate-400">{item.count.toLocaleString()}</span>
                      </div>
                      <div className="w-full bg-slate-800/50 rounded-full h-2">
                        <div className={`${bg} h-2 rounded-full`} style={{ width }}></div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Scatter Plot */}
          <div className="bg-[#13161F] border border-slate-800 rounded-xl p-5 shadow-lg">
             <h3 className="text-md font-semibold text-slate-200 mb-4 flex items-center gap-2">
              <Target className="text-purple-500" size={18} />
              Booth-Level Scatter: Caste Share vs Party Vote Share
            </h3>
            <div className="flex gap-4 mb-4">
              <select className="bg-[#1E2333] border border-slate-700 text-xs rounded p-1.5 text-slate-300"
                      value={selectedCaste} onChange={e => setSelectedCaste(e.target.value)}>
                {casteCols.map(c => <option key={c} value={c}>{c.replace("caste_share_", "")}</option>)}
              </select>
              <select className="bg-[#1E2333] border border-slate-700 text-xs rounded p-1.5 text-slate-300"
                      value={selectedParty} onChange={e => setSelectedParty(e.target.value)}>
                {partyCols.map(c => <option key={c} value={c}>{c.replace("party_share_", "")}</option>)}
              </select>
            </div>
            <div className="h-[350px] w-full">
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
                <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E2333" />
                  <XAxis type="number" dataKey="x" name="Caste Share" unit="%" stroke="#64748b" tick={{fontSize: 12}} />
                  <YAxis type="number" dataKey="y" name="Party Vote Share" unit="%" stroke="#64748b" tick={{fontSize: 12}} />
                  <ZAxis type="number" dataKey="z" range={[50, 300]} name="Voter Roll Count" />
                  <Tooltip 
                    cursor={{ strokeDasharray: '3 3' }} 
                    contentStyle={{ backgroundColor: '#13161F', borderColor: '#1E2333', fontSize: '12px' }}
                    formatter={(value: any, name: string) => [Number(value).toFixed(1) + (name !== "Voter Roll Count" ? "%" : ""), name]}
                  />
                  <Scatter data={scatterData}>
                    {scatterData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={PARTY_COLORS[entry.winner] || PARTY_COLORS.OTHER} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
        
        {/* Influence Table */}
        <div className="bg-[#13161F] border border-slate-800 rounded-xl p-5 shadow-lg overflow-x-auto">
          <h3 className="text-md font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Users className="text-blue-500" size={18} />
            Top Influential Caste Groups
          </h3>
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="p-3 font-medium">Caste Group</th>
                <th className="p-3 font-medium text-right">Pop. Share</th>
                <th className="p-3 font-medium">Dominant Party</th>
                <th className="p-3 font-medium text-right">Win% (Dom Booths)</th>
                <th className="p-3 font-medium text-center">Swing Potential</th>
                <th className="p-3 font-medium text-right">Best Corr r</th>
              </tr>
            </thead>
            <tbody>
              {influenceEntries.map((row, idx) => (
                <tr key={idx} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                  <td className="p-3 font-medium text-slate-200">{row.caste}</td>
                  <td className="p-3 text-right text-slate-400">{(row.population_share * 100).toFixed(1)}%</td>
                  <td className="p-3">
                    {row.dominant_party ? (
                      <span className="px-2 py-0.5 rounded text-xs font-semibold" 
                            style={{ backgroundColor: `${PARTY_COLORS[row.dominant_party]}33`, color: PARTY_COLORS[row.dominant_party] }}>
                        {row.dominant_party}
                      </span>
                    ) : <span className="text-slate-600">—</span>}
                  </td>
                  <td className="p-3 text-right text-slate-300">
                    {row.dominant_party_win_pct ? `${(row.dominant_party_win_pct * 100).toFixed(0)}%` : <span className="text-slate-600">—</span>}
                  </td>
                  <td className="p-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      row.swing_potential === 'HIGH' ? 'bg-red-500/20 text-red-400' :
                      row.swing_potential === 'MEDIUM' ? 'bg-orange-500/20 text-orange-400' :
                      row.swing_potential === 'LOW' ? 'bg-emerald-500/20 text-emerald-400' : 'text-slate-500'
                    }`}>
                      {row.swing_potential || '—'}
                    </span>
                  </td>
                  <td className="p-3 text-right font-mono text-xs text-slate-400">
                    {row.best_corr_r ? row.best_corr_r.toFixed(3) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </main>
    </div>
  )
}
