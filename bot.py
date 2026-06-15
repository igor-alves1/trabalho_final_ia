import pandas as pd
import numpy as np
from typing import List
from eafc_utils import fast_f, simulate_rollout
from draft import generate_draft_pack


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
                    

        else:
            raise ValueError(f"Modo '{self.mode}' inválido. Use 'manual', 'greedy_f' ou 'expectimax'.")
