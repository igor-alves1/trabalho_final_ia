"""Backend HTTP leve (stdlib) para a interface web do Draft AI.

Sem dependências além de pandas/numpy/requests (já presentes no ambiente).
Roda: `conda run -n venv python web/backend/server.py`  (porta 8000)
"""
import json
import os
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

from core import Bot, FORMACAO, setup_db, draft_to_payload, squad_score, preview_slot

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
FACES_DIR = os.path.join(os.path.dirname(__file__), "static", "faces")
os.makedirs(FACES_DIR, exist_ok=True)

print("Carregando banco de dados de jogadores...")
DB = setup_db()
print(f"  {len(DB)} jogadores no pool (overall >= 75).")

# Armazena drafts gerados em memória: id -> {"draft": draft, "df": DB}
DRAFTS = {}
DRAFTS_LOCK = threading.Lock()

# Cache de player_id -> face_url para o endpoint de imagens.
FACE_URLS = dict(zip(DB["player_id"].astype(int), DB["player_face_url"]))


class Handler(BaseHTTPRequestHandler):
    server_version = "DraftAI/1.0"

    # ---- helpers -------------------------------------------------------
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def log_message(self, fmt, *args):  # menos ruído no console
        pass

    # ---- routing -------------------------------------------------------
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/health":
            return self._json({"ok": True, "players": len(DB)})

        m = re.match(r"^/faces/(\d+)\.png$", self.path)
        if m:
            return self._serve_face(int(m.group(1)))

        self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/api/draft/new":
            return self._new_draft()

        m = re.match(r"^/api/draft/([\w-]+)/preview$", self.path)
        if m:
            return self._preview(m.group(1))

        m = re.match(r"^/api/draft/([\w-]+)/evaluate$", self.path)
        if m:
            return self._evaluate(m.group(1))

        m = re.match(r"^/api/draft/([\w-]+)/ai$", self.path)
        if m:
            return self._ai_play(m.group(1))

        self._json({"error": "not found"}, 404)

    # ---- endpoints -----------------------------------------------------
    def _new_draft(self):
        drafts = Bot.generate_drafts(DB, n=1)
        draft = drafts[0]
        draft_id = uuid.uuid4().hex[:12]
        with DRAFTS_LOCK:
            DRAFTS[draft_id] = draft
        self._json({
            "draft_id": draft_id,
            "formation": FORMACAO,
            "slots": draft_to_payload(draft),
        })

    def _preview(self, draft_id):
        with DRAFTS_LOCK:
            draft = DRAFTS.get(draft_id)
        if draft is None:
            return self._json({"error": "draft expirado"}, 404)
        body = self._read_body()
        slot = int(body.get("slot", 0))
        picks = body.get("picks", [])
        if not (0 <= slot < len(draft)):
            return self._json({"error": "slot inválido"}, 400)
        self._json(preview_slot(draft, picks, slot))

    def _evaluate(self, draft_id):
        with DRAFTS_LOCK:
            draft = DRAFTS.get(draft_id)
        if draft is None:
            return self._json({"error": "draft expirado"}, 404)
        body = self._read_body()
        picks = body.get("picks", [])  # lista de índices 0-4, um por slot
        if len(picks) != len(draft):
            return self._json({"error": "número de escolhas inválido"}, 400)
        squad = []
        for slot_idx, pick in enumerate(picks):
            slot = draft[slot_idx]
            if pick is None or not (0 <= pick < len(slot["cartas"])):
                return self._json({"error": f"escolha inválida no slot {slot_idx}"}, 400)
            card = dict(slot["cartas"][pick])
            card["choosen_position"] = slot["posicao"]
            squad.append(card)
        self._json(squad_score(squad))

    def _ai_play(self, draft_id):
        with DRAFTS_LOCK:
            draft = DRAFTS.get(draft_id)
        if draft is None:
            return self._json({"error": "draft expirado"}, 404)
        body = self._read_body()
        mode = body.get("mode", "greedy_f")
        rollouts = int(body.get("num_rollouts", 100))
        valid = {"random", "greedy_ovr", "greedy_f", "expectimax"}
        if mode not in valid:
            return self._json({"error": f"modo inválido: {mode}"}, 400)
        bot = Bot(mode=mode, num_rollouts=rollouts)
        squad = bot.play_draft(draft, DB)
        result = squad_score(squad)
        result["mode"] = mode
        result["num_rollouts"] = rollouts
        self._json(result)

    def _serve_face(self, player_id):
        path = os.path.join(FACES_DIR, f"{player_id}.png")
        if not os.path.exists(path):
            url = FACE_URLS.get(player_id)
            if not url or not isinstance(url, str):
                return self._json({"error": "sem imagem"}, 404)
            try:
                r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    with open(path, "wb") as fp:
                        fp.write(r.content)
                else:
                    return self._redirect(url)
            except requests.RequestException:
                return self._redirect(url)
        try:
            with open(path, "rb") as fp:
                data = fp.read()
        except OSError:
            return self._json({"error": "erro ao ler imagem"}, 500)
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "public, max-age=86400")
        self._cors()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self._cors()
        self.end_headers()


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Backend rodando em http://localhost:{PORT}")
    print("Endpoints: POST /api/draft/new | /api/draft/<id>/evaluate | /api/draft/<id>/ai")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
