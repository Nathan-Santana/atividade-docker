import json
import os
import threading
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
DATA_FILE = os.path.join(DATA_DIR, "notas.json")

app = FastAPI()
_lock = threading.Lock()


class Nota(BaseModel):
    texto: str


def _ler_notas():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _gravar_notas(notas):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(notas, f, ensure_ascii=False, indent=2)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/notas", status_code=201)
def criar_nota(nota: Nota):
    with _lock:
        notas = _ler_notas()
        nova_nota = {
            "texto": nota.texto,
            "data_hora": datetime.now().isoformat(),
        }
        notas.append(nova_nota)
        _gravar_notas(notas)
    return nova_nota


@app.get("/notas")
def listar_notas():
    with _lock:
        return _ler_notas()
