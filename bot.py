import pandas as pd
import numpy as np
from typing import List, Set
from eafc_utils import chemistry
from draft import generate_draft_pack

def f(simulated_df: pd.DataFrame) -> float:
    """Calcula a nota final do time simulado."""
    chem = chemistry(simulated_df)
    ovr = simulated_df['overall'].mean()
    return ovr + ((chem['total'] * 1.2) / 11)

def fast_f(squad_list: list, weights: list = None) -> float:
    if not squad_list:
        return 0.0
    
    if weights is None:
        weights = [1.0, 1.0, 1.0, 1.0]
    
    w_ovr, w_league, w_nat, w_club = weights

    c_league, c_nat, c_club = {}, {}, {}
    total_ovr = 0.0
    
    for p in squad_list:
        l, n, c = p['league_id'], p['nationality_id'], p['club_team_id']
        c_league[l] = c_league.get(l, 0) + 1
        c_nat[n] = c_nat.get(n, 0) + 1
        c_club[c] = c_club.get(c, 0) + 1
        total_ovr += p['overall']

    total_chemistry = 0.0
    
    for player in squad_list:
        pos_escolhida = player.get('choosen_position', '')
        pos_set = player.get('pos_set', set()) 
        
        if pos_escolhida in pos_set:
            l_qtd = c_league[player['league_id']]
            n_qtd = c_nat[player['nationality_id']]
            c_qtd = c_club[player['club_team_id']]
            
            l_pts = 3.0 if l_qtd >= 8 else (2.0 + (l_qtd - 5)/3 if l_qtd >= 5 else (1.0 + (l_qtd - 3)/2 if l_qtd >= 3 else l_qtd/3))
            n_pts = 3.0 if n_qtd >= 8 else (2.0 + (n_qtd - 5)/3 if n_qtd >= 5 else (1.0 + (n_qtd - 2)/3 if n_qtd >= 2 else n_qtd/2))
            c_pts = 3.0 if c_qtd >= 7 else (2.0 + (c_qtd - 4)/3 if c_qtd >= 4 else (1.0 + (c_qtd - 2)/2 if c_qtd >= 2 else c_qtd/2))

            total_chemistry += min(3.0, (l_pts * w_league) + (n_pts * w_nat) + (c_pts * w_club)) 

    mean_ovr = total_ovr / len(squad_list)
    return (mean_ovr * w_ovr) + ((total_chemistry * 1.2) / 11)

def simulate_rollout(tentative_squad_list: list, db_cache: dict, current_round: int, remaining_positions: list, weights: list = None) -> float:
    current_sim_squad = tentative_squad_list.copy()
    current_ids = {p['player_id'] for p in current_sim_squad if 'player_id' in p}
    
    for pos in remaining_positions:
        cache = db_cache[pos]
        records = cache['records']
        probs = cache['probs']
        n_total = cache['n_players']
        
        n_draws = min(15, n_total)
        # OTIMIZAÇÃO CRÍTICA: replace=True evita que o numpy faça sorting logarítmico
        drawn_indices = np.random.choice(n_total, size=n_draws, replace=True, p=probs)
        
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
            score = fast_f(test_squad, weights=weights)
            
            if score > best_sim_score:
                best_sim_score = score
                best_card = candidate
                
        if best_card is not None:
            current_ids.add(best_card['player_id'])
            current_sim_squad.append(best_card)
            
    return fast_f(current_sim_squad, weights=weights)


def choose(options: pd.DataFrame, mode: str = "greedy", current_squad: pd.DataFrame = None, db: pd.DataFrame = None, current_round: int = 1, remaining_positions: List[str] = None, num_rollouts: int = 10, weights: list = None) -> int:
    if mode == "greedy":
        return options['overall'].idxmax()
    elif mode == "expectimax":
        if current_squad is None or db is None or remaining_positions is None:
            raise ValueError("O modo expectimax exige 'current_squad', 'db' e 'remaining_positions'.")
            
        db_cache = {}
        for pos in set(remaining_positions):
            df_pos = db[db['player_positions'].str.contains(pos, na=False)].copy()
            
            db_weights = df_pos['weight'].values.astype(float)
            probs = db_weights / db_weights.sum()
            
            records_list = df_pos.to_dict('records')
            for rec in records_list:
                rec['pos_set'] = set(p.strip() for p in str(rec['player_positions']).split(','))
            
            db_cache[pos] = {
                'records': records_list,
                'probs': probs,
                'n_players': len(df_pos)
            }
        
        best_relative_index = -1
        max_expected_value = -float('inf')
        
        current_squad_list = current_squad.to_dict('records')
        
        for i in range(len(options)):
            candidate_dict = options.iloc[i].to_dict()
            candidate_dict['pos_set'] = set(p.strip() for p in str(candidate_dict['player_positions']).split(','))
            
            tentative_squad_list = current_squad_list + [candidate_dict]
            
            rollout_scores = []
            for _ in range(num_rollouts):
                score = simulate_rollout(tentative_squad_list, db_cache, current_round, remaining_positions, weights=weights)
                rollout_scores.append(score)
                
            expected_value = np.mean(rollout_scores)
            
            if expected_value > max_expected_value:
                max_expected_value = expected_value
                best_relative_index = i
                
        return best_relative_index
    else:
        raise ValueError("Parâmetro 'mode' possui um valor impróprio")
    
def run_single_draft(df_draft: pd.DataFrame, weights: list, position_priorities: list = None, num_rollouts: int = 100, verbose: bool = False) -> float:
    formacao_433 = ['ST', 'LW', 'RW', 'CM', 'CM', 'CM', 'LB', 'CB', 'CB', 'RB', 'GK']
    meu_time = []
    ids_escolhidos = set()

    if verbose:
        print("===========================================\n INICIANDO SIMULADOR DE DRAFT EA FC \n===========================================")
    
    # -------------------------------------------------------------
    # FASE 1: ESCOLHA DO CAPITÃO 
    # -------------------------------------------------------------
    if verbose:
        print("\n--- RODADA 0 | ESCOLHENDO O CAPITÃO DO TIME ---")
    
    pacote_capitao = generate_draft_pack(df_draft, round=0, position='ANY', chosen_ids=ids_escolhidos)
    opcoes_capitao = pacote_capitao.reset_index(drop=True)

    opcoes_capitao['choosen_position'] = opcoes_capitao['player_positions'].apply(lambda x: str(x).split(',')[0].strip())

    df_meu_time = pd.DataFrame(meu_time) if meu_time else pd.DataFrame(columns=df_draft.columns)

    indice_capitao = choose(
        options=opcoes_capitao,
        mode="expectimax",
        current_squad=df_meu_time,
        db=df_draft,
        current_round=0,
        remaining_positions=formacao_433,
        num_rollouts=num_rollouts,
        weights=weights
    )

    capitao_escolhido = opcoes_capitao.iloc[indice_capitao]
    posicao_do_capitao = capitao_escolhido['choosen_position']
    
    meu_time.append(capitao_escolhido)
    ids_escolhidos.add(capitao_escolhido['player_id'])

    if posicao_do_capitao in formacao_433:
        formacao_433.remove(posicao_do_capitao)
    else:
        mapeamento = {'CF': 'ST', 'CAM': 'CM', 'CDM': 'CM', 'LWB': 'LB', 'RWB': 'RB', 'LM': 'LW', 'RM': 'RW'}
        posicao_adaptada = mapeamento.get(posicao_do_capitao, 'ST') 
        if posicao_adaptada in formacao_433:
            formacao_433.remove(posicao_adaptada)
            capitao_escolhido['choosen_position'] = posicao_adaptada

    if verbose:
        print(f">>> CAPITÃO ESCOLHIDO: {capitao_escolhido['short_name']} ({posicao_do_capitao} | OVR {capitao_escolhido['overall']})")

    if position_priorities is not None and len(position_priorities) == 11:
        formacao_original = ['ST', 'LW', 'RW', 'CM', 'CM', 'CM', 'LB', 'CB', 'CB', 'RB', 'GK']
        mapa_prioridades = {i: position_priorities[i] for i in range(11)}
        
        posicoes_com_indice = []
        temp_prioridades = list(position_priorities)
        
        for pos in formacao_433:
            idx = formacao_original.index(pos)
            posicoes_com_indice.append((pos, temp_prioridades[idx]))
            formacao_original[idx] = 'USADO' 
            
        posicoes_com_indice.sort(key=lambda x: x[1], reverse=True)
        formacao_433 = [item[0] for item in posicoes_com_indice]

        if verbose:
            print(f"\n[!] Nova ordem de draft otimizada pelo DNA: {formacao_433}")

    # -------------------------------------------------------------
    # FASE 2: AS 10 RODADAS RESTANTES DO DRAFT
    # -------------------------------------------------------------
    for rodada in range(1, 11): 
        posicao_alvo = formacao_433[0]
        
        if verbose:
            print(f"\n--- RODADA {rodada}/10 | Buscando: {posicao_alvo} ---")
        
        pacote = generate_draft_pack(df_draft, rodada, posicao_alvo, ids_escolhidos)
        opcoes = pacote.reset_index(drop=True)
        opcoes['choosen_position'] = posicao_alvo
        
        if verbose:
            print(opcoes[['short_name', 'overall', 'club_name', 'league_name', 'nationality_name']])
        
        df_meu_time = pd.DataFrame(meu_time)
        
        proximas_posicoes = formacao_433[1:]
        
        indice_escolhido = choose(
            options=opcoes,
            mode="expectimax",
            current_squad=df_meu_time,
            db=df_draft,
            current_round=rodada,
            remaining_positions=proximas_posicoes,
            num_rollouts=num_rollouts,
            weights=weights
        )
        
        carta_escolhida = opcoes.iloc[indice_escolhido]
        meu_time.append(carta_escolhida)
        ids_escolhidos.add(carta_escolhida['player_id'])
        
        formacao_433.pop(0)
        
        if verbose:
            print(f">>> ESCOLHA DO BOT: {carta_escolhida['short_name']} (OVR {carta_escolhida['overall']})")

    # -------------------------------------------------------------
    # FASE 3: CONCLUSÃO E AVALIAÇÃO FINAL
    # -------------------------------------------------------------
    df_final = pd.DataFrame(meu_time)

    if verbose:
        print("\n===========================================")
        print(" DRAFT CONCLUÍDO! SEU ELENCO FINAL: ")
        print("===========================================")
        print(df_final[['short_name', 'overall', 'choosen_position', 'league_name', 'nationality_name']])

    nota_final_real = f(df_final)

    if verbose:
        print(f"\nNOTA FINAL DO TIME: {nota_final_real:.2f}")
        
    return nota_final_real