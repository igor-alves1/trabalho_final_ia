import json
import os
import time
import pandas as pd
import numpy as np
from bot import Bot, SimulatedAnnealingBot
from draft import generate_draft_pack
from eafc_utils import f

FORMACAO = ['ST', 'LW', 'RW', 'CM', 'CM', 'CM', 'LB', 'CB', 'CB', 'RB', 'GK']
N_RUNS = 100
RESULTS_DIR = "results"


def setup_db():
    df = pd.read_csv("data/FC26_20250921.csv", low_memory=False)
    df.drop(columns=["fifa_version", "fifa_update", "fifa_update_date", "player_face_url", "work_rate", "player_url"], inplace=True)
    df_draft = df[df['overall'] >= 75].copy()
    faixas = [
        (df_draft['overall'] >= 87),
        (df_draft['overall'] >= 84) & (df_draft['overall'] < 87),
        (df_draft['overall'] >= 80) & (df_draft['overall'] < 84),
        (df_draft['overall'] < 80)
    ]
    pesos = [5, 15, 40, 80]
    df_draft['weight'] = np.select(faixas, pesos, default=0)
    return df_draft


def run_draft(bot, df_draft):
    remaining_positions = list(FORMACAO)
    meu_time = []
    ids_escolhidos = set()

    for rodada in range(1, len(FORMACAO) + 1):
        pacote = generate_draft_pack(df_draft, rodada, remaining_positions, ids_escolhidos)
        opcoes = pacote.reset_index(drop=True)

        df_meu_time = pd.DataFrame(meu_time) if meu_time else pd.DataFrame(columns=df_draft.columns)

        indice_escolhido, posicao_escolhida = bot.choose(
            options=opcoes,
            current_squad=df_meu_time,
            db=df_draft,
            current_round=rodada,
            remaining_positions=remaining_positions
        )

        carta_escolhida = opcoes.iloc[indice_escolhido].copy()
        carta_escolhida['choosen_position'] = posicao_escolhida
        remaining_positions.remove(posicao_escolhida)
        meu_time.append(carta_escolhida)
        ids_escolhidos.add(carta_escolhida['player_id'])

    return f(pd.DataFrame(meu_time))


def run_experiment(nome, bot, df_draft):
    scores = []
    tempos = []
    for i in range(N_RUNS):
        if i % 10 == 0:
            print(f"  [{nome}] {i+1}/{N_RUNS}...")
        inicio = time.time()
        score = run_draft(bot, df_draft)
        tempos.append(time.time() - inicio)
        scores.append(score)
    return scores, tempos


def save_results(nome, scores, tempos):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    filename = nome.lower().replace(" ", "_") + ".json"
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, "w") as fp:
        json.dump({"scores": scores, "tempos": tempos}, fp)


def print_results(nome, scores):
    print(f"\n\nResultado da execução:")
    print(f" {nome}")
    print(f"  Média:  {np.mean(scores):.2f}")
    print(f"  Desvio: {np.std(scores):.2f}")
    print(f"  Mín:    {np.min(scores):.2f}")
    print(f"  Máx:    {np.max(scores):.2f}")


if __name__ == "__main__":
    print("Carregando banco de dados...")
    df_draft = setup_db()

    experimentos = [
        ("Random",              Bot(mode="random")),
        ("Greedy_f",            Bot(mode="greedy_f")),
        ("Expectimax 500",      Bot(mode="expectimax", num_rollouts=500)),
        ("Expectimax 1000",     Bot(mode="expectimax", num_rollouts=1000)),
        ("Expectimax 2000",     Bot(mode="expectimax", num_rollouts=2000)),
    ]

    resultados = {}
    for nome, bot in experimentos:
        print(f"\nRodando: {nome}")
        scores, tempos = run_experiment(nome, bot, df_draft)
        resultados[nome] = scores
        print_results(nome, scores)
        save_results(nome, scores, tempos)

    print("\n\n---------RESUMO FINAL----------")
    print(f"{'Algoritmo':<25} {'Média':>8} {'Desvio':>8} {'Mín':>8} {'Máx':>8}")
    for nome, scores in resultados.items():
        print(f"{nome:<25} {np.mean(scores):>8.2f} {np.std(scores):>8.2f} {np.min(scores):>8.2f} {np.max(scores):>8.2f}")
