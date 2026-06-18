"""Núcleo compartilhado do backend web.

Carrega o banco de jogadores (mantendo `player_face_url`, ao contrário do
test.py) e oferece helpers para gerar drafts, serializar cartas e avaliar times
reutilizando exatamente a lógica de `eafc_utils` / `bot`.
"""
import os
import sys
from collections import Counter
import numpy as np
import pandas as pd

# Permite importar bot.py / eafc_utils.py / draft.py da raiz do projeto.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bot import Bot, FORMACAO  # noqa: E402
from eafc_utils import f, chemistry  # noqa: E402

CSV_PATH = os.path.join(PROJECT_ROOT, "data", "FC26_20250921.csv")

# Campos enviados ao frontend para cada carta.
CARD_FIELDS = [
    "player_id", "short_name", "long_name", "overall", "player_positions",
    "club_name", "league_name", "nationality_name",
    "club_team_id", "league_id", "nationality_id",
    "player_face_url", "pace", "shooting", "passing", "dribbling",
    "defending", "physic",
]


def setup_db():
    """Igual ao test.setup_db, mas preserva `player_face_url` (as imagens)."""
    df = pd.read_csv(CSV_PATH, low_memory=False)
    df = df[df["overall"] >= 75].copy()
    faixas = [
        (df["overall"] >= 87),
        (df["overall"] >= 84) & (df["overall"] < 87),
        (df["overall"] >= 80) & (df["overall"] < 84),
        (df["overall"] < 80),
    ]
    # Pesos favorecendo jogadores bons, mas com TODOS os tiers > 0 para que
    # toda posição seja sorteável (ex.: não há zagueiros/laterais 87+ suficientes,
    # então zerar os tiers baixos quebraria o sorteio ponderado).
    df["weight"] = np.select(faixas, [80, 50, 20, 5], default=0)
    return df


def _clean(v):
    """Converte valores numpy/NaN em tipos serializáveis em JSON."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, float) and np.isnan(v):
        return None
    if pd.isna(v) if not isinstance(v, (list, dict)) else False:
        return None
    return v


def card_to_dict(record: dict) -> dict:
    """Extrai apenas os campos relevantes de uma carta para o frontend."""
    out = {}
    for k in CARD_FIELDS:
        out[k] = _clean(record.get(k))
    return out


def draft_to_payload(draft: dict) -> list:
    """Converte um draft {slot: {posicao, cartas}} no formato da API."""
    slots = []
    for slot_idx in range(len(draft)):
        slot = draft[slot_idx]
        slots.append({
            "slot": slot_idx,
            "position": slot["posicao"],
            "cards": [card_to_dict(c) for c in slot["cartas"]],
        })
    return slots


# --- Química estrita (mesmos limiares de eafc_utils.chemistry) -------------
# (limiar p/ 1 ponto, limiar p/ 2 pontos, limiar p/ 3 pontos)
_LEAGUE_THRESH = (3, 5, 8)
_NATION_THRESH = (2, 5, 8)
_CLUB_THRESH = (2, 4, 7)


def _pts(qtd, thr):
    t1, t2, t3 = thr
    if qtd >= t3:
        return 3
    if qtd >= t2:
        return 2
    if qtd >= t1:
        return 1
    return 0


def _strict_chemistry_total(squad: list) -> int:
    """Química total estrita de uma lista de jogadores (mesma regra do jogo)."""
    if not squad:
        return 0
    cl = Counter(p["league_id"] for p in squad)
    cn = Counter(p["nationality_id"] for p in squad)
    cc = Counter(p["club_team_id"] for p in squad)
    total = 0
    for p in squad:
        if str(p.get("choosen_position", "")) in str(p.get("player_positions", "")):
            pts = (
                _pts(cl[p["league_id"]], _LEAGUE_THRESH)
                + _pts(cn[p["nationality_id"]], _NATION_THRESH)
                + _pts(cc[p["club_team_id"]], _CLUB_THRESH)
            )
            total += min(3, pts)
    return total


def _strict_chemistry_per_player(squad: list) -> list:
    """Química estrita (0-3) de cada jogador, na ordem da lista."""
    if not squad:
        return []
    cl = Counter(p["league_id"] for p in squad)
    cn = Counter(p["nationality_id"] for p in squad)
    cc = Counter(p["club_team_id"] for p in squad)
    out = []
    for p in squad:
        if str(p.get("choosen_position", "")) in str(p.get("player_positions", "")):
            pts = (
                _pts(cl[p["league_id"]], _LEAGUE_THRESH)
                + _pts(cn[p["nationality_id"]], _NATION_THRESH)
                + _pts(cc[p["club_team_id"]], _CLUB_THRESH)
            )
            out.append(min(3, pts))
        else:
            out.append(0)
    return out


def _mean_ovr(squad: list) -> float:
    if not squad:
        return 0.0
    return sum(p["overall"] for p in squad) / len(squad)


def _dim_status(count_after: int, first_threshold: int) -> str:
    """'active' = já pontua; 'building' = caminhando para pontuar; 'none'."""
    if count_after >= first_threshold:
        return "active"
    if count_after >= 2:
        return "building"
    return "none"


def preview_slot(draft: dict, picks: list, slot: int) -> dict:
    """Para o slot atual, calcula a química/OVR do time parcial e, para cada
    uma das 5 cartas, o ganho de química/OVR e quais dimensões (nação/liga/clube)
    geram entrosamento (para destacar no front)."""
    # Time parcial: escolhas já feitas (slots 0..slot-1).
    current = []
    current_slots = []
    for s in range(min(slot, len(draft))):
        pick = picks[s] if s < len(picks) else None
        if pick is None:
            continue
        card = dict(draft[s]["cartas"][pick])
        card["choosen_position"] = draft[s]["posicao"]
        current.append(card)
        current_slots.append(s)

    cur_chem = _strict_chemistry_total(current)
    cur_ovr = _mean_ovr(current)
    # Química individual de cada jogador já escolhido, indexada por slot.
    per_player = _strict_chemistry_per_player(current)
    chem_by_slot = {current_slots[i]: per_player[i] for i in range(len(current))}

    cl = Counter(p["league_id"] for p in current)
    cn = Counter(p["nationality_id"] for p in current)
    cc = Counter(p["club_team_id"] for p in current)

    pos = draft[slot]["posicao"]
    candidates = {}
    for i, raw in enumerate(draft[slot]["cartas"]):
        cand = dict(raw)
        cand["choosen_position"] = pos
        new_squad = current + [cand]
        new_chem = _strict_chemistry_total(new_squad)
        new_ovr = _mean_ovr(new_squad)
        candidates[i] = {
            "new_chem": new_chem,
            "delta_chem": new_chem - cur_chem,
            "new_ovr": round(new_ovr, 2),
            "delta_ovr": round(new_ovr - cur_ovr, 2) if current else 0.0,
            "status": {
                "nationality": _dim_status(cn[cand["nationality_id"]] + 1, _NATION_THRESH[0]),
                "league": _dim_status(cl[cand["league_id"]] + 1, _LEAGUE_THRESH[0]),
                "club": _dim_status(cc[cand["club_team_id"]] + 1, _CLUB_THRESH[0]),
            },
        }

    return {
        "current": {
            "chemistry_total": cur_chem,
            "ovr": round(cur_ovr, 2),
            "n": len(current),
            "chem_by_slot": chem_by_slot,
        },
        "candidates": candidates,
    }


def squad_score(squad_records: list) -> dict:
    """Roda eafc_utils.f + chemistry detalhada num time (lista de dicts)."""
    sdf = pd.DataFrame(squad_records)
    score = f(sdf)
    chem = chemistry(sdf)
    chem_by_name = {d["short_name"]: d["chemistry"] for d in chem["details"]}
    players = []
    for rec in squad_records:
        card = card_to_dict(rec)
        card["choosen_position"] = rec.get("choosen_position")
        card["chemistry"] = chem_by_name.get(rec.get("short_name"), 0)
        players.append(card)
    return {
        "ovr": round(float(score["ovr"]), 2),
        "chemistry": round(float(score["chemistry"]), 2),
        "chemistry_total": chem["total"],
        "final_score": round(float(score["final_score"]), 2),
        "players": players,
    }
