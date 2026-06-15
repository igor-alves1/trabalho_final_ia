from collections import Counter
import pandas as pd
import numpy as np

def chemistry(df: pd.DataFrame) -> dict:
    """
    Calcula o entrosamento individual e total de um elenco de 11 jogadores.
    
    Args:
        df: DataFrame contendo os jogadores escolhidos.
                   
    Returns:
        Um dicionário com o Entrosamento Total e a lista detalhada de cada jogador.
    """

    count_league = Counter(df['league_id'])
    count_nationality = Counter(df['nationality_id'])
    count_club = Counter(df['club_team_id'])

    def get_league_points(qtd):
        if qtd >= 8: return 3
        if qtd >= 5: return 2
        if qtd >= 3: return 1
        return 0

    def get_nationality_points(qtd):
        if qtd >= 8: return 3
        if qtd >= 5: return 2
        if qtd >= 2: return 1
        return 0

    def get_club_points(qtd):
        if qtd >= 7: return 3
        if qtd >= 4: return 2
        if qtd >= 2: return 1
        return 0
    
    total_chemistry = 0
    player_details = []

    for _, player in df.iterrows():
        player_pts = 0
        
        card_positions = str(player['player_positions'])
        choosen_position = str(player['choosen_position'])

        if choosen_position in card_positions:
            league_pts = get_league_points(count_league[player['league_id']])
            club_pts = get_club_points(count_club[player['club_team_id']])
            nationality_pts = get_nationality_points(count_nationality[player['nationality_id']])

            player_pts = min(3, league_pts + nationality_pts + club_pts)

        total_chemistry += player_pts
        player_details.append({
            'short_name': player['short_name'],
            'chemistry': player_pts
        })
    
    return {
        'total': total_chemistry,
        'details': player_details
    }


def chemistry_fractional(df: pd.DataFrame) -> dict:
    """
    Calcula o entrosamento individual e total de um elenco de 11 jogadores.
    A ideia desta função é tentar recompensar o bot por conta de escolhas que "caminham em direção a um ponto de entrosamento", 
    transformando os platôs de recompensa (inerentes à lógica do Draft do Fifa) em "rampas".
    
    Args:
        df: DataFrame contendo os jogadores escolhidos.
                   
    Returns:
        Um dicionário com o Entrosamento Total e a lista detalhada de cada jogador.
    """

    count_league = Counter(df['league_id'])
    count_nationality = Counter(df['nationality_id'])
    count_club = Counter(df['club_team_id'])

    def get_fractional_points(qtd: int, thresholds: list) -> float:
        t1, t2, t3 = thresholds
        
        if qtd >= t3: 
            return 3.0
        if qtd >= t2: 
            return 2.0 + (qtd - t2) / (t3 - t2)
        if qtd >= t1: 
            return 1.0 + (qtd - t1) / (t2 - t1)

        return qtd / t1

    def get_league_points(qtd):
        return get_fractional_points(qtd, [3, 6, 8])

    def get_nationality_points(qtd):
        return get_fractional_points(qtd, [2, 5, 8])

    def get_club_points(qtd):
        return get_fractional_points(qtd, [2, 4, 7])
    
    total_chemistry = 0.0
    player_details = []

    for _, player in df.iterrows():
        player_pts = 0.0
        
        card_positions = str(player['player_positions'])
        choosen_position = str(player['choosen_position'])

        if choosen_position in card_positions:
            league_pts = get_league_points(count_league[player['league_id']])
            club_pts = get_club_points(count_club[player['club_team_id']])
            nationality_pts = get_nationality_points(count_nationality[player['nationality_id']])

            player_pts = min(3.0, league_pts + nationality_pts + club_pts)

        total_chemistry += player_pts
        
        player_details.append({
            'short_name': player['short_name'],
            'chemistry': player_pts
        })
    
    return {
        'total': round(total_chemistry, 3),
        'details': player_details
    }


def f(simulated_df) -> float:
    """Calcula a nota final do time simulado."""
    chem = chemistry(simulated_df)
    ovr = simulated_df['overall'].mean()
    return ovr + ((chem['total'] * 3.6) / 11)


def fast_f(squad_list: list) -> float:
    """
    Versão ultrarrápida da função objetivo focada apenas nas simulações.
    Recebe uma lista de dicionários nativos do Python ao invés de um DataFrame.
    """
    if not squad_list:
        return 0.0

    count_league = Counter(p['league_id'] for p in squad_list)
    count_nationality = Counter(p['nationality_id'] for p in squad_list)
    count_club = Counter(p['club_team_id'] for p in squad_list)

    total_chemistry = 0.0
    total_ovr = 0.0

    for player in squad_list:
        total_ovr += player['overall']

        posicao_escolhida = player.get('choosen_position', '')
        posicoes_da_carta = player.get('player_positions', '')

        if posicao_escolhida in posicoes_da_carta:
            l_qtd = count_league[player['league_id']]
            n_qtd = count_nationality[player['nationality_id']]
            c_qtd = count_club[player['club_team_id']]

            l_pts = 3.0 if l_qtd >= 8 else (2.0 + (l_qtd - 5)/3 if l_qtd >= 5 else (1.0 + (l_qtd - 3)/2 if l_qtd >= 3 else l_qtd/3))
            n_pts = 3.0 if n_qtd >= 8 else (2.0 + (n_qtd - 5)/3 if n_qtd >= 5 else (1.0 + (n_qtd - 2)/3 if n_qtd >= 2 else n_qtd/2))
            c_pts = 3.0 if c_qtd >= 7 else (2.0 + (c_qtd - 4)/3 if c_qtd >= 4 else (1.0 + (c_qtd - 2)/2 if c_qtd >= 2 else c_qtd/2))

            total_chemistry += min(3.0, l_pts + n_pts + c_pts)

    mean_ovr = total_ovr / len(squad_list)
    return mean_ovr + ((total_chemistry * 3.6) / 11)


def simulate_rollout(tentative_squad_list: list, db_cache: dict, remaining_positions: list) -> float:
    current_sim_squad = tentative_squad_list.copy()
    current_ids = {p['player_id'] for p in current_sim_squad if 'player_id' in p}

    for pos in remaining_positions:
        cache = db_cache[pos]
        records = cache['records']
        probs = cache['probs']
        n_total = cache['n_players']

        n_draws = min(15, n_total)
        drawn_indices = np.random.choice(n_total, size=n_draws, replace=False, p=probs)

        pack_dicts = []
        for idx in drawn_indices:
            player = records[idx]
            if player['player_id'] not in current_ids:
                player_copy = player.copy()
                player_copy['choosen_position'] = pos
                pack_dicts.append(player_copy)
            if len(pack_dicts) == 5:
                break

        if not pack_dicts:
            continue

        best_card = None
        best_sim_score = -float('inf')

        for candidate in pack_dicts:
            score = fast_f(current_sim_squad + [candidate])
            if score > best_sim_score:
                best_sim_score = score
                best_card = candidate

        if best_card is not None:
            current_ids.add(best_card['player_id'])
            current_sim_squad.append(best_card)

    return fast_f(current_sim_squad)