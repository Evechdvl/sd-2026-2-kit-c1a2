"""
Worker: consome a fila e executa a inferencia.

O worker grava o resultado ao terminar e trata falhas com retentativa e fila
de descarte (dead-letter).

Rodar:  python -m app.worker
Suba mais de um worker em terminais diferentes e veja a carga se dividir.
"""
import logging
import os
import time

from app import fila
from app.modelo import carregar_modelo

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
MAX_TENTATIVAS = 3
INTERVALO_RETRY = float(os.getenv("WORKER_RETRY_DELAY", "1"))
WORKER_ID = os.getenv("WORKER_ID", f"worker-{os.getpid()}")


def processar_tarefa(tarefa: dict, modelo) -> None:
    """Processa uma tarefa, repetindo falhas e usando dead-letter no limite."""
    tarefa_id = tarefa["id"]
    texto = tarefa["texto"]
    inicio = time.perf_counter()
    ultimo_erro = None

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            inicio_inferencia = time.perf_counter()
            cacheado = fila.buscar_cache(texto)
            cache_hit = cacheado is not None
            resultado = dict(cacheado) if cache_hit else modelo.prever(texto)
            tempo_inferencia_ms = round(
                (time.perf_counter() - inicio_inferencia) * 1000, 2
            )
            if not cache_hit:
                fila.guardar_cache(texto, resultado)
            fila.registrar_latencia("worker", tempo_inferencia_ms, cache_hit)
            resultado["status"] = "pronto"
            resultado["tempo_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
            resultado["cache_hit"] = cache_hit
            fila.guardar_resultado(tarefa_id, resultado)
            logger.info(
                "worker_id=%s requisicao id=%s tamanho_entrada=%d "
                "tempo_resposta_ms=%.2f status=pronto tentativa=%d cache_hit=%s",
                WORKER_ID,
                tarefa_id,
                len(texto),
                resultado["tempo_ms"],
                tentativa,
                cache_hit,
            )
            return
        except Exception as erro:  # noqa: BLE001
            ultimo_erro = erro
            if tentativa < MAX_TENTATIVAS:
                logger.warning(
                    "falha id=%s tentativa=%d/%d erro=%s",
                    tarefa_id,
                    tentativa,
                    MAX_TENTATIVAS,
                    erro,
                )
                time.sleep(INTERVALO_RETRY)

    tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
    mensagem = str(ultimo_erro)
    fila.enviar_dead_letter(tarefa, mensagem, MAX_TENTATIVAS)
    fila.guardar_resultado(
        tarefa_id,
        {
            "status": "erro",
            "erro": mensagem,
            "tentativas": MAX_TENTATIVAS,
            "tempo_ms": tempo_ms,
        },
    )
    logger.error(
        "worker_id=%s requisicao id=%s tamanho_entrada=%d tempo_resposta_ms=%.2f "
        "status=dead_letter tentativas=%d erro=%s",
        WORKER_ID,
        tarefa_id,
        len(texto),
        tempo_ms,
        MAX_TENTATIVAS,
        mensagem,
    )


def main():
    print("[worker] carregando modelo...")
    modelo = carregar_modelo()
    print("[worker] pronto. aguardando tarefas (Ctrl+C para sair)")

    while True:
        tarefa = fila.proxima_tarefa(timeout=5)
        if tarefa is None:
            continue

        logger.info("worker_id=%s processando tarefa id=%s", WORKER_ID, tarefa["id"])
        processar_tarefa(tarefa, modelo)


if __name__ == "__main__":
    main()
