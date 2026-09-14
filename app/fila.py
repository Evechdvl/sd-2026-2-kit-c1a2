"""Fila Redis e armazenamento local de resultados do serviço."""
import hashlib
import json
import os
import uuid
from pathlib import Path

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
FILA_TAREFAS = "tarefas"
FILA_DEAD_LETTER = "tarefas_dead_letter"
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "300"))

RAIZ_DADOS = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[1] / "dados"))
DIR_RESULTADOS = RAIZ_DADOS / "resultados"
ARQUIVO_METRICAS = RAIZ_DADOS / "metricas.json"

_cliente = None


def _preparar_diretorios() -> None:
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)


def cliente():
    global _cliente
    if _cliente is None:
        _cliente = redis.from_url(REDIS_URL, decode_responses=True)
    return _cliente


def _gravar_json(caminho: Path, dados: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    temporario.replace(caminho)


def _ler_json(caminho: Path):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def _arquivo_resultado(tarefa_id: str) -> Path:
    return DIR_RESULTADOS / f"{tarefa_id}.json"


def enfileirar(texto: str) -> str:
    """Grava o estado inicial local e coloca a tarefa na fila Redis."""
    _preparar_diretorios()
    tarefa_id = str(uuid.uuid4())
    _gravar_json(_arquivo_resultado(tarefa_id), {"status": "na_fila"})
    cliente().rpush(FILA_TAREFAS, json.dumps({"id": tarefa_id, "texto": texto}))
    return tarefa_id


def proxima_tarefa(timeout: int = 5):
    """Bloqueia até chegar tarefa. Usado pelo worker."""
    item = cliente().blpop(FILA_TAREFAS, timeout=timeout)
    if item is None:
        return None
    return json.loads(item[1])


def guardar_resultado(tarefa_id: str, resultado: dict) -> None:
    _preparar_diretorios()
    _gravar_json(_arquivo_resultado(tarefa_id), resultado)


def enviar_dead_letter(tarefa: dict, erro: str, tentativas: int) -> None:
    """Mantém a tarefa com falha na fila Redis de descarte."""
    payload = {**tarefa, "erro": erro, "tentativas": tentativas}
    cliente().rpush(FILA_DEAD_LETTER, json.dumps(payload))


def buscar_resultado(tarefa_id: str):
    return _ler_json(_arquivo_resultado(tarefa_id))


def _arquivo_cache(texto: str) -> Path:
    digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    return Path("cache:" + digest)


def buscar_cache(texto: str):
    bruto = cliente().get(str(_arquivo_cache(texto)))
    return json.loads(bruto) if bruto else None


def guardar_cache(texto: str, resultado: dict) -> None:
    cliente().setex(str(_arquivo_cache(texto)), CACHE_TTL, json.dumps(resultado))


def registrar_latencia(servico: str, tempo_ms: float, cache_hit: bool = False) -> None:
    """Atualiza métricas agregadas em dados/metricas.json."""
    _preparar_diretorios()
    metricas = _ler_json(ARQUIVO_METRICAS) or {}
    dados = metricas.setdefault(servico, {"requisicoes": 0, "tempo_total_ms": 0.0, "cache_hits": 0})
    dados["requisicoes"] += 1
    dados["tempo_total_ms"] += tempo_ms
    if cache_hit:
        dados["cache_hits"] += 1
    _gravar_json(ARQUIVO_METRICAS, metricas)


def buscar_metricas():
    metricas = _ler_json(ARQUIVO_METRICAS) or {}
    for dados in metricas.values():
        requisicoes = dados.get("requisicoes", 0)
        dados["latencia_media_ms"] = round(
            dados.get("tempo_total_ms", 0.0) / requisicoes, 2
        ) if requisicoes else 0.0
    return {"servicos": metricas}
