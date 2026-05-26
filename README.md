# DeepCar

Buscador de veículos usados e seminovos com agregação de anúncios, score automático, insights de risco e atualização contínua da base.

## Estado atual

- Fontes ativas no fluxo principal: OLX.
- Na primeira carga da base, o backend tenta completar pelo menos 500 anúncios da OLX.
- A busca retorna o que já existe no banco e pode disparar scraping em background quando o usuário pesquisa por texto, marca ou modelo.
- O frontend segura o estado vazio enquanto a busca ainda está coletando páginas suficientes para mostrar resultado parcial.
- Quando a aplicação abre com a base inicial ainda vazia, a interface mostra uma mensagem amigável de inicialização com o progresso da carga inicial.
- Score e insights são recalculados automaticamente, com heurísticas para preço suspeito e quilometragem improvável.
- Atualização FIPE diária e reprocessamento diário de score e insights já estão agendados no backend.

## Stack

| Camada | Tecnologia |
| --- | --- |
| Frontend | Next.js 16, React 18, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python, SQLAlchemy async |
| Banco | SQLite |
| Cache | TTL em memória |
| Scraping | Worker externo para OLX, com HTTPX/curl fallback |
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
│   └── deepcar.db
├── frontend/
└── docker-compose.yml
```

## Como rodar

### Pré-requisitos

- Python 3.10 ou superior
- Node.js 20 ou superior

### Opção 1: manual

Backend:

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

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

### Opção 2: Docker Compose

```bash
docker-compose up --build
```

## URLs locais

| Serviço | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

## Banco vazio e primeira carga

Se você apagar o arquivo backend/deepcar.db e subir o backend, o sistema faz o seguinte:

1. recria automaticamente as tabelas do banco
2. inicia os jobs agendados
3. dispara automaticamente um bootstrap em background até tentar completar 500 anúncios da OLX, quando essa meta ainda não foi atingida

A base volta a receber anúncios reais nestes cenários:

1. no bootstrap automático do startup, quando a base ativa está vazia
2. quando o usuário faz uma busca na página 1 com q, marca ou modelo
3. quando você roda manualmente o scraper
4. quando o job periódico de scrape rodar no próximo ciclo

Importante:

- o bootstrap automático não roda de novo se já existirem anúncios ativos da OLX no banco
- durante esse bootstrap inicial, o frontend mostra uma mensagem de preparação da base com o progresso por fonte
- o scrape periódico geral continua rodando a cada 6 horas

Para forçar uma carga inicial real logo após zerar o banco, use uma destas opções:

```bash
cd backend
python scripts/run_scrapers.py all 3
```

ou faça uma busca real pelo frontend.

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
| GET | /api/search | Busca veículos com filtros e paginação |
| GET | /api/car/{id} | Detalhe de um veículo |
| GET | /api/filters | Opções dos filtros |
| GET | /api/favorites | Lista favoritos |
| POST | /api/favorites/{id} | Adiciona favorito |
| DELETE | /api/favorites/{id} | Remove favorito |
| POST | /api/scraper/run/{source} | Executa scrape manual para olx ou all (atualmente equivalente a olx) |
| GET | /api/scraper/status | Estado dos scrapers |
| POST | /api/scraper/cancel | Cancela scrape de uma busca |
| GET | /api/scraper/progress | Consulta progresso de uma busca |

## Scripts úteis do backend

| Script | Uso |
| --- | --- |
| scripts/seed.py | Popular o banco com dados de exemplo |
| scripts/run_scrapers.py | Forçar carga real da OLX |
| scripts/update_fipe.py | Atualizar FIPE manualmente sob demanda |
| scripts/rescore_existing_vehicles.py | Reprocessar score e insights manualmente |

## Observações de manutenção

- O cache atual é em memória. Redis não é necessário para o fluxo atual.
- A busca em página 1 evita cache quando há query relevante, para os resultados novos aparecerem sem precisar reiniciar a página.
- O worker de OLX roda em processo separado para evitar problemas do Playwright em background no ambiente Windows.
