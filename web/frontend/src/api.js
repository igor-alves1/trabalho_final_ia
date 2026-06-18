// Helpers de comunicação com o backend.

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || `Erro ${res.status}`)
  return data
}

export function newDraft() {
  return postJSON('/api/draft/new', {})
}

export function previewSlot(draftId, picks, slot) {
  return postJSON(`/api/draft/${draftId}/preview`, { picks, slot })
}

export function evaluateSquad(draftId, picks) {
  return postJSON(`/api/draft/${draftId}/evaluate`, { picks })
}

export function aiPlay(draftId, mode, numRollouts) {
  return postJSON(`/api/draft/${draftId}/ai`, {
    mode,
    num_rollouts: numRollouts,
  })
}

export function faceUrl(playerId) {
  return `/faces/${playerId}.png`
}
