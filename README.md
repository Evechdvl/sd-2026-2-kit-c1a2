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

## Execução — teste rápido recomendado

O exemplo `exemplos/cliente_rest.py` é a forma mais simples de testar o
projeto completo. Ele executa uma inferência síncrona e depois testa o fluxo
assíncrono com fila, worker e consulta do resultado.

Use quatro terminais, todos na pasta do projeto.

### Terminal 1 — Redis

```bash
docker compose up -d
docker compose ps
```

O Redis precisa aparecer como `Up` e `healthy`.

### Terminal 2 — API REST

```bash
source .venv/bin/activate
python -m uvicorn app.api_rest:app --reload --port 8001
```

Deixe esse terminal aberto. A API ficará em <http://localhost:8001>.

### Terminal 3 — Worker

```bash
source .venv/bin/activate
python -m app.worker
```

O worker deve mostrar que está pronto e aguardando tarefas.

### Terminal 4 — Cliente REST

```bash
source .venv/bin/activate
python exemplos/cliente_rest.py "o atendimento foi otimo"
```

O resultado esperado será parecido com:

```text
sincrono: {... 'sentimento': 'positivo', ...}
id da tarefa:  UUID_DA_TAREFA
assincrono: {... 'status': 'pronto', ...}
```

O primeiro resultado é síncrono. O segundo passa pela fila Redis e pelo
worker. Se o mesmo texto já tiver sido processado, pode aparecer
`'cache_hit': True`.

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

O cliente está em `exemplos/cliente_rest.py`. Com a API, o Redis e o worker em
execução, rode:

```bash
source .venv/bin/activate
python exemplos/cliente_rest.py "o atendimento foi otimo"
```

O cliente testa automaticamente a rota síncrona e o fluxo assíncrono completo.

Para usar outra porta:

```bash
REST_URL=http://localhost:8000 python exemplos/cliente_rest.py "texto de teste"
```

O valor padrão é `http://localhost:8001`.

## Solução de problemas

### `Failed to connect to localhost port 8001`

A API não está em execução. Inicie-a com:

```bash
python -m uvicorn app.api_rest:app --reload --port 8001
```

### Resposta `na_fila` não muda para `pronto`

O worker não está rodando ou o Redis não está saudável. Confira:

```bash
docker compose ps
python -m app.worker
```

### Erro `422` ao usar `curl`

Use a URL sem colchetes ou parênteses:

```bash
curl -X POST http://localhost:8001/predict-sync \
  -H 'Content-Type: application/json' \
  -d '{"texto":"o atendimento foi otimo"}'
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
