import PlayerCard from './PlayerCard.jsx'

// Coordenadas (% top/left) para cada slot da formação 4-3-3, na ordem do FORMACAO.
// ['ST','LW','RW','CM','CM','CM','LB','CB','CB','RB','GK']
const COORDS = [
  { top: 9, left: 50 },   // ST
  { top: 22, left: 17 },  // LW
  { top: 22, left: 83 },  // RW
  { top: 44, left: 27 },  // CM
  { top: 39, left: 50 },  // CM
  { top: 44, left: 73 },  // CM
  { top: 69, left: 11 },  // LB
  { top: 71, left: 37 },  // CB
  { top: 71, left: 63 },  // CB
  { top: 69, left: 89 },  // RB
  { top: 89, left: 50 },  // GK
]

// `squad` é a lista de jogadores (com choosen_position e chemistry) OU null por slot.
// `linkCard` (opcional): carta em hover; destaca nos titulares as dimensões em comum.
// `linkStatus` (opcional): status por dimensão do candidato em hover ('active'|'building').
export default function Pitch({ squad, positions, highlightSlot, linkCard, linkStatus }) {
  return (
    <div className="pitch">
      <div className="pitch-lines" />
      {positions.map((pos, idx) => {
        const player = squad[idx]
        const coord = COORDS[idx]
        let highlight
        if (player && linkCard) {
          highlight = {
            nationality:
              player.nationality_id === linkCard.nationality_id ? linkStatus?.nationality : 'none',
            league: player.league_id === linkCard.league_id ? linkStatus?.league : 'none',
            club: player.club_team_id === linkCard.club_team_id ? linkStatus?.club : 'none',
          }
        }
        return (
          <div
            key={idx}
            className={`pitch-slot ${highlightSlot === idx ? 'highlight' : ''}`}
            style={{ top: `${coord.top}%`, left: `${coord.left}%` }}
          >
            {player ? (
              <PlayerCard
                card={player}
                position={player.choosen_position || pos}
                chemistry={player.chemistry}
                highlight={highlight}
                compact
              />
            ) : (
              <div className="empty-slot">
                <span>{pos}</span>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
