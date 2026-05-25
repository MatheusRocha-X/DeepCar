# DeepCar

Buscador de veículos usados e seminovos com agregação de anúncios, score automático, insights de risco e atualização contínua da base.

## Estado atual

- Fontes ativas no fluxo principal: OLX e iCarros.
- Na primeira carga da base, o backend tenta completar pelo menos 500 anúncios da OLX e 500 do iCarros.
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
| Scraping | Playwright para OLX, HTTPX para iCarros |
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

### Arquivos de ambiente

Antes de subir localmente, crie estes arquivos a partir dos exemplos versionados:

- `backend/.env` a partir de `backend/.env.example`
- `frontend/.env.local` a partir de `frontend/.env.example`

No PowerShell:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local
```

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
3. dispara automaticamente um bootstrap em background até tentar completar 500 anúncios da OLX e 500 do iCarros, quando essas metas ainda não foram atingidas

A base volta a receber anúncios reais nestes cenários:

1. no bootstrap automático do startup, quando a base ativa está vazia
2. quando o usuário faz uma busca na página 1 com q, marca ou modelo
3. quando você roda manualmente o scraper
4. quando o job periódico de scrape rodar no próximo ciclo

Importante:

- o bootstrap automático não roda de novo se já existirem anúncios ativos de OLX ou iCarros no banco
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
| POST | /api/scraper/run/{source} | Executa scrape manual para olx, icarros ou all |
| GET | /api/scraper/status | Estado dos scrapers |
| POST | /api/scraper/cancel | Cancela scrape de uma busca |
| GET | /api/scraper/progress | Consulta progresso de uma busca |

## Scripts úteis do backend

| Script | Uso |
| --- | --- |
| scripts/seed.py | Popular o banco com dados de exemplo |
| scripts/run_scrapers.py | Forçar carga real de OLX e iCarros |
| scripts/update_fipe.py | Atualizar FIPE manualmente sob demanda |
| scripts/rescore_existing_vehicles.py | Reprocessar score e insights manualmente |

## Observações de manutenção

- O cache atual é em memória. Redis não é necessário para o fluxo atual.
- A busca em página 1 evita cache quando há query relevante, para os resultados novos aparecerem sem precisar reiniciar a página.
- O worker de OLX roda em processo separado para evitar problemas do Playwright em background no ambiente Windows.

## Deploy com GitHub, Render e Vercel

Arquivos de automação já criados neste repositório:

- `render.yaml`: cria o backend no Render via Blueprint
- `frontend/vercel.json`: fixa os comandos e o preset do projeto no Vercel

### 1. Parear o projeto com o GitHub

Passo a passo pelo site do GitHub:

1. entre em https://github.com
2. clique em `New repository`
3. escolha o nome do repositório, por exemplo `deepcar`
4. escolha se ele será `Public` ou `Private`
5. se esta pasta já tem os arquivos do projeto, deixe desmarcado `Add a README file`, `.gitignore` e `Choose a license`
6. clique em `Create repository`
7. copie a URL HTTPS exibida pelo GitHub, por exemplo `https://github.com/seu-usuario/deepcar.git`

Se esta pasta ainda não estiver versionada com Git, rode no terminal:

```bash
cd DeepCar
git init
git add .
git commit -m "chore: initial commit"
git branch -M main
git remote add origin https://github.com/seu-usuario/deepcar.git
git push -u origin main
```

Se o repositório local já existir e você só quiser conectar ao GitHub:

```bash
git remote add origin https://github.com/seu-usuario/deepcar.git
git push -u origin main
```

Se o `origin` já existir, troque a URL em vez de adicionar de novo:

```bash
git remote set-url origin https://github.com/seu-usuario/deepcar.git
git push -u origin main
```

Dica prática:

- crie o repositório no GitHub sem README, `.gitignore` ou licença se você já tiver arquivos locais, para evitar conflito no primeiro push
- depois do pareamento, novos deploys passam a ser feitos com `git add .`, `git commit -m "..."` e `git push`
- se o GitHub pedir autenticação no push, use login no navegador ou um token pessoal em vez de senha antiga

### 2. Deploy do backend no Render

Este repositório agora já possui um `render.yaml` na raiz. O caminho recomendado é criar o backend via `Blueprint`, porque o arquivo já aponta para `backend`, usa Docker, cria disco persistente e configura as variáveis mínimas.

Passo a passo:

1. Faça push do projeto para o GitHub.
2. No Render, clique em `New +` > `Blueprint`.
3. Conecte sua conta do GitHub e escolha o mesmo repositório.
4. O Render deve detectar automaticamente o arquivo `render.yaml`.
5. Revise o serviço que será criado com esta configuração:
	- Name: `deepcar-backend`
	- Runtime: `Docker`
	- Root Directory: `backend`
	- Health Check Path: `/health`
	- Persistent Disk em `/var/data`
	- `DATABASE_URL` apontando para `/var/data/deepcar.db`
	- `SECRET_KEY` gerada automaticamente pelo Render
6. Clique em `Apply` ou `Create Resources`.
7. Aguarde o primeiro deploy terminar.
8. Se quiser restringir CORS apenas ao seu frontend, adicione manualmente no painel do Render:

```env
CORS_ORIGINS=["http://localhost:3000","https://seu-projeto.vercel.app"]
```

9. Quando terminar, teste estas URLs:
	- `https://seu-backend.onrender.com/health`
	- `https://seu-backend.onrender.com/docs`

Observações importantes para o Render:

- como o banco atual é SQLite, o disco persistente é obrigatório
- o backend agora sobe com `1` worker para não duplicar scheduler, bootstrap e jobs agendados
- o `render.yaml` não define `CORS_ORIGINS` por padrão porque o backend já aceita origens não-locais pelo regex atual; só adicione essa variável se quiser travar explicitamente os domínios permitidos
- se o plano do Render entrar em sleep, os jobs automáticos deixam de rodar com confiabilidade

### 3. Deploy do frontend no Vercel

O frontend está em uma subpasta Next.js e agora também possui `frontend/vercel.json`. Esse arquivo fixa framework e comandos do projeto, mas o `Root Directory` ainda precisa ser definido no painel do Vercel.

Passo a passo:

1. No Vercel, clique em `Add New` > `Project`.
2. Importe o mesmo repositório do GitHub.
3. Na configuração do projeto, ajuste:
	- Root Directory: `frontend`
	- Framework Preset: `Next.js`
4. O Vercel vai ler automaticamente o arquivo `frontend/vercel.json` depois que o `Root Directory` estiver apontando para `frontend`.
5. Adicione a variável de ambiente abaixo:

```env
NEXT_PUBLIC_API_URL=https://seu-backend.onrender.com/api
```

6. Clique em `Deploy`.
7. Depois do deploy, abra o domínio do Vercel e confirme que a interface carrega e consegue buscar dados da API.

### 4. Conectar Vercel + Render

Depois que os dois serviços estiverem no ar:

1. copie a URL pública do Render
2. cole essa URL na variável `NEXT_PUBLIC_API_URL` do Vercel, sempre terminando com `/api`
3. faça um redeploy do Vercel, se a variável tiver sido criada ou alterada depois do primeiro build
4. teste busca, detalhe do veículo, favoritos e carregamento de imagens

### 5. Fluxo de atualização depois do primeiro deploy

Depois que GitHub, Render e Vercel estiverem conectados, o fluxo normal fica assim:

```bash
git add .
git commit -m "feat: sua alteração"
git push origin main
```

Com isso:

- o GitHub recebe o código
- o Render redeploya o backend automaticamente
- o Vercel redeploya o frontend automaticamente

### 6. Resumo rápido da arquitetura de deploy

- GitHub: repositório central do projeto
- Render: backend FastAPI + Playwright + SQLite com disco persistente
- Vercel: frontend Next.js apontando para a API do Render
