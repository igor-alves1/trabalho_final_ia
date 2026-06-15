import pandas as pd
import numpy as np
from typing import List
from eafc_utils import fast_f, simulate_rollout
from draft import generate_draft_pack
import random

class Bot:
    def __init__(self, mode: str = "greedy", num_rollouts: int = 10):
        self.mode = mode
        self.num_rollouts = num_rollouts

    def choose(self, options: pd.DataFrame, current_squad: pd.DataFrame = None, db: pd.DataFrame = None, current_round: int = 1, remaining_positions: List[str] = None) -> int:
        if self.mode == "manual":
            while True:
                try:
                    escolha = int(input("\nDigite o número da sua escolha (0 a 4): "))
                    if 0 <= escolha <= 4:
                        return escolha
                    print("Escolha inválida. O número deve estar entre 0 e 4.")
                except ValueError:
                    print("Entrada inválida. Por favor, digite um número inteiro.")

        elif self.mode == "greedy_f":
            current_squad_list = current_squad.to_dict('records')
            best_index = -1
            best_position = None
            best_score = -float('inf')
            for i in range(len(options)):
                candidate = options.iloc[i].to_dict()
                card_positions = str(candidate['player_positions']).split(',')
                for pos in remaining_positions:
                    if (any(pos.strip() == p.strip() for p in card_positions)):
                        candidate['choosen_position'] = pos
                        score = fast_f(current_squad_list + [candidate])
                        if score > best_score:
                            best_score = score
                            best_index = i
                            best_position = pos
            return best_index, best_position

        elif self.mode == "expectimax":
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

            best_index = -1
            best_position = None
            max_expected_value = -float('inf')
            current_squad_list = current_squad.to_dict('records')
            for i in range(len(options)):
                candidate_dict = options.iloc[i].to_dict()
                card_positions = str(candidate_dict['player_positions']).split(',')
                for pos in set(remaining_positions):
                    if not any(pos.strip() == p.strip() for p in card_positions):
                        continue
                    candidate_dict['choosen_position'] = pos
                    remaining_after = list(remaining_positions)
                    remaining_after.remove(pos)
                    tentative_squad_list = current_squad_list + [candidate_dict]
                    rollout_scores = [
                        simulate_rollout(tentative_squad_list, db_cache, remaining_after)
                        for _ in range(self.num_rollouts)
                    ]
                    expected_value = np.mean(rollout_scores)
                    if expected_value > max_expected_value:
                        max_expected_value = expected_value
                        best_index = i
                        best_position = pos
            return best_index, best_position
        elif self.mode == "random":
            i = random.randint(0, len(options) - 1)
            candidate = options.iloc[i]
            card_positions = str(candidate['player_positions']).split(',')
            valid_position = [p for p in remaining_positions if any(p.strip() == cp.strip() for cp in card_positions)]
            posicao = random.choice(valid_position)
            return i, posicao 
            
            
                    

        else:
            raise ValueError(f"Modo '{self.mode}' inválido. Use 'manual', 'greedy_f' ou 'expectimax'.")



class SimulatedAnnealingBot:
    def __init__(self, temp_inicial=100, temp_final=0.1, alpha=0.995,iteracoes=5000):
        self.temp_inicial = temp_inicial
        self.temp_final = temp_final
        self.alpha = alpha
        self.iteracoes = iteracoes

    def montar_time(self, db, formacao):
        time_atual = []
        ids_usados = set()
        for pos in formacao:
            pool = db[db['player_positions'].str.contains(pos, na=False)]
            pool = pool[~pool['player_id'].isin(ids_usados)]
            jogador = pool.sample(1, weights='weight').iloc[0].to_dict()
            jogador['choosen_position'] = pos
            time_atual.append(jogador)
            ids_usados.add(jogador['player_id'])
        melhor_time = time_atual.copy()
        melhor_score = fast_f(melhor_time)
        score_atual = melhor_score
        temp = self.temp_inicial
        for _ in range(self.iteracoes):
            idx = random.randint(0, len(time_atual) - 1)
            pos = time_atual[idx]['choosen_position']
            ids_sem_atual = {j['player_id'] for j in time_atual if j != time_atual[idx]}
            pool = db[db['player_positions'].str.contains(pos, na=False)]
            pool = pool[~pool['player_id'].isin(ids_sem_atual)]
            if pool.empty:
                continue
            novo_jogador = pool.sample(1, weights='weight').iloc[0].to_dict()
            novo_jogador['choosen_position'] = pos
            novo_time = time_atual.copy()
            novo_time[idx] = novo_jogador
            novo_score = fast_f(novo_time)
            delta = novo_score - score_atual
            if delta > 0 or random.random() < np.exp(delta / temp):
                time_atual= novo_time
                score_atual = novo_score
                if score_atual > melhor_score:
                    melhor_score = score_atual
                    melhor_time = time_atual.copy()
            temp *= self.alpha
            if temp < self.temp_final:
                break
        
        return pd.DataFrame(melhor_time)