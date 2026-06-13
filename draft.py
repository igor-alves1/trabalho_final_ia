import pandas as pd
from typing import Set

def _apply_round_filters(df: pd.DataFrame, round: int, position: str) -> pd.DataFrame:
    """
    Filtra o DataFrame baseando-se na rodada atual e na posição.
    """
    if round == 1:
        df_filtered = df[(df['overall'] >= 88)]

        if len(df_filtered) < 5:
            df_filtered = df.nlargest(50, 'overall')
        
        return df_filtered
    else:
        return df[df['player_positions'].str.contains(position)]
    
def _remove_duplicated_cards(df: pd.DataFrame, chosen_ids: Set[int]) -> pd.DataFrame:
    """
    Remove do pool as cartas que o jogador já possui no time.
    """
    if not chosen_ids:
        return df
    
    return df[~df['player_id'].isin(chosen_ids)]

def generate_draft_pack(df: pd.DataFrame, round: int, position: str, chosen_ids: Set[int], n_cards: int = 5) -> pd.DataFrame:
    """
    Orquestra a filtragem e realiza o sorteio ponderado de 5 cartas.
    
    Args:
        df: O DataFrame completo com todos os jogadores.
        round: Inteiro indicando a rodada atual do draft (1 a 11).
        position: String com a sigla da posição (ex: 'ST', 'CB').
        chosen_ids: Um Set (conjunto) contendo os IDs dos jogadores já no time.
        n_cards: Quantidade de cartas a sortear (padrão 5).
        
    Returns:
        Um DataFrame contendo exatamente as cartas sorteadas.
    """

    df_available = _remove_duplicated_cards(df, chosen_ids)
    df_filtered = _apply_round_filters(df_available, round, position)

    pack = df_filtered.sample(n=n_cards, replace=False, weights='weight')
    
    return pack
    
