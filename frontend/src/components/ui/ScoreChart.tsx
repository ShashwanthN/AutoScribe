export type ScorePoint = {
  key: string;
  label: string;
  score: number | null;
  active?: boolean;
};

/**
 * Minimal inline SVG line chart — score per run, no charting dependency.
 * Deliberately simple: only what the Voice Lab needs (a trend + a
 * highlighted "deployed" point), not a general-purpose chart component.
 */
export function ScoreChart({ points }: { points: ScorePoint[] }) {
  const scored = points.filter((p): p is ScorePoint & { score: number } => p.score !== null);
  if (scored.length === 0) {
    return (
      <div className="grid h-[140px] place-items-center rounded-control border border-dashed border-border text-sm text-text-muted">
        Scores will appear here after your first run.
      </div>
    );
  }

  const width = 640;
  const height = 140;
  const padX = 28;
  const padY = 18;
  const scores = scored.map((p) => p.score);
  const min = Math.min(...scores, 0);
  const max = Math.max(...scores, 1);
  const range = max - min || 1;

  const xFor = (i: number) =>
    points.length === 1 ? width / 2 : padX + (i / (points.length - 1)) * (width - padX * 2);
  const yFor = (score: number) => height - padY - ((score - min) / range) * (height - padY * 2);

  const linePath = points
    .map((p, i) => (p.score === null ? null : `${i === 0 || points[i - 1]?.score === null ? "M" : "L"} ${xFor(i)} ${yFor(p.score)}`))
    .filter(Boolean)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-[140px] w-full" preserveAspectRatio="none">
      <line x1={padX} y1={height - padY} x2={width - padX} y2={height - padY} stroke="var(--color-border)" strokeWidth={1} />
      <path d={linePath} fill="none" stroke="var(--color-accent)" strokeWidth={2} />
      {points.map((p, i) =>
        p.score === null ? null : (
          <g key={p.key}>
            <circle
              cx={xFor(i)}
              cy={yFor(p.score)}
              r={p.active ? 5 : 3.5}
              fill={p.active ? "var(--color-accent)" : "var(--color-surface)"}
              stroke="var(--color-accent)"
              strokeWidth={2}
            />
            {p.active ? (
              <text x={xFor(i)} y={yFor(p.score) - 12} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--color-accent)">
                deployed
              </text>
            ) : null}
          </g>
        )
      )}
    </svg>
  );
}
