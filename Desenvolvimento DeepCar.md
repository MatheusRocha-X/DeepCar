# 🚗 Projeto SaaS/PWA — AI Car Finder

## Objetivo
Desenvolver um sistema web PWA inteligente de busca de veículos usados/seminovos.

O sistema deve agregar anúncios automotivos de diferentes fontes e permitir buscas avançadas com filtros inteligentes, ranking de qualidade e interface moderna.

O foco do MVP é:
- busca rápida
- filtros avançados
- experiência semelhante ao Webmotors
- score inteligente de anúncios

---

# 🧠 Conceito do Produto

O usuário pesquisa veículos usando filtros como:
- marca
- modelo
- ano
- km
- preço
- tipo de vendedor

O sistema retorna:
- anúncios organizados
- score de qualidade
- indicadores inteligentes
- melhores oportunidades

---

# 🌐 Tipo de aplicação

PWA (Progressive Web App)

Responsivo:
- desktop
- tablet
- mobile

---

# 🏗️ Stack Tecnológica

## Frontend
- Next.js
- TypeScript
- TailwindCSS

## Backend
- FastAPI (Python)

## Banco
- SQLite

## Cache
- Redis

## Scraping
- Playwright

---

# 🎨 Interface

Interface moderna estilo:
- Webmotors
- OLX
- iCarros

Design:
- clean
- rápido
- minimalista
- cards modernos

Tema:
- dark/light mode

---

# 🔍 Funcionalidade Principal

## Sistema de busca inteligente

Filtros:

### Marca
Dropdown pesquisável.

### Modelo
Dependente da marca selecionada.

### Ano
- Ano mínimo
- Ano máximo

### KM
- KM mínimo
- KM máximo

### Preço
- preço mínimo
- preço máximo

### Tipo de vendedor
- Pessoa Física
- Loja
- Concessionária

### Combustível
- Flex
- Gasolina
- Diesel
- Elétrico
- Híbrido

### Câmbio
- Manual
- Automático
- CVT
- Automatizado

### Localização
- Estado
- Cidade

---

# 📋 Resultado da Busca

Exibir anúncios em cards.

Cada card deve conter:

- foto principal
- título
- preço
- km
- ano
- cidade
- tipo vendedor
- score inteligente
- resumo automático
- botão “Ver anúncio”

---

# ⭐ Sistema de Score Inteligente

Cada anúncio deve receber um score de 0 a 100.

Critérios:

## Preço
Comparar com média do mercado.

## KM
Comparar km com ano do veículo.

## Fotos
Quantidade e qualidade.

## Descrição
Detectar:
- descrição pobre
- termos suspeitos
- excesso de urgência

## Vendedor
Priorizar:
- lojas confiáveis
- anúncios completos

---

# 🧠 Insights Inteligentes

Exibir mensagens automáticas:

Exemplos:

- “Preço abaixo da média”
- “KM baixa para o ano”
- “Possível anúncio duplicado”
- “Descrição suspeita”
- “Bom custo-benefício”

---

# 🕷️ Sistema de Scraping

Criar arquitetura preparada para múltiplas fontes.

Inicialmente:
- OLX
- Webmotors 
- Icarros
- Na Pista

O scraper deve:

- coletar anúncios
- extrair dados
- salvar no banco
- atualizar anúncios periodicamente

Tecnologia:
- Playwright

---

# 🗄️ Estrutura do Banco

Tabela anúncios:

- id
- titulo
- marca
- modelo
- versao
- ano
- km
- preco
- cambio
- combustivel
- cidade
- estado
- vendedor_tipo
- descricao
- fotos[]
- source_url
- source_name
- score
- insights[]
- created_at

---

# 🔥 Funcionalidades Extras do MVP

## Favoritos
Usuário salva anúncios.

## Ordenação
Ordenar por:
- score
- menor preço
- menor km
- mais recente

## Busca rápida
Barra global de pesquisa.

---

# 📱 PWA

Aplicação deve:
- funcionar no celular
- ser instalável
- ter boa performance
- cache offline básico

---

# ⚡ Performance

Requisitos:
- paginação
- lazy loading
- cache de resultados
- otimização de imagens

---

# 🔐 Backend

Criar API REST estruturada:

Rotas:
- /search
- /car/:id
- /favorites
- /filters

---

# 🎯 Objetivo Visual

A aplicação deve parecer:
- moderna
- premium
- inteligente
- rápida

Foco em UX.

# 🎨 Referências

Inspirar UX em:
- Webmotors
- Airbnb
- OLX
- Mercado Livre

Layout moderno e minimalista.

---