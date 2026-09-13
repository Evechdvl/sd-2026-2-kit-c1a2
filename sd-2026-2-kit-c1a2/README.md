# Kit de Partida — C1.A2: Serviço de Inferência Distribuído

**Sistemas Distribuídos e Computação em Nuvem · FAESA · 2026/2**
Prof. Howard Cruz Roatti · Lançado na Aula 6 (10/09) · Entrega na Aula 7 (17/09)

---

## O que é isto

Um serviço que recebe um texto, executa uma inferência de IA e devolve o resultado.
O desafio **não é a IA** (o modelo já vem pronto), e sim expor esse serviço por **duas
tecnologias de comunicação** (REST e gRPC) e **não deixar o cliente esperando** — usando fila.

> **Sobre a IA neste trabalho:** todo contato com inteligência artificial aqui é
> **chamada de biblioteca ou de API**. Você **não vai treinar modelos** nem precisar de
> matemática de aprendizado de máquina. O modelo já vem pronto e configurado.
> A sua nota vem da **engenharia distribuída**: arquitetura, comunicação, resiliência e
> execução reproduzível — a sofisticação do modelo **não pontua**.

---

## Como começar

```bash
# 1. Clone o kit e entre na pasta
git clone https://github.com/howardroatti/sd-2026-2-kit-c1a2.git
cd sd-2026-2-kit-c1a2

# 2. Crie e ative o ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt
```

```bash
# 4. Suba a fila (Redis) em outro terminal
docker compose up -d

# 5. Rode o serviço REST
uvicorn app.api_rest:app --reload --port 8000
# abra http://localhost:8000/docs

# 6. Em outro terminal, rode o worker
python -m app.worker

# 7. Teste o exemplo pronto (rota síncrona)
python exemplos/cliente_rest.py "o atendimento foi otimo"

# 8. Para o gRPC, gere os stubs antes
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/inferencia.proto
python -m app.servidor_grpc
```

---

## Estrutura do projeto

```
sd-2026-2-kit-c1a2/
├── app/
│   ├── modelo.py           # PRONTO - modelo de sentimento offline
│   ├── fila.py             # PRONTO - auxiliares de fila (Redis)
│   ├── api_rest.py         # TAREFAS 1 e 2
│   ├── worker.py           # TAREFAS 3 e 5
│   └── servidor_grpc.py    # TAREFA 4
├── proto/inferencia.proto  # contrato gRPC
├── exemplos/cliente_rest.py
├── scripts/gerar_stubs.*
├── docker-compose.yml      # sobe o Redis
└── TAREFAS.md              # <- comece por aqui
```

---

## O que você precisa fazer

Abra o arquivo **`TAREFAS.md`**: ele lista o núcleo obrigatório item a item, indicando
o arquivo e a aula de referência de cada um.

---

## Como você será avaliado

| Critério | Pontos |
|---|---|
| Arquitetura e decomposição em serviços | 1,5 |
| Comunicação funcionando (REST / gRPC / mensageria) | 1,5 |
| Resiliência e tratamento de falhas | 1,0 |
| Execução reproduzível (README, container, deploy) | 1,0 |
| **Sofisticação do modelo de IA** | **não pontua** |
| **Total** | **5,0** |

**Entrega:** no seu repositório do GitHub, **sem apresentação oral**. Grupos livres.

---

## Aulas de referência

- **Aula 4** — Do RPC ao gRPC (contrato `.proto` e stubs)
- **Aula 5** — REST e OpenAPI com FastAPI
- **Aula 6** — IA como serviço (carregar o modelo uma vez)
- **Aula 8** — Mensageria: fila, worker e dead-letter

---

## Dúvidas frequentes

**Preciso saber machine learning?** Não. O modelo já está pronto e você só chama uma função.

**E se eu não tiver internet no laboratório?** Tudo neste kit funciona offline. O modelo é
treinado localmente e o cliente de LLM tem modo simulado.

**Posso trocar a linguagem?** O kit é em Python porque é o ecossistema usado nas aulas.
Se quiser usar outra linguagem, converse com o professor antes.

**Posso usar IA para me ajudar a programar?** Sim. Este é um trabalho prático feito fora de
sala, e usar ferramentas de IA é realista. O que se avalia é o **sistema funcionando** e as
**decisões de arquitetura** — que você precisa saber explicar.
