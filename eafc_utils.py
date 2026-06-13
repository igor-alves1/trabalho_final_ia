from collections import Counter
import pandas as pd

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

import pandas as pd
from collections import Counter

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