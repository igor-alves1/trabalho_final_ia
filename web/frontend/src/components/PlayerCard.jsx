import { useState } from 'react'
import { faceUrl } from '../api.js'

// Carta estilo FUT.
// Props extras:
//  - highlight: { nationality, league, club } com 'active' | 'building' (destaca onde há química)
//  - preview: { delta_chem, new_chem, new_ovr, delta_ovr, status } -> tooltip no hover
//  - onHoverChange: (bool) => void  (avisa o pai para destacar o campo)
export default function PlayerCard({
  card, position, selected, onClick, compact, chemistry, highlight, preview, onHoverChange,
}) {
  const [imgError, setImgError] = useState(false)
  const ovr = card.overall
  const tier =
    ovr >= 88 ? 'tier-icon' : ovr >= 84 ? 'tier-gold' : ovr >= 80 ? 'tier-silver' : 'tier-bronze'

  const pos = position || card.choosen_position || (card.player_positions || '').split(',')[0]
  const hl = highlight || {}

  const handleEnter = () => onHoverChange && onHoverChange(true)
  const handleLeave = () => onHoverChange && onHoverChange(false)

  return (
    <button
      className={`player-card ${tier} ${selected ? 'selected' : ''} ${compact ? 'compact' : ''} ${onClick ? 'clickable' : ''}`}
      onClick={onClick}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      type="button"
      disabled={!onClick}
    >
      <div className="card-top">
        <div className="card-meta">
          <span className="card-ovr">{ovr}</span>
          <span className="card-pos">{pos}</span>
        </div>
        <div className="card-face">
          {!imgError ? (
            <img
              src={faceUrl(card.player_id)}
              alt={card.short_name}
              onError={() => setImgError(true)}
              loading="lazy"
            />
          ) : (
            <div className="card-face-fallback">{(card.short_name || '?')[0]}</div>
          )}
        </div>
      </div>
      <div className="card-name">{card.short_name}</div>
      {chemistry != null && (
        <div className="card-chem">
          {[0, 1, 2].map((i) => (
            <span key={i} className={`chem-pip ${i < chemistry ? 'on' : ''}`} />
          ))}
        </div>
      )}
      <div className="card-info">
        <span className={`info-nat hl-${hl.nationality || 'none'}`} title="País">{card.nationality_name}</span>
        <span className={`info-lea hl-${hl.league || 'none'}`} title="Liga">{card.league_name}</span>
        <span className={`info-clu hl-${hl.club || 'none'}`} title="Clube">{card.club_name}</span>
      </div>

      {preview && (
        <div className="card-tooltip">
          <div className="tip-row">
            <span>Química</span>
            <span className={`tip-delta ${preview.delta_chem > 0 ? 'up' : ''}`}>
              {preview.delta_chem > 0 ? `+${preview.delta_chem}` : preview.delta_chem} (→ {preview.new_chem})
            </span>
          </div>
          <div className="tip-row">
            <span>OVR médio</span>
            <span className="tip-delta">
              {preview.new_ovr}
              {preview.delta_ovr !== 0 && (
                <em className={preview.delta_ovr > 0 ? 'up' : 'down'}>
                  {' '}
                  ({preview.delta_ovr > 0 ? '+' : ''}
                  {preview.delta_ovr})
                </em>
              )}
            </span>
          </div>
          <div className="tip-chips">
            <Chip label={card.nationality_name} status={preview.status?.nationality} />
            <Chip label={card.league_name} status={preview.status?.league} />
            <Chip label={card.club_name} status={preview.status?.club} />
          </div>
        </div>
      )}
    </button>
  )
}

function Chip({ label, status }) {
  if (!label) return null
  return <span className={`chip hl-${status || 'none'}`}>{label}</span>
}
