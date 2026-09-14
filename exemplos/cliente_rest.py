"""Cliente REST de exemplo. Rode com o servico no ar."""
import sys
import time
import os

import requests

BASE = os.getenv("REST_URL", "http://localhost:8001")


def sincrono(texto):
    r = requests.post(f"{BASE}/predict-sync", json={"texto": texto}, timeout=10)
    r.raise_for_status()
    print("sincrono:", r.json())


def assincrono(texto):
    """Submete a tarefa e aguarda o resultado processado pelo worker."""
    r = requests.post(f"{BASE}/predict", json={"texto": texto}, timeout=10)
    r.raise_for_status()
    tarefa_id = r.json()["id"]
    print("id da tarefa:", tarefa_id)

    for _ in range(30):
        time.sleep(0.5)
        r = requests.get(f"{BASE}/resultado/{tarefa_id}", timeout=10)
        dados = r.json()
        if dados.get("status") == "pronto":
            print("assincrono:", dados)
            return
    print("tempo esgotado esperando o resultado")


if __name__ == "__main__":
    texto = " ".join(sys.argv[1:]) or "o atendimento foi muito bom"
    sincrono(texto)
    try:
        assincrono(texto)
    except Exception as e:  # noqa: BLE001
        print("erro no fluxo assincrono:", e)
