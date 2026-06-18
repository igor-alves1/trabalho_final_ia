"""Baixa em lote as imagens (player_face_url) de todo o pool do draft.

As imagens vão para web/backend/static/faces/{player_id}.png e ficam disponíveis
offline para a interface. O servidor também baixa sob demanda, então este script
é opcional (só acelera o primeiro uso).

Uso: conda run -n venv python web/backend/download_faces.py
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from core import setup_db

FACES_DIR = os.path.join(os.path.dirname(__file__), "static", "faces")
os.makedirs(FACES_DIR, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0"}


def download_one(player_id, url):
    path = os.path.join(FACES_DIR, f"{player_id}.png")
    if os.path.exists(path):
        return "skip"
    if not isinstance(url, str) or not url.startswith("http"):
        return "no-url"
    try:
        r = requests.get(url, timeout=15, headers=HEADERS)
        if r.status_code == 200:
            with open(path, "wb") as fp:
                fp.write(r.content)
            return "ok"
        return f"http-{r.status_code}"
    except requests.RequestException:
        return "error"


def main():
    df = setup_db()
    pairs = list(zip(df["player_id"].astype(int), df["player_face_url"]))
    print(f"Baixando {len(pairs)} imagens para {FACES_DIR} ...")
    counts = {}
    done = 0
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(download_one, pid, url): pid for pid, url in pairs}
        for fut in as_completed(futures):
            res = fut.result()
            counts[res] = counts.get(res, 0) + 1
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(pairs)} ...")
    print("Concluído:", counts)


if __name__ == "__main__":
    main()
