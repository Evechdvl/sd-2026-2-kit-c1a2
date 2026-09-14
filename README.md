# Serviço de Inferência Distribuído

Projeto C1.A2 de Sistemas Distribuídos e Computação em Nuvem.

O sistema recebe textos, executa um classificador local de sentimento e disponibiliza REST e gRPC. O modelo é carregado uma vez por processo.

## Arquitetura

```text
Cliente REST ──> FastAPI ──> Redis: fila tarefas ──> Worker ──> Modelo local
      │                         Redis: cache          │
      │                                               └─ retry/dead-letter
      └── consulta ──> dados/resultados/<id>.json

Cliente gRPC ────────────────────────────────> Servidor gRPC ──> Modelo local
```

- Redis é usado para a fila `tarefas`, a fila `tarefas_dead_letter` e o cache.
- Resultados processados são gravados em `dados/resultados/`.
- Métricas são gravadas em `dados/metricas.json`.
- O cache expira por padrão após 300 segundos.

## Requisitos

- Python 3.10 ou superior
- Docker e Docker Compose

## Instalação

```bash
git clone https://github.com/Evechdvl/sd-2026-2-kit-c1a2.git
cd sd-2026-2-kit-c1a2

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Se a criação do ambiente virtual informar que `ensurepip` não está disponível:

```bash
sudo apt update
sudo apt install -y python3.12-venv
```

Gere os stubs gRPC:

```bash
python -m grpc_tools.protoc -I proto --python_out=. \
  --grpc_python_out=. proto/inferencia.proto
```

## Execução

### Redis

```bash
docker compose up -d
docker compose ps
```

O container deve aparecer como `Up` e `healthy`.

### API REST

Em um terminal:

```bash
source .venv/bin/activate
python -m uvicorn app.api_rest:app --reload --port 8001
```

Documentação: <http://localhost:8001/docs>

### Worker

Em outro terminal:

```bash
source .venv/bin/activate
python -m app.worker
```

Para demonstrar divisão de carga, execute dois workers:

```bash
WORKER_ID=worker-1 python -m app.worker
WORKER_ID=worker-2 python -m app.worker
```

O worker tenta cada inferência até três vezes. Após três falhas, envia a tarefa para `tarefas_dead_letter`.

### Servidor gRPC

Em outro terminal:

```bash
source .venv/bin/activate
python -m app.servidor_grpc
```

O servidor escuta a porta `50051`.

## Cliente REST

Com a API, o Redis e o worker em execução:

```bash
source .venv/bin/activate
python exemplos/cliente_rest.py "o atendimento foi otimo"
```

O cliente testa a rota síncrona e o fluxo assíncrono completo.

Para usar outra porta:

```bash
REST_URL=http://localhost:8000 python exemplos/cliente_rest.py "texto de teste"
```

## Testes manuais REST

Inferência síncrona:

```bash
curl -X POST http://localhost:8001/predict-sync \
  -H 'Content-Type: application/json' \
  -d '{"texto":"o atendimento foi otimo"}'
```

Submissão assíncrona:

```bash
curl -i -X POST http://localhost:8001/predict \
  -H 'Content-Type: application/json' \
  -d '{"texto":"o atendimento foi otimo"}'
```

Copie o ID retornado e consulte:

```bash
curl http://localhost:8001/resultado/ID_RETORNADO
```

Processamento em lote:

```bash
curl -X POST http://localhost:8001/predict-batch \
  -H 'Content-Type: application/json' \
  -d '{"textos":["atendimento excelente","serviço ruim"]}'
```

Métricas:

```bash
curl http://localhost:8001/metricas
```

## Teste gRPC

```bash
python - <<'PY'
import grpc
import inferencia_pb2
import inferencia_pb2_grpc

with grpc.insecure_channel("localhost:50051") as canal:
    stub = inferencia_pb2_grpc.InferenciaStub(canal)
    resposta = stub.PreverLote(
        inferencia_pb2.PedidoLote(
            textos=["atendimento excelente", "serviço ruim"]
        )
    )

for item in resposta.resultados:
    print(item.texto, item.sentimento, item.confianca)
PY
```

## Armazenamento

```text
dados/
├── resultados/       # um JSON por tarefa processada
└── metricas.json     # contadores e latência média
```

O cache fica no Redis e pode ser limpo com:

```bash
docker exec sd-2026-2-kit-c1a2-redis-1 sh -c '
redis-cli --scan --pattern "cache:*" |
while read -r chave; do redis-cli DEL "$chave"; done
'
```

O modelo local é versionado automaticamente. Quando a versão dos dados de treinamento muda, o `modelo.joblib` é treinado novamente na próxima inicialização.

## Encerramento

```bash
docker compose down
```

Para manter os arquivos de resultados e métricas, não remova `dados/`.
