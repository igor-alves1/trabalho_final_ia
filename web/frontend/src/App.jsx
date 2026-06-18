import { useState, useMemo, useEffect } from 'react'
import { newDraft, evaluateSquad, aiPlay, previewSlot } from './api.js'
import PlayerCard from './components/PlayerCard.jsx'
import Pitch from './components/Pitch.jsx'
import ScoreCard from './components/ScoreCard.jsx'

const AI_MODES = [
  { id: 'random', label: 'Random', desc: 'Escolhe carta e posição aleatórias.' },
  { id: 'greedy_ovr', label: 'Greedy OVR', desc: 'Sempre o maior overall.' },
  { id: 'greedy_f', label: 'Greedy F', desc: 'Maximiza OVR + química localmente.' },
  { id: 'expectimax', label: 'Expectimax', desc: 'Busca + Monte Carlo (rollouts).' },
]

const AI_COLORS = {
  random: '#9ca3af',
  greedy_ovr: '#60a5fa',
  greedy_f: '#34d399',
  expectimax: '#f472b6',
}

export default function App() {
  const [view, setView] = useState('start') // start | drafting | compare
  const [draft, setDraft] = useState(null)
  const [picks, setPicks] = useState([])
  const [currentSlot, setCurrentSlot] = useState(0)
  const [humanScore, setHumanScore] = useState(null)
  const [aiMode, setAiMode] = useState('expectimax')
  const [aiRollouts, setAiRollouts] = useState(100)
  const [aiRuns, setAiRuns] = useState([]) // [{label, color, score}]
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [preview, setPreview] = useState(null) // preview do slot atual
  const [hoveredIdx, setHoveredIdx] = useState(null) // carta candidata em hover

  const formation = draft?.formation || []

  // Busca o preview (química/OVR parcial + ganhos por carta) ao mudar de slot.
  useEffect(() => {
    if (view !== 'drafting' || !draft) return
    let cancelled = false
    setHoveredIdx(null)
    previewSlot(draft.draft_id, picks.slice(0, currentSlot), currentSlot)
      .then((p) => { if (!cancelled) setPreview(p) })
      .catch(() => { if (!cancelled) setPreview(null) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, draft, currentSlot])

  // Time parcial do humano (durante o draft) indexado por slot.
  // Anexa a química individual (bolinhas) vinda do preview.
  const partialSquad = useMemo(() => {
    if (!draft) return []
    const chemBySlot = preview?.current?.chem_by_slot || {}
    return draft.slots.map((slot, idx) => {
      const pick = picks[idx]
      if (pick == null) return null
      return {
        ...slot.cards[pick],
        choosen_position: slot.position,
        chemistry: chemBySlot[idx],
      }
    })
  }, [draft, picks, preview])

  async function handleNewDraft() {
    setLoading(true)
    setError(null)
    try {
      const d = await newDraft()
      setDraft(d)
      setPicks(new Array(d.slots.length).fill(null))
      setCurrentSlot(0)
      setHumanScore(null)
      setAiRuns([])
      setView('drafting')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handlePick(cardIdx) {
    const newPicks = [...picks]
    newPicks[currentSlot] = cardIdx
    setPicks(newPicks)
    if (currentSlot < draft.slots.length - 1) {
      setCurrentSlot(currentSlot + 1)
    } else {
      // último slot escolhido -> avalia o time
      setLoading(true)
      setError(null)
      try {
        const score = await evaluateSquad(draft.draft_id, newPicks)
        setHumanScore(score)
        setView('compare')
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
  }

  async function handleRunAI() {
    setLoading(true)
    setError(null)
    try {
      const result = await aiPlay(draft.draft_id, aiMode, aiRollouts)
      const label =
        aiMode === 'expectimax' ? `Expectimax (${aiRollouts})` : AI_MODES.find((m) => m.id === aiMode).label
      setAiRuns((prev) => [
        ...prev.filter((r) => r.label !== label),
        { label, color: AI_COLORS[aiMode], score: result, mode: aiMode },
      ])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // Melhor nota entre humano + IAs (para destacar).
  const bestFinal = useMemo(() => {
    const vals = []
    if (humanScore) vals.push(humanScore.final_score)
    aiRuns.forEach((r) => vals.push(r.score.final_score))
    return vals.length ? Math.max(...vals) : null
  }, [humanScore, aiRuns])

  const lastAi = aiRuns[aiRuns.length - 1]

  return (
    <div className="app">
      <header className="header">
        <div className="header-title">
          <span className="logo">⚽</span>
          <div>
            <h1>EA FC 26 — Draft AI</h1>
            <p>Monte seu time 4-3-3 e enfrente a Inteligência Artificial no mesmo draft.</p>
          </div>
        </div>
        {view !== 'start' && (
          <button className="btn ghost" onClick={handleNewDraft} disabled={loading}>
            Novo Draft
          </button>
        )}
      </header>

      {error && <div className="error-banner">⚠ {error}</div>}

      {view === 'start' && (
        <div className="start-screen">
          <div className="start-card">
            <h2>Como funciona</h2>
            <ol>
              <li>Geramos um draft: 11 posições (4-3-3), cada uma com 5 cartas sorteadas.</li>
              <li>Você escolhe 1 carta por posição (a 1ª é o capitão, OVR ≥ 88).</li>
              <li>A IA joga o <strong>mesmo</strong> draft e comparamos as notas.</li>
            </ol>
            <button className="btn primary big" onClick={handleNewDraft} disabled={loading}>
              {loading ? 'Gerando...' : 'Começar Draft'}
            </button>
          </div>
        </div>
      )}

      {view === 'drafting' && draft && (
        <div className="draft-layout">
          <div className="draft-main">
            <div className="round-info">
              <div className="round-info-top">
                <span className="round-badge">
                  Rodada {currentSlot + 1} / {draft.slots.length}
                </span>
                <div className="team-stats">
                  <div className="stat">
                    <span className="stat-label">Química do time</span>
                    <span className="stat-value chem">{preview ? preview.current.chemistry_total : 0}<small>/33</small></span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">OVR médio</span>
                    <span className="stat-value">{preview && preview.current.n ? preview.current.ovr.toFixed(1) : '—'}</span>
                  </div>
                </div>
              </div>
              <h2>
                Escolha um jogador para <span className="pos-tag">{draft.slots[currentSlot].position}</span>
                {currentSlot === 0 && <span className="captain-tag">⭐ Capitão</span>}
              </h2>
              <p className="round-hint">
                Passe o mouse numa carta para ver o ganho de química/OVR. Verde = já pontua,
                amarelo = caminhando para pontuar.
              </p>
            </div>
            <div className="card-grid">
              {draft.slots[currentSlot].cards.map((card, idx) => {
                const cp = preview?.candidates?.[idx]
                return (
                  <PlayerCard
                    key={card.player_id}
                    card={card}
                    position={draft.slots[currentSlot].position}
                    onClick={() => handlePick(idx)}
                    preview={cp}
                    highlight={cp?.status}
                    onHoverChange={(on) => setHoveredIdx(on ? idx : (h) => (h === idx ? null : h))}
                  />
                )
              })}
            </div>
          </div>
          <aside className="draft-side">
            <h3>Seu time {preview?.current?.n ? `(${preview.current.n}/11)` : ''}</h3>
            <Pitch
              squad={partialSquad}
              positions={formation}
              highlightSlot={currentSlot}
              linkCard={hoveredIdx != null ? draft.slots[currentSlot].cards[hoveredIdx] : null}
              linkStatus={hoveredIdx != null ? preview?.candidates?.[hoveredIdx]?.status : null}
            />
          </aside>
        </div>
      )}

      {view === 'compare' && (
        <div className="compare-layout">
          <section className="ai-controls">
            <h2>Rode a IA no mesmo draft</h2>
            <div className="controls-row">
              <div className="mode-pills">
                {AI_MODES.map((m) => (
                  <button
                    key={m.id}
                    className={`pill ${aiMode === m.id ? 'active' : ''}`}
                    style={aiMode === m.id ? { '--accent': AI_COLORS[m.id] } : {}}
                    onClick={() => setAiMode(m.id)}
                    title={m.desc}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
              {aiMode === 'expectimax' && (
                <label className="rollouts">
                  Rollouts:
                  <input
                    type="number"
                    min="10"
                    max="2000"
                    step="10"
                    value={aiRollouts}
                    onChange={(e) => setAiRollouts(Number(e.target.value))}
                  />
                </label>
              )}
              <button className="btn primary" onClick={handleRunAI} disabled={loading}>
                {loading ? 'Rodando IA...' : '▶ Rodar IA'}
              </button>
            </div>
            <p className="mode-desc">{AI_MODES.find((m) => m.id === aiMode).desc}</p>
          </section>

          <div className="pitches">
            <div className="pitch-col">
              <h3 className="pitch-title human">👤 Seu time</h3>
              <Pitch squad={humanScore?.players || []} positions={formation} />
            </div>
            <div className="pitch-col">
              <h3 className="pitch-title ai" style={lastAi ? { color: lastAi.color } : {}}>
                🤖 {lastAi ? lastAi.label : 'IA'}
              </h3>
              {lastAi ? (
                <Pitch squad={lastAi.score.players} positions={formation} />
              ) : (
                <div className="ai-placeholder">Escolha um algoritmo e clique em "Rodar IA".</div>
              )}
            </div>
          </div>

          <div className="scores">
            <ScoreCard title="👤 Você" score={humanScore} accent="#fbbf24" best={humanScore?.final_score === bestFinal} />
            {aiRuns.map((r) => (
              <ScoreCard
                key={r.label}
                title={`🤖 ${r.label}`}
                score={r.score}
                accent={r.color}
                best={r.score.final_score === bestFinal}
              />
            ))}
          </div>

          {aiRuns.length > 0 && (
            <ComparisonTable human={humanScore} aiRuns={aiRuns} bestFinal={bestFinal} />
          )}
        </div>
      )}

      <footer className="footer">
        <div className="footer-formula">
          Fórmula: <code>Nota = OVR_médio + (Química_total × 4 / 11)</code> · Formação fixa 4-3-3 ·
          Mesmo draft para humano e IA.
        </div>
        <div className="footer-rules">
          <strong>Química em degraus</strong> — cada atributo só pontua a partir de um nº mínimo de
          jogadores que o compartilham (até 3 pontos por jogador):
          <span className="rule"><b>País</b> 2 / 5 / 8</span>
          <span className="rule"><b>Clube</b> 2 / 4 / 7</span>
          <span className="rule"><b>Liga</b> 3 / 5 / 8</span>
          <span className="rule-note">(nº de jogadores → 1 / 2 / 3 pontos)</span>
          <br />
          <span className="legend-dot active" /> verde = já pontua &nbsp;·&nbsp;
          <span className="legend-dot building" /> amarelo = caminhando (tem 2, falta atingir o limiar — só ocorre na Liga, que precisa de 3)
        </div>
      </footer>
    </div>
  )
}

function ComparisonTable({ human, aiRuns, bestFinal }) {
  const rows = [
    { label: '👤 Você', score: human, color: '#fbbf24' },
    ...aiRuns.map((r) => ({ label: `🤖 ${r.label}`, score: r.score, color: r.color })),
  ]
  return (
    <div className="comp-table-wrap">
      <h3>Comparação</h3>
      <table className="comp-table">
        <thead>
          <tr>
            <th>Jogador</th>
            <th>OVR médio</th>
            <th>Química</th>
            <th>Nota Final</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className={r.score.final_score === bestFinal ? 'best-row' : ''}>
              <td>
                <span className="dot" style={{ background: r.color }} /> {r.label}
              </td>
              <td>{r.score.ovr.toFixed(2)}</td>
              <td>
                {r.score.chemistry.toFixed(2)} <span className="muted">({r.score.chemistry_total}/33)</span>
              </td>
              <td className="final-cell">{r.score.final_score.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
