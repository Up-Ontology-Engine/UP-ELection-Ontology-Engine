interface Props {
  title: string;
  sub?: string;
  accent?: string;
  right?: React.ReactNode;
}

export default function SectionHeader({ title, sub, accent = "#f97316", right }: Props) {
  return (
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        <div className="w-0.5 h-4 rounded-full" style={{ background: accent }} />
        <div>
          <p className="text-xs font-semibold" style={{ color: "var(--text-1)" }}>{title}</p>
          {sub && <p className="text-xs" style={{ color: "var(--text-3)" }}>{sub}</p>}
        </div>
      </div>
      {right}
    </div>
  );
}
