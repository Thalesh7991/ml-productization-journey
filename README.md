# Churn Prediction — Do Notebook à Produção

> Da análise exploratória até um sistema de predição assíncrono, containerizado, com mensageria e persistência relacional.

---

## Contexto de Negócio

Churn é uma das métricas mais críticas para qualquer empresa. Adquirir um novo cliente custa entre 5 e 7 vezes mais do que reter um existente. Identificar clientes com alto risco de cancelamento — antes que cancelem — viabiliza ações de retenção direcionadas: ofertas personalizadas, suporte proativo, programas de fidelidade.

**O foco deste projeto não é a performance do modelo.** O modelo de Gradient Boosting utilizado é um baseline sólido, mas o objetivo central aqui é outro: demonstrar a evolução de um projeto de ciência de dados saindo de um Jupyter notebook para um sistema produtizado com práticas robustas de engenharia.


Neste projeto foquei em melhorar minhas habilidades em produtizar um projeto de Ciência de Dados, pois é isso que separa um Cientista de Dados que apenas entrega modelos daqueles Seniors que entregam sistemas que funcionam em produção e **realmente agregam valor ao negócio**.

---

## Evolução da Arquitetura

O projeto foi construído em fases deliberadas, cada uma introduzindo uma nova camada de maturidade de produção.

### Fase 1 — Notebook (Baseline)

O ponto de partida: um único Jupyter notebook (`notebooks/ciclo0.ipynb`) com análise exploratória, engenharia de features, treinamento e avaliação do modelo. Não reutilizável. Não deployável. Mas essencial para validar a hipótese de negócio.

**Problema dessa abordagem:** toda a lógica misturada em um único arquivo. Sem garantias de reprodutibilidade. Sem como ser chamado por nenhum sistema externo.

---

### Fase 2 — Modularização (`src/`)

A lógica do notebook foi refatorada em um pacote Python organizado:

```
src/
├── config.py          # Fonte única de verdade para constantes e paths
├── data/load.py       # Ingestão de dados
├── features/build.py  # Pipeline de feature engineering (sem data leakage)
├── models/
│   ├── train.py       # Treinamento, validação cruzada, serialização de artefatos
│   ├── predict.py     # Pipeline de inferência (dados brutos → probabilidade)
│   └── evaluate.py    # Cálculo de métricas e persistência de resultados
```

**Decisão de design crítica — prevenção de data leakage:**

O pipeline de feature engineering foi separado em duas etapas explícitas:

```python
build_features_base(df)          # Transformações determinísticas — seguro antes do split
apply_scaling(df, scaler, fit)   # MinMaxScaler — fit APENAS nos dados de treino
```

Essa separação garante que o scaler nunca aprenda estatísticas do conjunto de teste — um erro comum em projetos de DS que infla métricas de avaliação e degrada a performance em produção.

**Serialização do artefato do modelo:**

Modelo e scaler são persistidos juntos em um único bundle:
```python
{"model": GradientBoostingClassifier, "scaler": MinMaxScaler}
```

Isso previne o bug clássico de produção de usar um scaler incompatível com o modelo no momento da inferência.

---

### Fase 3 — API REST (FastAPI)

Uma API síncrona de predição foi a primeira versão deployável:

```
POST /predict  →  Feature Engineering  →  Modelo  →  {"churn_probability": 0.82, "churn_label": 1}
```

Construída com **FastAPI** e **Pydantic v2** para validação automática de inputs. Todos os campos categóricos usam tipos `Literal` — um `InternetService: "wifi"` inválido retorna HTTP 422 antes de chegar ao modelo.

---

### Fase 4 — Containerização (Docker)

A API foi containerizada usando a imagem base `python:3.11-slim`. Um `.dockerignore` exclui arquivos de dados, notebooks e testes da imagem, mantendo-a enxuta.

---

### Fase 5 — Mensageria Assíncrona (RabbitMQ)

**O ponto de inflexão arquitetural.**

A API síncrona tem uma limitação fundamental: o cliente aguarda enquanto o modelo processa. Em cenários de batch, sistemas de alta concorrência ou modelos pesados, isso cria gargalos e riscos de timeout.

A solução é o padrão de **job assíncrono** com broker de mensagens.

#### Como funciona

```
┌──────────┐   POST /predict   ┌─────────────┐
│  Cliente │ ─────────────────▶│   FastAPI   │
│          │◀───────────────── │             │
│          │  {"job_id": "..."}│  producer   │
└──────────┘                   └──────┬──────┘
                                      │ publish
                                      ▼
                               ┌─────────────┐
                               │  RabbitMQ   │  fila: churn_requests
                               └──────┬──────┘
                                      │ consume
                                      ▼
                               ┌─────────────┐
                               │   Worker    │  FE + predict_proba()
                               │             │
                               └──────┬──────┘
                                      │ INSERT
                                      ▼
                               ┌─────────────┐
                               │ PostgreSQL  │  tabela: predictions
                               └──────┬──────┘
                                      │ SELECT
┌──────────┐  GET /result/{id}  ┌─────▼───────┐
│  Cliente │ ─────────────────▶│   FastAPI   │
│          │◀────────────────── │             │
│          │  {predição}        └─────────────┘
└──────────┘
```

#### Por que isso importa

| Preocupação | API Síncrona | Mensageria Assíncrona |
|---|---|---|
| Cliente aguarda o modelo | Sim | Não — recebe `job_id` imediatamente |
| Requisições simultâneas | Limitado pelas threads da API | Fila absorve qualquer volume |
| Risco de timeout do modelo | Sim | Não — worker processa no seu ritmo |
| Escalabilidade horizontal | Adicionar réplicas da API | Adicionar réplicas do worker independentemente |
| Tolerância a falhas | Requisição perdida se a API cair | Mensagem permanece na fila até ACK |

#### Durabilidade das mensagens

A fila é declarada com `durable=True` — mensagens sobrevivem a restarts do RabbitMQ. O worker só envia `basic_ack` **após** gravar com sucesso no banco. Em caso de falha, `basic_nack(requeue=False)` descarta a mensagem de forma limpa, evitando loop infinito de reprocessamento.

---

### Fase 6 — Persistência Relacional (PostgreSQL)

Os resultados são armazenados em banco de dados relacional — não em arquivos temporários. Isso viabiliza:

- **Trilha de auditoria** — histórico completo de todas as predições realizadas
- **Análises de negócio** — consultas como "quantos clientes de alto risco foram pontuados este mês com a versão X do modelo"
- **Monitoramento do modelo** — rastreamento de drift nas probabilidades preditas ao longo do tempo

**Schema:**

```sql
CREATE TABLE predictions (
    job_id            UUID         PRIMARY KEY,
    created_at        TIMESTAMPTZ  DEFAULT NOW(),
    churn_probability FLOAT        NOT NULL,
    churn_label       SMALLINT     NOT NULL,
    model_version     VARCHAR(50)  NOT NULL,
    input_data        JSONB
);
```

A coluna `input_data JSONB` armazena o payload original do cliente — viabilizando análises retrospectivas e debugging sem precisar re-consultar o sistema de origem.

---

## Estrutura do Projeto

```
churn_kaggle/
├── src/
│   ├── config.py              # Constantes, paths, listas de features
│   ├── data/load.py           # Carregamento de dados
│   ├── features/build.py      # Feature engineering (sem data leakage)
│   ├── models/
│   │   ├── train.py           # Pipeline de treinamento
│   │   ├── predict.py         # Pipeline de inferência
│   │   └── evaluate.py        # Métricas
│   ├── api/
│   │   ├── main.py            # Aplicação FastAPI
│   │   └── schemas.py         # Modelos Pydantic de request/response
│   ├── messaging/
│   │   ├── producer.py        # Publica jobs no RabbitMQ
│   │   └── worker.py          # Consome fila, executa inferência, persiste no banco
│   └── db/
│       ├── connection.py      # Fábrica de conexão PostgreSQL
│       └── schema.py          # Criação de tabelas (CREATE TABLE IF NOT EXISTS)
├── tests/
│   ├── conftest.py            # Fixtures compartilhadas do pytest
│   └── test_features.py       # Testes unitários de feature engineering
├── notebooks/
│   └── ciclo0.ipynb           # EDA original e modelo baseline
├── models/                    # Artefatos serializados do modelo (.pkl)
├── train.py                   # Entry point: executa o pipeline completo de treino
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .gitignore
```

---

## Como Executar

### Pré-requisitos

- Docker Desktop
- Docker Compose

### Subir todos os serviços

```bash
docker compose up --build
```

Isso inicia 4 containers:

| Container | Função | Porta |
|---|---|---|
| `rabbitmq` | Broker de mensagens + UI de gerenciamento | 5672 / 15672 |
| `postgres` | Persistência relacional | 5432 |
| `api` | Serviço de predição FastAPI | 8000 |
| `worker` | Worker de inferência assíncrona | — |

Todos os serviços sobem em ordem de dependência com health checks — a API e o worker só iniciam após RabbitMQ e PostgreSQL estarem prontos.

### Endpoints da API

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/predict` | Submete um job de predição |
| `GET` | `/result/{job_id}` | Recupera o resultado da predição |

Documentação interativa: [http://localhost:8000/docs](http://localhost:8000/docs)

UI de gerenciamento do RabbitMQ: [http://localhost:15672](http://localhost:15672) (guest / guest)

### Exemplo de fluxo completo

```bash
# 1. Submeter um job de predição
POST /predict
{
  "SeniorCitizen": 0,
  "Partner": "Yes",
  "Dependents": "No",
  "tenure": 3,
  "PhoneService": "Yes",
  "MultipleLines": "No",
  "InternetService": "Fiber optic",
  "OnlineSecurity": "No",
  "OnlineBackup": "No",
  "DeviceProtection": "No",
  "TechSupport": "No",
  "StreamingTV": "Yes",
  "StreamingMovies": "Yes",
  "Contract": "Month-to-month",
  "PaperlessBilling": "Yes",
  "PaymentMethod": "Electronic check",
  "MonthlyCharges": 85.0
}

# Resposta imediata
{"job_id": "7f335d63-...", "status": "queued"}

# 2. Consultar o resultado (após ~1s)
GET /result/7f335d63-...

# Resposta
{
  "job_id": "7f335d63-...",
  "churn_probability": 0.527,
  "churn_label": 1,
  "model_version": "ciclo0",
  "created_at": "2026-04-06T19:50:36+00:00"
}
```

### Consultar o banco diretamente

```bash
docker exec -it churn_kaggle-postgres-1 \
  psql -U postgres -d churn \
  -c "SELECT job_id, churn_probability, churn_label, model_version, created_at FROM predictions ORDER BY created_at DESC;"
```

---

## Modelo

- **Algoritmo:** Gradient Boosting Classifier (scikit-learn)
- **Features:** 20 features a partir dos dados brutos
- **Validação:** Validação cruzada estratificada com 5 folds
- **Artefato:** `models/gradient_boosting_ciclo0.pkl` — bundle serializado `{model, scaler}`

Principais features:
- `TenureGroup` — tempo de contrato agrupado em faixas (0–12, 12–24, 24–48, 48–72 meses)
- `ServicesBundle` — contagem de serviços adicionais ativos (0–6)
- `IsAutoPayment` — flag binária para métodos de pagamento automático (correlacionado com menor churn)
- `HasInternetService` — derivado do campo `InternetService`

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11 |
| ML | scikit-learn, pandas, numpy |
| API | FastAPI, Pydantic v2, Uvicorn |
| Mensageria | RabbitMQ, pika |
| Banco de Dados | PostgreSQL 16, psycopg2 |
| Containers | Docker, Docker Compose |
| Testes | pytest |

---

## Decisões de Engenharia

**Pipeline sem data leakage por design** — a engenharia de features é separada em transformações determinísticas (pré-split) e scaling (fit apenas no treino). Isso é garantido estruturalmente, não por convenção.

**Bundle único de artefato** — modelo e scaler serializados juntos eliminam a possibilidade de usar artefatos incompatíveis em produção.

**Validação de input rigorosa** — todos os campos categóricos usam tipos `Literal` no Pydantic. Inputs inválidos são rejeitados na fronteira da API antes de chegarem ao modelo.

**`basic_nack(requeue=False)` em falhas** — mensagens malformadas são descartadas para evitar loops infinitos de reprocessamento bloqueando a fila.

**`basic_qos(prefetch_count=1)`** — o worker processa uma mensagem por vez, prevenindo sobrecarga de memória em picos de tráfego.

**Retry loops com delay** — tanto a API quanto o worker reconectam automaticamente ao RabbitMQ e ao PostgreSQL na inicialização, tolerando o delay natural entre a subida dos containers.
