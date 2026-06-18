// Mostra a nota de um time (OVR / Química / Nota Final) com barras.
export default function ScoreCard({ title, score, accent, best }) {
  if (!score) return null
  return (
    <div className={`score-card ${best ? 'best' : ''}`} style={accent ? { '--accent': accent } : {}}>
      <h3>
        {title}
        {best && <span className="best-badge">★ melhor</span>}
      </h3>
      <div className="score-final">{score.final_score.toFixed(2)}</div>
      <div className="score-final-label">Nota Final</div>
      <Metric label="OVR médio" value={score.ovr} max={100} />
      <Metric label="Química" value={score.chemistry} max={12} suffix={` (${score.chemistry_total}/33)`} />
    </div>
  )
}

function Metric({ label, value, max, suffix }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className="metric">
      <div className="metric-head">
        <span>{label}</span>
        <span>
          {value.toFixed(2)}
          {suffix || ''}
        </span>
      </div>
      <div className="metric-bar">
        <div className="metric-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
