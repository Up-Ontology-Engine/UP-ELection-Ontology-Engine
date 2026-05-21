interface Props {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
  icon?: React.ReactNode;
}

export default function StatCard({ label, value, sub, color = "#f97316", icon }: Props) {
  return (
    <div className="rounded-xl p-4 flex flex-col gap-1"
      style={{ background: "#111827", border: "1px solid #1e2d45" }}>
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider" style={{ color: "#94a3b8" }}>{label}</span>
        {icon && <span style={{ color }}>{icon}</span>}
      </div>
      <p className="text-2xl font-bold" style={{ color }}>{value}</p>
      {sub && <p className="text-xs" style={{ color: "#475569" }}>{sub}</p>}
    </div>
  );
}
