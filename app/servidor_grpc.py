"""
Interface gRPC do servico de inferencia.

PRE-REQUISITO: gerar os stubs antes de rodar (veja scripts/gerar_stubs).

Os metodos Prever e PreverLote executam o modelo carregado uma vez por
processo.

Rodar:  python -m app.servidor_grpc
"""
from concurrent import futures
import logging
import time
import uuid

import grpc

from app import fila
from app.modelo import carregar_modelo

try:
    import inferencia_pb2
    import inferencia_pb2_grpc
except ImportError:  # pragma: no cover
    raise SystemExit(
        "Stubs nao encontrados. Rode antes:\n"
        "  python -m grpc_tools.protoc -I proto --python_out=. "
        "--grpc_python_out=. proto/inferencia.proto"
    )

logger = logging.getLogger(__name__)
logging.basicConfig(
    level="INFO",
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


class ServicoInferencia(inferencia_pb2_grpc.InferenciaServicer):

    def __init__(self):
        print("[grpc] carregando modelo...")
        self.modelo = carregar_modelo()
        print("[grpc] modelo pronto")

    def _inferir(self, texto):
        inicio = time.perf_counter()
        cacheado = fila.buscar_cache(texto)
        cache_hit = cacheado is not None
        resultado = dict(cacheado) if cache_hit else self.modelo.prever(texto)
        if not cache_hit:
            fila.guardar_cache(texto, resultado)
        tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
        fila.registrar_latencia("grpc", tempo_ms, cache_hit)
        return resultado, cache_hit

    def Prever(self, request, context):
        requisicao_id = str(uuid.uuid4())
        inicio = time.perf_counter()
        r, cache_hit = self._inferir(request.texto)
        tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
        logger.info(
            "requisicao id=%s tamanho_entrada=%d tempo_resposta_ms=%.2f "
            "status=pronto metodo=Prever cache_hit=%s",
            requisicao_id,
            len(request.texto),
            tempo_ms,
            cache_hit,
        )
        return inferencia_pb2.RespostaPrever(
            texto=r["texto"], sentimento=r["sentimento"], confianca=r["confianca"]
        )

    def PreverLote(self, request, context):
        """Executa uma inferência para cada texto recebido no lote."""
        requisicao_id = str(uuid.uuid4())
        inicio = time.perf_counter()
        resultados = []
        cache_hits = 0
        for texto in request.textos:
            resultado, cache_hit = self._inferir(texto)
            resultados.append(resultado)
            cache_hits += int(cache_hit)
        tempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
        tamanho_entrada = sum(len(texto) for texto in request.textos)
        logger.info(
            "requisicao id=%s tamanho_entrada=%d tempo_resposta_ms=%.2f "
            "status=pronto metodo=PreverLote itens=%d cache_hits=%d",
            requisicao_id,
            tamanho_entrada,
            tempo_ms,
            len(request.textos),
            cache_hits,
        )
        return inferencia_pb2.RespostaLote(
            resultados=[
                inferencia_pb2.RespostaPrever(
                    texto=resultado["texto"],
                    sentimento=resultado["sentimento"],
                    confianca=resultado["confianca"],
                )
                for resultado in resultados
            ]
        )


def servir(porta: int = 50051):
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inferencia_pb2_grpc.add_InferenciaServicer_to_server(
        ServicoInferencia(), servidor)
    servidor.add_insecure_port(f"[::]:{porta}")
    servidor.start()
    print(f"[grpc] escutando na porta {porta}")
    servidor.wait_for_termination()


if __name__ == "__main__":
    servir()
