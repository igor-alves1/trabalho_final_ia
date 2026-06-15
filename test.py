import json
import os
import time
import pandas as pd
import numpy as np
from bot import Bot, SimulatedAnnealingBot
from eafc_utils import f

N_RUNS = 100
RESULTS_DIR = "results"
DRAFTS_PATH = "data/drafts.json"


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


def _json_safe(o):
    if isinstance(o, np.integer):  return int(o)
    if isinstance(o, np.floating): return float(o)
    raise TypeError(f"não serializável: {type(o)}")


def save_drafts(drafts):
    with open(DRAFTS_PATH, "w") as fp:
        json.dump(drafts, fp, default=_json_safe)


def load_drafts():
    with open(DRAFTS_PATH) as fp:
        raw = json.load(fp)
    return {int(draft_id): {int(slot): v for slot, v in draft.items()}
            for draft_id, draft in raw.items()}


def run_experiment(nome, bot, df_draft, drafts):
    scores = {}
    tempos = []
    for i, (draft_id, draft) in enumerate(sorted(drafts.items())):
        if i % 10 == 0:
            print(f"  [{nome}] {i+1}/{N_RUNS}...")
        inicio = time.time()
        squad = bot.play_draft(draft, df_draft)
        scores[draft_id + 1] = f(pd.DataFrame(squad))
        tempos.append(time.time() - inicio)
    return scores, tempos


def save_results(nome, scores, tempos):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    filename = nome.lower().replace(" ", "_") + ".json"
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, "w") as fp:
        json.dump({"scores": scores, "tempos": tempos}, fp, default=_json_safe, indent=4)


def print_results(nome, scores):
    final_scores = [v['final_score'] for v in scores.values()]
    print(f"\n\nResultado da execução:")
    print(f" {nome}")
    print(f"  Média:  {np.mean(final_scores):.2f}")
    print(f"  Desvio: {np.std(final_scores):.2f}")
    print(f"  Mín:    {np.min(final_scores):.2f}")
    print(f"  Máx:    {np.max(final_scores):.2f}")


if __name__ == "__main__":
    print("Carregando banco de dados...")
    df_draft = setup_db()

    if os.path.exists(DRAFTS_PATH):
        print("Carregando drafts salvos...")
        drafts = load_drafts()
    else:
        print(f"Gerando {N_RUNS} drafts...")
        drafts = Bot.generate_drafts(df_draft, n=N_RUNS)
        save_drafts(drafts)
        print("Drafts salvos em", DRAFTS_PATH)

    experimentos = [
        ("Random",              Bot(mode="random")),
        ("Greedy_ovr",          Bot(mode="greedy_ovr")),
        ("Greedy_f",            Bot(mode="greedy_f")),
        ("Expectimax 500",      Bot(mode="expectimax", num_rollouts=500)),
        ("Expectimax 1000",     Bot(mode="expectimax", num_rollouts=1000)),
        ("Expectimax 2000",     Bot(mode="expectimax", num_rollouts=2000)),
    ]

    resultados = {}
    for nome, bot in experimentos:
        print(f"\nRodando: {nome}")
        scores, tempos = run_experiment(nome, bot, df_draft, drafts)
        resultados[nome] = scores
        print_results(nome, scores)
        save_results(nome, scores, tempos)

    print("\n\n---------RESUMO FINAL----------")
    print(f"{'Algoritmo':<25} {'Média':>8} {'Desvio':>8} {'Mín':>8} {'Máx':>8}")
    for nome, scores in resultados.items():
        fs = [v['final_score'] for v in scores.values()]
        print(f"{nome:<25} {np.mean(fs):>8.2f} {np.std(fs):>8.2f} {np.min(fs):>8.2f} {np.max(fs):>8.2f}")
