# DeepCar

Buscador de veículos usados e seminovos com agregação de anúncios, score automático, insights de risco e atualização contínua da base.

## Licenca

Este projeto esta publicado com direitos reservados.
Nao e permitida a copia, reutilizacao, modificacao, distribuicao ou criacao de obras derivadas sem autorizacao previa por escrito do titular.

Consulte o arquivo `LICENSE` para os termos completos.

## Estado atual

- Fontes ativas no fluxo principal: OLX e iCarros.
- Na primeira carga da base, o backend tenta completar pelo menos 500 anúncios ativos da OLX e 200 do iCarros.
- A busca retorna o que já existe no banco e pode disparar scraping em background na página 1 quando o usuário aplica qualquer filtro relevante.
- O frontend só segura o estado vazio enquanto ainda não existem resultados locais suficientes; se o banco já tiver anúncios compatíveis, eles aparecem imediatamente enquanto o scraping continua.
- Quando a aplicação sobe com a base ativa vazia, a interface mostra o progresso do bootstrap inicial.
- Score e insights são recalculados automaticamente, com heurísticas para preço suspeito e quilometragem improvável.
- Atualização FIPE diária e reprocessamento diário de score e insights já estão agendados no backend.

## Stack

| Camada | Tecnologia |
| --- | --- |
| Frontend | Next.js, React 18, TypeScript, Tailwind CSS, TanStack Query, Zustand |
| Backend | FastAPI, Python, SQLAlchemy async |
| Banco | SQLite |
| Cache | TTL em memória |
| Scraping | Worker externo para OLX, com HTTPX e fallback para curl |
| Jobs | APScheduler |

## Estrutura resumida

```text
DeepCar/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── scrapers/
│   │   ├── services/
│   │   └── main.py
│   ├── scripts/
│   │   ├── run_scrapers.py
│   │   ├── update_fipe.py
│   │   ├── rescore_existing_vehicles.py
│   │   └── seed.py
│   ├── olx_query_worker.py
│   └── deepcar.db
├── frontend/
└── docker-compose.yml
```

## Como rodar

### Pré-requisitos

- Python 3.12 ou superior recomendado
- Node.js 20 ou superior

### Opção 1: manual

Backend:

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Observações:

- O bootstrap inicial e os jobs automáticos são iniciados pelo startup do FastAPI.
- Para desenvolvimento local, mantenha um único processo do Uvicorn. Rodar múltiplos workers duplica scheduler e tarefas de bootstrap.
- O fluxo atual de scraping da OLX usa worker externo e não depende de Playwright no caminho principal de execução manual.
- Se o PowerShell não reconhecer `uvicorn`, use `python -m uvicorn` ou `py -m uvicorn` em vez do executável direto.

Se você quiser dados de exemplo em vez de esperar scraping real:

```bash
cd backend
python scripts/seed.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

No PowerShell do Windows, se houver bloqueio do npm.ps1, use:

```powershell
npm.cmd run dev
```

Variáveis úteis no frontend:

- `NEXT_PUBLIC_API_URL`: por padrão o cliente usa `http://localhost:8000/api`; quando a página abre fora de localhost, o frontend tenta derivar automaticamente o host da API a partir da URL atual.

### Opção 2: Docker Compose

```bash
docker-compose up --build
```

Observações importantes sobre o compose atual:

- O arquivo atual ainda sobe Redis, embora o cache usado hoje pela aplicação seja em memória.
- O backend no compose está configurado com mais de um worker do Uvicorn; isso não é o ideal para este projeto porque pode duplicar jobs do scheduler e bootstrap de startup.

## URLs locais

| Serviço | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Health | http://localhost:8000/health |
| Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

## Banco vazio e primeira carga

Se você apagar o arquivo `backend/deepcar.db` e subir o backend, o sistema faz o seguinte:

1. recria automaticamente as tabelas do banco
2. inicia os jobs agendados
3. dispara automaticamente um bootstrap em background até tentar completar 500 anúncios ativos da OLX, caso a meta ainda não tenha sido atingida

A base volta a receber anúncios reais nestes cenários:

1. no bootstrap automático do startup, quando a base ativa ainda não atingiu a meta inicial
2. quando o usuário faz uma busca na página 1 com qualquer filtro relevante
3. quando você roda manualmente o scraper
4. quando o job periódico de scrape roda no próximo ciclo

Importante:

- o bootstrap automático não roda de novo se a meta inicial da OLX já estiver satisfeita
- durante esse bootstrap inicial, o frontend mostra uma mensagem de preparação da base com o progresso salvo por fonte
- o scrape periódico geral continua rodando a cada 6 horas

Para forçar uma carga inicial real logo após zerar o banco, use:

```bash
cd backend
python scripts/run_scrapers.py all 3
```

ou faça uma busca real pelo frontend com filtros na página 1.

## Jobs automáticos do backend

| Job | Frequência |
| --- | --- |
| Scrape geral | a cada 6 horas |
| Refresh de anúncios ativos | a cada 2 horas |
| Limpeza de anúncios antigos | a cada 12 horas |
| Atualização FIPE | diariamente às 03:00 |
| Reprocessamento de score e insights | diariamente às 04:00 |

## Endpoints principais

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | / | Metadados básicos da API |
| GET | /health | Healthcheck simples |
| GET | /api/search | Busca veículos com filtros e paginação |
| GET | /api/car/{id} | Detalhe de um veículo |
| GET | /api/filters | Opções dos filtros |
| GET | /api/favorites | Lista favoritos da sessão atual |
| POST | /api/favorites/{id} | Adiciona favorito |
| DELETE | /api/favorites/{id} | Remove favorito |
| POST | /api/scraper/run/{source} | Executa scrape manual para `olx`, `icarros` ou `all` |
| GET | /api/scraper/status | Estado interno dos scrapers |
| GET | /api/scraper/bootstrap-status | Progresso da carga inicial automática |
| POST | /api/scraper/cancel?q=... | Cancela scrape de uma busca |
| GET | /api/scraper/progress?q=... | Consulta progresso de uma busca |
| POST | /api/scraper/live?q=... | Dispara scrape rápido ao vivo para uma busca textual |
| GET | /api/scraper/live/stream?q=... | Stream SSE com progresso do scrape ao vivo |
| GET | /api/images/proxy?url=... | Proxy de imagens para driblar hotlink protection |

## Scripts úteis do backend

| Script | Uso |
| --- | --- |
| scripts/seed.py | Popular o banco com dados de exemplo |
| scripts/run_scrapers.py | Forçar carga real da OLX |
| scripts/update_fipe.py | Atualizar FIPE manualmente sob demanda |
| scripts/rescore_existing_vehicles.py | Reprocessar score e insights manualmente |

## Observações de manutenção

- O cache atual é em memória. Redis não é necessário para o fluxo principal atual.
- A busca em página 1 evita cache quando há filtros relevantes, para os resultados novos aparecerem sem precisar reiniciar a página.
- O worker da OLX roda em processo separado para evitar problemas de scraping dentro do loop principal da API no ambiente Windows.
- O frontend envia um identificador de sessão em `x-session-id`; os favoritos são vinculados a essa sessão.
