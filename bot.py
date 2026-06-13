import pandas as pd
from collections import Counter
import numpy as np
from typing import List, Set
from eafc_utils import chemistry
from draft import generate_draft_pack

def f(simulated_df: pd.DataFrame) -> float:
    """Calcula a nota final do time simulado."""
    chem = chemistry(simulated_df)
    ovr = simulated_df['overall'].mean()
    return ovr + ((chem['total'] * 1.2) / 11)

def fast_f(squad_list: list) -> float:
    """
    PEDI PARA O GEMINI OTIMIZAR O CÓDIGO:
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
    return mean_ovr + ((total_chemistry * 1.2) / 11)

def simulate_rollout(tentative_squad_list: list, db_cache: dict, current_round: int, remaining_positions: list) -> float:
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
            test_squad = current_sim_squad + [candidate]
            score = fast_f(test_squad)
            
            if score > best_sim_score:
                best_sim_score = score
                best_card = candidate
                
        if best_card is not None:
            current_ids.add(best_card['player_id'])
            current_sim_squad.append(best_card)
            
    return fast_f(current_sim_squad)

def choose(options: pd.DataFrame, mode: str = "greedy", current_squad: pd.DataFrame = None, db: pd.DataFrame = None, current_round: int = 1, remaining_positions: List[str] = None, num_rollouts: int = 10) -> int:
    """
    Isola a lógica de decisão do draft com Expectimax e mecânicas oficiais.
    
    Args:
        options: DataFrame contendo as 5 cartas sorteadas atualmente.
        mode: Define a heurística do bot.
        current_squad: DataFrame com as escolhas já consolidadas no draft.
        db: Base de dados completa com pesos e posições.
        current_round: A rodada da escolha atual (1 a 11).
        remaining_positions: Lista com as strings das posições que faltam nas rodadas seguintes.
        num_rollouts: Quantidade de simulações Monte Carlo por opção (K).
    """
    if mode == "manual":
        while True:
            try:
                escolha = int(input("\nDigite o número da sua escolha (0 a 4): "))
                if 0 <= escolha <= 4:
                    return escolha
                print("Escolha inválida. O número deve estar entre 0 e 4.")
            except ValueError:
                print("Entrada inválida. Por favor, digite um número inteiro.")
    elif mode == "greedy":
        return options['overall'].idxmax()
    elif mode == "expectimax":
        if current_squad is None or db is None or remaining_positions is None:
            raise ValueError("O modo expectimax exige 'current_squad', 'db' e 'remaining_positions'.")
            
        db_cache = {}
        for pos in set(remaining_positions):
            df_pos = db[db['player_positions'].str.contains(pos, na=False)].copy()
            
            weights = df_pos['weight'].values.astype(float)
            probs = weights / weights.sum()
            
            db_cache[pos] = {
                'records': df_pos.to_dict('records'),
                'probs': probs,
                'n_players': len(df_pos)
            }
        
        best_relative_index = -1
        max_expected_value = -float('inf')
        
        current_squad_list = current_squad.to_dict('records')
        
        for i in range(len(options)):
            candidate_dict = options.iloc[i].to_dict()
            tentative_squad_list = current_squad_list + [candidate_dict]
            
            rollout_scores = []
            for _ in range(num_rollouts):
                score = simulate_rollout(tentative_squad_list, db_cache, current_round, remaining_positions)
                rollout_scores.append(score)
                
            expected_value = np.mean(rollout_scores)
            
            if expected_value > max_expected_value:
                max_expected_value = expected_value
                best_relative_index = i
                
        return best_relative_index
    else:
        raise ValueError("Parâmetro 'mode' possui um valor impróprio")