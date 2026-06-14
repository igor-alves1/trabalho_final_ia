import pandas as pd
from typing import Set

def _apply_round_filters(df: pd.DataFrame, round: int, position: str) -> pd.DataFrame:
    if round == 0 or position == 'ANY':
        df_filtered = df[(df['overall'] >= 88)]

        if len(df_filtered) < 5:
            df_filtered = df.nlargest(50, 'overall')
        
        return df_filtered
    else:
        return df[df['player_positions'].str.contains(position, na=False)]
    
def _remove_duplicated_cards(df: pd.DataFrame, chosen_ids: Set[int]) -> pd.DataFrame:
    if not chosen_ids:
        return df
    
    return df[~df['player_id'].isin(chosen_ids)]

def generate_draft_pack(df: pd.DataFrame, round: int, position: str, chosen_ids: Set[int], n_cards: int = 5) -> pd.DataFrame:
    df_available = _remove_duplicated_cards(df, chosen_ids)
    df_filtered = _apply_round_filters(df_available, round, position)

    qtd_sorteio = min(n_cards, len(df_filtered))
    
    pack = df_filtered.sample(n=qtd_sorteio, replace=False, weights='weight')
    
    return pack