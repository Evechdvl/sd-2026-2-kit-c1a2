"""
Worker: consome a fila e executa a inferencia.

O QUE JA ESTA PRONTO: o laco principal e o carregamento do modelo.
O QUE VOCE PRECISA FAZER (TAREFAS.md, itens 3 e 5):
  - guardar o resultado ao terminar
  - tratar erro com retentativa e fila de descarte (dead-letter)

Rodar:  python -m app.worker
Suba mais de um worker em terminais diferentes e veja a carga se dividir.
"""
import time

from app import fila
from app.modelo import carregar_modelo


def main():
    print("[worker] carregando modelo...")
    modelo = carregar_modelo()
    print("[worker] pronto. aguardando tarefas (Ctrl+C para sair)")

    while True:
        tarefa = fila.proxima_tarefa(timeout=5)
        if tarefa is None:
            continue
        
        tarefa_id = tarefa["id"]
        texto = tarefa["texto"]

        print(f"[worker] processando {tarefa['id']}")
        inicio = time.time()
        try:
            resultado = modelo.prever(tarefa["texto"])
            resultado["status"] = "pronto"
            resultado["tempo_ms"] = round((time.time() - inicio) * 1000, 2)

            fila.guardar_resultado(
                tarefa_id,
                resultado
            )
            print(f"[worker] tarefa {tarefa_id} concluida")

            

        except Exception as erro:
            # Em caso de erro, também salva o erro
            fila.guardar_resultado(
                tarefa_id,
                {
                    "status": "erro",
                    "erro": str(erro)
                }
            )

            print(
                f"[worker] erro na tarefa "
                f"{tarefa_id}: {erro}"
            )
        except Exception as erro:  # noqa: BLE001
            # TAREFA 5: retentativa + dead-letter em vez de so registrar.
            print(f"[worker] ERRO em {tarefa['id']}: {erro}")


if __name__ == "__main__":
    main()
