"""
Interface REST do servico de inferencia.

O QUE JA ESTA PRONTO:
  - carregamento do modelo UMA vez, na subida (nao a cada requisicao)
  - rota sincrona /predict-sync, usada no laboratorio da Aula 6

Rotas disponíveis:
  - POST /predict  -> colocar na fila e devolver o id
  - GET  /resultado/{id} -> devolver o resultado quando estiver pronto
  - POST /predict-batch -> inferência síncrona de vários textos
  - GET /metricas -> latência média e acertos de cache

Rodar:  uvicorn app.api_rest:app --reload --port 8000
Docs:   http://localhost:8000/docs
"""
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import fila
from app.modelo import carregar_modelo

app = FastAPI(title="Servico de Inferencia - C1.A2", version="0.1.0")
logger = logging.getLogger(__name__)
logging.basicConfig(
    level="INFO",
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

modelo = None


class Entrada(BaseModel):
    texto: str


class EntradaLote(BaseModel):
    textos: list[str]


def _inferir(texto: str) -> dict:
    """Executa uma inferência usando o cache quando disponível."""
    inicio = time.perf_counter()
    cacheado = fila.buscar_cache(texto)
    cache_hit = cacheado is not None
    resultado = dict(cacheado) if cache_hit else modelo.prever(texto)
    if not cache_hit:
        fila.guardar_cache(texto, resultado)
    tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
    fila.registrar_latencia("rest", tempo_ms, cache_hit)
    resultado["tempo_ms"] = tempo_ms
    resultado["cache_hit"] = cache_hit
    return resultado


@app.on_event("startup")
def _subir():
    """Carrega o modelo UMA vez. Este e o ponto-chave da Aula 6."""
    global modelo
    inicio = time.time()
    modelo = carregar_modelo()
    print(f"[startup] modelo carregado em {time.time() - inicio:.3f}s")


@app.get("/saude")
def saude():
    inicio = time.perf_counter()
    requisicao_id = str(uuid.uuid4())
    resposta = {"status": "ok", "modelo_carregado": modelo is not None}
    logger.info(
        "requisicao id=%s tamanho_entrada=0 tempo_resposta_ms=%.2f "
        "status=pronto rota=/saude",
        requisicao_id,
        (time.perf_counter() - inicio) * 1000,
    )
    return resposta


@app.post("/predict-sync")
def predict_sync(entrada: Entrada):
    """Inferencia SINCRONA: o cliente espera a resposta. Lab da Aula 6."""
    if not entrada.texto.strip():
        raise HTTPException(status_code=400, detail="texto vazio")
    requisicao_id = str(uuid.uuid4())
    inicio = time.perf_counter()
    resultado = _inferir(entrada.texto)
    tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
    logger.info(
        "requisicao id=%s tamanho_entrada=%d tempo_resposta_ms=%.2f "
        "status=pronto rota=/predict-sync",
        requisicao_id,
        len(entrada.texto),
        tempo_ms,
    )
    return resultado


@app.post("/predict-batch")
def predict_batch(entrada: EntradaLote):
    """Executa inferência síncrona para vários textos pela interface REST."""
    if not entrada.textos or any(not texto.strip() for texto in entrada.textos):
        raise HTTPException(status_code=400, detail="a lista deve conter textos não vazios")

    requisicao_id = str(uuid.uuid4())
    inicio = time.perf_counter()
    resultados = [_inferir(texto) for texto in entrada.textos]
    tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
    logger.info(
        "requisicao id=%s tamanho_entrada=%d tempo_resposta_ms=%.2f "
        "status=pronto rota=/predict-batch itens=%d",
        requisicao_id,
        sum(len(texto) for texto in entrada.textos),
        tempo_ms,
        len(entrada.textos),
    )
    return {
        "resultados": resultados,
        "quantidade": len(resultados),
        "tempo_ms": tempo_ms,
    }


@app.get("/metricas")
def metricas():
    """Expõe a latência média e os acertos de cache acumulados no Redis."""
    inicio = time.perf_counter()
    resposta = fila.buscar_metricas()
    logger.info(
        "requisicao id=%s tamanho_entrada=0 tempo_resposta_ms=%.2f "
        "status=pronto rota=/metricas",
        str(uuid.uuid4()),
        (time.perf_counter() - inicio) * 1000,
    )
    return resposta


@app.post("/predict", status_code=202)
def predict(entrada: Entrada):
    """Enfileira a inferência e responde sem aguardar o worker."""
    if not entrada.texto.strip():
        raise HTTPException(status_code=400, detail="texto vazio")

    inicio = time.perf_counter()
    tarefa_id = fila.enfileirar(entrada.texto)
    tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
    logger.info(
        "requisicao id=%s tamanho_entrada=%d tempo_resposta_ms=%.2f "
        "status=na_fila rota=/predict",
        tarefa_id,
        len(entrada.texto),
        tempo_ms,
    )
    return {"id": tarefa_id}


@app.get("/resultado/{tarefa_id}")
def resultado(tarefa_id: str):
    """Consulta o resultado ou responde 404 quando o id não existe."""
    inicio = time.perf_counter()
    resposta = fila.buscar_resultado(tarefa_id)
    tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
    if resposta is None:
        logger.info(
            "requisicao id=%s tamanho_entrada=0 tempo_resposta_ms=%.2f "
            "status=nao_encontrado rota=/resultado",
            tarefa_id,
            tempo_ms,
        )
        raise HTTPException(status_code=404, detail="id não encontrado")

    logger.info(
        "requisicao id=%s tamanho_entrada=0 tempo_resposta_ms=%.2f "
        "status=%s rota=/resultado",
        tarefa_id,
        tempo_ms,
        resposta.get("status", "desconhecido"),
    )
    return resposta
