# CreditoIMO - Product Requirements Document

## Problema Original
Aplicação de gestão de processos de crédito habitação e transações imobiliárias que funciona como "espelho" de um quadro Trello, com sincronização bidirecional.

## Stack Técnica
- **Frontend**: React + Vite (migrado de CRA), Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, Pydantic, Motor (MongoDB async)
- **Base de Dados**: MongoDB Atlas (Cluster: cluster0.c8livu.mongodb.net)
  - **Desenvolvimento/Testes**: `powerprecision_dev`
  - **Produção**: `powerprecision`
- **Integrações**: Trello API & Webhooks, IMAP/SMTP (emails), Cloud Storage (S3, Google Drive, OneDrive, Dropbox - configurável pelo admin), Gemini 2.0 Flash (scraping), AWS S3 (documentos), OpenAI GPT-4o-mini (análise de documentos via emergentintegrations), ScraperAPI (web scraping)

## Última Actualização - 15 Fevereiro 2026 (Sessão 31)

### ✅ TAREFA P0 Completa (Sessão 31) - 100% VERIFIED (iteration_44)

#### Categorização e Pesquisa de Documentos com IA
**Objetivo:** Permitir categorizar documentos automaticamente com IA e pesquisar por conteúdo.
**Requisitos do utilizador:**
1. Deixar a IA criar categorias automaticamente
2. Pesquisa por cliente/processo específico
3. Interface na página de detalhes do processo

##### Backend - Novos Endpoints - IMPLEMENTADO
- **`GET /api/documents/metadata/{process_id}`**: Obtém metadados de todos os documentos de um processo
- **`POST /api/documents/search`**: Pesquisa documentos por query (2-500 chars), filtro por process_id e categorias, limit 1-100
- **`GET /api/documents/categories`**: Lista categorias com contagem de documentos, filtro opcional por process_id
- **`POST /api/documents/categorize/{process_id}`**: Categoriza um documento específico (s3_path, filename)
- **`POST /api/documents/categorize-all/{process_id}`**: Categoriza todos os documentos não categorizados
- **Ficheiros**: `/app/backend/routes/documents.py` (linhas 388-755)
- **Status**: ✅ IMPLEMENTADO E TESTADO

##### Backend - Serviço de Categorização IA - IMPLEMENTADO
- **Extração de texto**: pypdf para PDFs
- **Categorização IA**: GPT-4o-mini via Emergent LLM Key
- **Categorias dinâmicas**: IA cria categorias baseadas no conteúdo (Identificação, Rendimentos, Emprego, Bancários, Imóvel, Contratos, Fiscais, Simulações, Outros)
- **Retorna**: category, subcategory, confidence (0-1), tags (3-5 palavras), summary
- **Pesquisa por conteúdo**: scoring ponderado em filename, categoria, tags, resumo e texto extraído
- **Ficheiros**: `/app/backend/services/document_categorization.py`
- **Status**: ✅ IMPLEMENTADO E TESTADO

##### Backend - Modelos - IMPLEMENTADO
- **DocumentMetadata**: id, process_id, client_name, s3_path, filename, ai_category, ai_subcategory, ai_confidence, ai_tags, ai_summary, extracted_text, is_categorized
- **DocumentSearchRequest**: query, process_id (opcional), categories (opcional), limit
- **DocumentSearchResult**: id, process_id, client_name, s3_path, filename, ai_category, ai_summary, relevance_score, matched_text
- **Ficheiros**: `/app/backend/models/document.py`
- **Status**: ✅ IMPLEMENTADO E TESTADO

##### Frontend - Componente DocumentSearchPanel - IMPLEMENTADO
- **Localização**: Página de detalhes do processo, após accordion de "Documentos"
- **Funcionalidades**:
  - Campo de pesquisa com mínimo 2 caracteres
  - Botão "Categorizar com IA" que abre dialog com contagens (total, já categorizados, por categorizar)
  - Dialog de progresso durante categorização
  - Filtro dropdown por categoria
  - Lista de documentos com badges de categoria coloridos
  - Exibição de tags por documento
  - Resultados de pesquisa com relevância e texto correspondente
  - Mensagem "Nenhum documento encontrado" quando vazio
- **data-testid**: document-search-panel, document-search-input, search-btn, categorize-all-btn
- **Ficheiros**: 
  - `/app/frontend/src/components/DocumentSearchPanel.jsx` (NOVO)
  - `/app/frontend/src/pages/ProcessDetails.js` (linha 66 import, linhas 1991-1995 integração)
- **Status**: ✅ IMPLEMENTADO E TESTADO

### ✅ TAREFA 1 & 2 Completas (Sessão 30) - 100% VERIFIED (iteration_43)

#### TAREFA 1: Gestão de Emails (Privacidade e Associação Manual)
**Objetivo:** Mostrar apenas emails relevantes e permitir associação manual.

##### 1A: Filtro por Participação do Utilizador - IMPLEMENTADO
- **Problema**: Utilizadores viam todos os emails do cliente, independentemente de terem participado
- **Solução**: Parâmetro `filter_by_user=true` no endpoint `GET /api/emails/process/{id}` que filtra emails onde o utilizador é sender, to ou cc
- **Ficheiros**: `/app/backend/routes/emails.py`
- **Status**: ✅ IMPLEMENTADO E TESTADO

##### 1B: Pesquisa de Emails - IMPLEMENTADO
- **Endpoint**: `GET /api/emails/search?q=termo&limit=20`
- **Funcionalidade**: Pesquisa por assunto ou remetente (mínimo 3 caracteres)
- **Ficheiros**: `/app/backend/routes/emails.py`
- **Status**: ✅ IMPLEMENTADO E TESTADO

##### 1C: Associação Manual de Emails - IMPLEMENTADO
- **Endpoint**: `POST /api/emails/associate` com body `{email_id, process_id}`
- **Funcionalidade**: Associa email existente a um cliente/processo mesmo que email não esteja no header
- **UI**: Botão "Associar" no EmailHistoryPanel, dialog de pesquisa
- **Ficheiros**: 
  - `/app/backend/routes/emails.py`
  - `/app/frontend/src/components/EmailHistoryPanel.js`
- **Status**: ✅ IMPLEMENTADO E TESTADO

#### TAREFA 2: Documentos e Validação de Dados IA (Conflitos e Confirmação)
**Objetivo:** IA lê documentos, mas se campo já tem dados, utilizador decide. Se cliente "Confirmado", IA para de analisar dados de perfil.

##### 2A: Flag de Confirmação de Dados - IMPLEMENTADO
- **Campos adicionados ao modelo Process**: `is_data_confirmed` (bool), `ai_suggestions` (list)
- **Endpoint**: `POST /api/processes/{id}/confirm-data` com body `{confirmed: true/false}`
- **Funcionalidade**: Quando confirmado, IA não sobrepõe dados de perfil
- **Ficheiros**: 
  - `/app/backend/models/process.py`
  - `/app/backend/routes/processes.py`
- **Status**: ✅ IMPLEMENTADO E TESTADO

##### 2B: Resolução de Conflitos - IMPLEMENTADO
- **Endpoint**: `POST /api/processes/{id}/resolve-conflict` com body `{field, choice: 'ai'|'current'}`
- **Funcionalidade**: Resolve conflito aceitando valor IA ou mantendo valor actual
- **Ficheiros**: `/app/backend/routes/processes.py`
- **Status**: ✅ IMPLEMENTADO E TESTADO

##### 2C: Funções de Gestão de Conflitos - IMPLEMENTADO
- **Funções**: `check_data_conflicts()`, `merge_data_with_conflicts()`
- **Lógica**:
  - Campo vazio → IA preenche automaticamente
  - Campo preenchido + não confirmado → Gera sugestão (ai_suggestions)
  - Campo confirmado → Ignora extração de dados de perfil
- **Ficheiros**: `/app/backend/services/ai_document.py`
- **Status**: ✅ IMPLEMENTADO E TESTADO

##### 2D: Componente DataConflictResolver - IMPLEMENTADO
- **Localização**: Topo da ficha do cliente, após Timeline
- **Funcionalidades**:
  - Mostra badge verde "Dados Verificados" quando confirmado
  - Mostra lista de conflitos pendentes com "Valor Actual" vs "Valor Sugerido pela IA"
  - Botões "Manter Actual" e "Aceitar IA" para cada conflito
  - Botão "Confirmar Dados" quando todos conflitos resolvidos
- **Ficheiros**: 
  - `/app/frontend/src/components/DataConflictResolver.jsx` (NOVO)
  - `/app/frontend/src/pages/ProcessDetails.js`
- **Status**: ✅ IMPLEMENTADO E TESTADO

### ✅ Bug Fixes P0 Completos (Sessão 29) - 100% VERIFIED (iteration_42)

#### Bug Fix 1: Erro ao salvar perfil - CORRIGIDO
- **Problema**: Utilizadores não-admin não conseguiam atualizar o próprio perfil (API exigia role admin)
- **Solução**: Nova rota `PUT /api/auth/profile` que permite qualquer utilizador autenticado atualizar o seu próprio nome e telefone
- **Ficheiros modificados**: 
  - `/app/backend/routes/auth.py` - adicionada rota `/api/auth/profile`
  - `/app/frontend/src/pages/SettingsPage.js` - atualizado para usar nova rota
- **Status**: ✅ CORRIGIDO E TESTADO

#### Bug Fix 2: Rota de alteração de password - IMPLEMENTADO
- **Problema**: Não existia endpoint funcional para alterar password
- **Solução**: Nova rota `POST /api/auth/change-password` com validação (6+ caracteres, password atual correcta)
- **Ficheiros modificados**: `/app/backend/routes/auth.py`
- **Status**: ✅ IMPLEMENTADO E TESTADO

#### Bug Fix 3: Botão "Clientes" no mobile para consultores - CORRIGIDO
- **Problema**: No mobile, consultores iam para `/clientes` (todos os clientes) em vez de `/meus-clientes`
- **Solução**: `getClientsPath()` no MobileBottomNav retorna `/meus-clientes` para roles consultor, intermediario, mediador
- **Ficheiros modificados**: `/app/frontend/src/components/layout/MobileBottomNav.jsx`
- **Status**: ✅ CORRIGIDO E TESTADO

#### Bug Fix 4: Erro ao criar "Novo Processo" - CORRIGIDO
- **Problema**: A rota `POST /api/clients/{client_id}/create-process` falhava porque procurava na colecção `clients` vazia
- **Solução**: A rota agora aceita tanto client_id real como process_id (clientes virtuais agregados de processos)
- **Ficheiros modificados**: `/app/backend/routes/clients.py`
- **Status**: ✅ CORRIGIDO E TESTADO

#### Bug Fix 5: Página Leads/Visitas no mobile - IMPLEMENTADO
- **Problema**: Kanban era inutilizável em dispositivos mobile (colunas muito pequenas)
- **Solução**: Nova visualização em lista para mobile com:
  - Filtro de status dropdown
  - Cards expandidos com todas as informações
  - Dropdown para mudar status directamente
  - Classes responsivas: `md:hidden` para lista, `hidden md:flex` para Kanban
- **Ficheiros modificados**: `/app/frontend/src/components/LeadsKanban.js` (novo componente `LeadListItem`)
- **Status**: ✅ IMPLEMENTADO E TESTADO

#### Bug Fix 6: Tabs do menu sobrepostas - CORRIGIDO
- **Problema**: No AdminDashboard, as tabs apareciam truncadas e sobrepostas no mobile
- **Solução**: 
  - TabsList com `inline-flex w-max min-w-full`
  - Container wrapper com `overflow-x-auto scrollbar-hide`
  - CSS `.scrollbar-hide` adicionado ao index.css
- **Ficheiros modificados**: 
  - `/app/frontend/src/pages/AdminDashboard.js`
  - `/app/frontend/src/index.css`
- **Status**: ✅ CORRIGIDO E TESTADO

#### Bug Fix 7: Botão "Ver Ficha" redireccionava ao login - CORRIGIDO
- **Problema**: Na lista de clientes, o botão "Ver Ficha" usava rota incorrecta `/processos/` em vez de `/process/`
- **Solução**: Corrigida navegação para usar `/process/{process_id}`
- **Ficheiros modificados**: `/app/frontend/src/pages/ClientsPage.js`
- **Status**: ✅ CORRIGIDO E TESTADO

#### Bug Fix 8: Clicar no nome do cliente - IMPLEMENTADO
- **Problema**: O nome do cliente na lista não era clicável
- **Solução**: Nome do cliente agora é um botão que navega para `/process/{process_id}`
- **Ficheiros modificados**: `/app/frontend/src/pages/ClientsPage.js`
- **Status**: ✅ IMPLEMENTADO E TESTADO

### ✅ Bug Fixes P0 Completos (Sessão 28 Parte 2) - 100% VERIFIED

#### P0: Clicar na Lead não abria modal - CORRIGIDO
- **Problema**: Utilizador reportou que clicar no cartão de lead não mostrava nada
- **Solução**: Adicionado `onClick={() => onEdit(lead)}` no componente Card + `e.stopPropagation()` em todos os botões de acção
- **Ficheiros modificados**: `/app/frontend/src/components/LeadsKanban.js`
- **Status**: ✅ CORRIGIDO E TESTADO (iteration_41)

#### P0: Dark Mode - Fundos brancos nos stats - CORRIGIDO
- **Problema**: Cards de estatísticas tinham fundos brancos que não se adaptavam ao dark mode
- **Solução**: Adicionadas classes `dark:bg-*-900/30` a todos os icon containers e badges
- **Ficheiros modificados**: `/app/frontend/src/pages/UnifiedLogsPage.js`
- **Escopo**: Tab Erros do Sistema + Tab Importações IA + severityConfig
- **Status**: ✅ CORRIGIDO E TESTADO (iteration_41)

### ✅ Funcionalidades P0 Completas (Sessão 28 - Parte 1) - 100% VERIFIED

#### P0: Sistema de Logs de Importação IA Melhorado - IMPLEMENTADO
- **Vista Lista com Selecção Múltipla**: Checkboxes individuais + "Selecionar Todos"
- **Vista Agrupada por Cliente**: Toggle "Lista/Clientes" com cards expandíveis
- **Resolução em Massa**: Barra de acções com "Marcar como Resolvidos"
- **Novos Endpoints**: 
  - `GET /api/admin/ai-import-logs-v2/grouped`
  - `POST /api/admin/ai-import-logs/bulk-resolve`
- **Status**: ✅ IMPLEMENTADO E TESTADO (iteration_40)

### ✅ Correcções P0 Completas (Sessão 27) - 100% VERIFIED

#### P0 #1: Dark Mode no Kanban do Gestor de Visitas - CORRIGIDO
- **Problema**: As colunas do Kanban não eram visíveis em dark mode (usavam `bg-gray-50` fixo)
- **Solução**: Trocado para classes dark-mode-aware `bg-muted/50 dark:bg-muted/30`
- **Ficheiros modificados**: `/app/frontend/src/components/LeadsKanban.js`
- **Status**: ✅ CORRIGIDO E TESTADO (iteration_39)

#### P0 #2: Botão "Criar Lead" da Importação HTML - CORRIGIDO
- **Problema**: O botão não funcionava porque os campos do scraper eram em português mas o modelo espera inglês
- **Solução**: Mapeamento de campos correcto + validação de URL (http/https)
- **Ficheiros modificados**: `/app/frontend/src/pages/IdealistaImportPage.js`
- **Status**: ✅ CORRIGIDO E TESTADO (iteration_39)

#### P0 #3: Extracção HTML mostra mais dados - MELHORADO
- **Problema**: A extracção de HTML mostrava poucos dados
- **Solução**: 
  - Prompt de extracção melhorado com 30+ campos
  - Novos campos: preco_m2, codigo_postal, area_bruta, area_terreno, suites, garagem, piso, elevador, varanda, vista, orientacao_solar, condominio, agencia_telefone, referencia, foto_principal, url_planta, url_video
  - UI actualizada para mostrar todos os campos em grid de 4 colunas
- **Ficheiros modificados**: 
  - `/app/backend/services/scraper.py` - prompts Gemini e OpenAI
  - `/app/frontend/src/pages/IdealistaImportPage.js` - display expandido
- **Status**: ✅ CORRIGIDO E TESTADO (iteration_39)

#### P0 #4: Link "Ver" levava para Login - CORRIGIDO
- **Problema**: Ao clicar "Ver" numa lead, ia para a página de login em vez do URL externo
- **Causa Raiz**: Leads criados sem URL válida tinham valores como `idealista-import-123456789`
- **Solução**: 
  - Validação de URL: só mostra link se começar com `http://` ou `https://`
  - Se URL inválida, mostra `—` em vez de link
  - Função `handleCreateLead` agora valida URLs antes de guardar
- **Ficheiros modificados**: `/app/frontend/src/components/LeadsKanban.js`
- **Status**: ✅ CORRIGIDO E TESTADO (iteration_39)

#### P0 #5: Fallback Gemini → OpenAI - IMPLEMENTADO
- **Problema**: Quando quota Gemini excedida, extracção falhava
- **Solução**: 
  - `analyze_with_ai()` agora tenta Gemini primeiro
  - Se `quota_exceeded`, automaticamente usa OpenAI gpt-4o-mini
  - Normalização de respostas aninhadas do OpenAI
- **Ficheiros modificados**: `/app/backend/services/scraper.py`
- **Status**: ✅ CORRIGIDO E TESTADO (iteration_39)

#### P0 #6: Erro 'list' object has no attribute 'get' - CORRIGIDO
- **Problema**: ai_document.py falhava quando IA retornava lista em vez de dict
- **Solução**: `parse_ai_response()` agora detecta e trata listas
- **Ficheiros modificados**: `/app/backend/services/ai_document.py`
- **Status**: ✅ CORRIGIDO

### ✅ Tarefas P1 Completas (Sessão 27)

#### P1: Botão "Importar HTML" no Gestor de Visitas - IMPLEMENTADO
- Botão no header do Kanban navega para `/admin/importar-idealista`
- **Status**: ✅ IMPLEMENTADO E TESTADO (iteration_39)

#### P1: Feedback Visual no Bookmarklet Avançado - MELHORADO
- Overlay visual mostra progresso
- **Status**: ✅ IMPLEMENTADO

#### P1: Mais sources detectados na importação HTML
- Adicionados: powerealestate, remax, era, century21, kellerwilliams, olx, bpi
- **Status**: ✅ IMPLEMENTADO

### ✅ Bug Fixes Anteriores (Sessão 25-26)
  - Status "paused" guardado na DB com timestamp
- **Ficheiros modificados**:
  - `/app/backend/routes/ai_bulk.py` - Endpoints POST /pause e POST /resume
  - `/app/frontend/src/pages/BackgroundJobsPage.js` - Handlers e UI para pausar/retomar
- **Novos Endpoints**:
  - `POST /api/ai/bulk/background-jobs/{job_id}/pause`
  - `POST /api/ai/bulk/background-jobs/{job_id}/resume`
- **Status**: ✅ VERIFICADO (100% testes passed - iteration_37)

#### P0: Página de Importação Idealista (HTML Paste) - IMPLEMENTADO
- **Problema**: O Idealista bloqueia scrapers com HTTP 403, impedindo importação directa de URLs
- **Solução**: Criada página para o utilizador colar o HTML da página manualmente
- **Funcionalidades implementadas**:
  - Página `/admin/importar-idealista` com instruções claras
  - Método "Colar Página": Ctrl+A, Ctrl+C no browser → colar no CRM
  - Método "Bookmarklet": Um-clique para copiar dados automaticamente
  - Extracção de dados com IA (título, preço, localização, tipologia, área, agente)
  - Botão "Criar Lead" após extracção bem-sucedida
- **Ficheiros criados/modificados**:
  - `/app/frontend/src/pages/IdealistaImportPage.js` - Nova página de importação
  - `/app/frontend/src/App.js` - Adicionada rota `/admin/importar-idealista`
  - `/app/frontend/src/layouts/DashboardLayout.js` - Link "Importar Idealista" no menu Sistema
- **Endpoint backend**: `POST /api/scraper/extract-html`
- **Status**: ✅ VERIFICADO (100% testes passed - iteration_36)

#### P0: Funcionalidade Cancelar Jobs em Background - IMPLEMENTADO
- **Problema**: Utilizador não conseguia parar jobs de importação em execução
- **Solução**: Adicionado botão "Cancelar" na página de Background Jobs
- **Funcionalidades implementadas**:
  - Botão "Cancelar" só aparece para jobs com status "running"
  - Confirmação visual de cancelamento com spinner
  - Job é marcado como "cancelled" na DB
  - Toast de confirmação após cancelamento
- **Ficheiros modificados**:
  - `/app/frontend/src/pages/BackgroundJobsPage.js` - UI do botão cancelar (linhas 160-183)
- **Endpoint backend**: `POST /api/ai/bulk/background-jobs/{job_id}/cancel`
- **Status**: ✅ VERIFICADO (100% testes passed - iteration_36)

### ✅ Tarefas Completadas (Sessão 24)

#### P0: Background Jobs - Correcções - IMPLEMENTADO
- **Problema**: Jobs de importação massiva não apareciam na página de processos em background
- **Causa Raiz**: O novo fluxo agregado guardava jobs na DB mas o frontend usava ID errado para actualizar progresso
- **Solução**:
  - Novo endpoint `POST /api/ai/bulk/background-job/{job_id}/progress` para actualizar progresso
  - Novo endpoint `POST /api/ai/bulk/background-jobs/clear-all` para limpar jobs stuck
  - Frontend actualizado para usar o endpoint correcto de progresso
- **Status**: ✅ VERIFICADO (100% testes passed - iteration_35)

#### P0: Suporte para Documentos Estrangeiros (França) - IMPLEMENTADO
- **Problema**: Clientes portugueses emigrados em França enviavam documentos em francês que não eram correctamente extraídos
- **Solução**:
  - Prompts de extração actualizados para suportar:
    - Recibos franceses (Bulletin de paie / Fiche de paie)
    - Declarações IRS francesas (Avis d'impôt sur le revenu)
    - Declarações espanholas (Nómina, IRPF)
  - Novos campos suportados: `pais_origem`, `moeda`, `nif_fr`, `morada_fiscal_fr`
  - Agregador actualizado para processar salários de diferentes países
  - Detecção automática de tipo de documento melhorada para ficheiros em francês
- **Ficheiros modificados**:
  - `/app/backend/services/ai_document.py` - Prompts multi-língua (linhas 726-810)
  - `/app/backend/services/documents/data_aggregator.py` - Processamento de documentos estrangeiros
- **Status**: ✅ VERIFICADO (20/20 testes passed)

#### ⚠️ Idealista.pt Scraping - LIMITAÇÃO CONHECIDA
- **Problema**: Importação de URLs do Idealista.pt não funciona (HTTP 403)
- **Investigação**:
  - Integrado ScraperAPI com modo `ultra_premium`
  - Mesmo com ScraperAPI, o Idealista continua a bloquear (403)
- **Conclusão**: O Idealista tem protecção anti-bot muito agressiva que bloqueia TODOS os scrapers
- **Alternativas sugeridas**:
  1. Parceria/API directa com Idealista
  2. Utilizador cola o HTML da página manualmente
  3. Extensão de browser para extrair dados
- **Status**: ⏳ LIMITAÇÃO DO SERVIÇO EXTERNO

### ✅ Tarefas Completadas (Sessão 23)

#### P0: Importação Agregada "Cliente a Cliente" - IMPLEMENTADO E TESTADO
- **Problema**: O utilizador pediu nova lógica de importação massiva de documentos que:
  1. Processa documentos cliente a cliente (não documento a documento)
  2. Acumula dados extraídos em memória antes de salvar
  3. Deduplica campos (usa valor mais recente quando há conflito)
  4. Agrega salários por empresa (lista separada + soma total)
  5. Salva uma única vez por cliente após processar todos os documentos
- **Solução Implementada**:
  - Criado novo serviço `data_aggregator.py` com classes `ClientDataAggregator` e `SessionAggregator`
  - Novos endpoints de sessão agregada no `ai_bulk.py`
  - Frontend actualizado para usar modo agregado
- **Lógica de Salários**:
  - Salários de empresas diferentes são agregados (lista com N entradas + soma total)
  - Salários da mesma empresa mantêm apenas a entrada mais recente
  - Normalização de nomes de empresa (remove Lda, SA, Unipessoal, etc.)
- **Novos Endpoints**:
  - `POST /api/ai/bulk/aggregated-session/start` - Criar sessão agregada
  - `POST /api/ai/bulk/aggregated-session/{id}/analyze` - Analisar ficheiro e agregar dados
  - `GET /api/ai/bulk/aggregated-session/{id}/status` - Estado da sessão
  - `POST /api/ai/bulk/aggregated-session/{id}/finish` - Consolidar e salvar dados
- **Ficheiros criados/modificados**:
  - `/app/backend/services/documents/data_aggregator.py` (NOVO) - Classes de agregação
  - `/app/backend/routes/ai_bulk.py` - Novos endpoints agregados
  - `/app/frontend/src/components/BulkDocumentUpload.js` - Integração com modo agregado
- **Status**: ✅ IMPLEMENTADO E VERIFICADO (15/15 testes passed - iteration_34)

### ✅ Tarefas Completadas (Sessão 22)

#### P0: ModuleNotFoundError - emergentintegrations - CORRIGIDO
- **Problema**: Erro `ModuleNotFoundError: No module named 'emergentintegrations'` durante importação massiva AI
- **Causa Raiz**: O pacote `emergentintegrations` não estava persistido no `requirements.txt`
- **Solução**: 
  - Instalado pacote via `pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/`
  - Actualizado `requirements.txt` com `pip freeze`
  - Corrigido `ai_improvement_agent.py` para usar sintaxe correcta do LlmChat (requer session_id e system_message)
- **Ficheiros modificados**:
  - `/app/backend/requirements.txt` - Adicionado emergentintegrations
  - `/app/backend/services/ai_improvement_agent.py` - Corrigida inicialização do LlmChat
- **Status**: ✅ CORRIGIDO E VERIFICADO (Testes iteration_33)

#### P1: Background Jobs não aparecem - CORRIGIDO
- **Problema**: Ficheiros importados via AI não apareciam na página de "Processos em Background"
- **Causa Raiz**: Jobs eram guardados apenas em memória, perdidos ao reiniciar o servidor
- **Solução**: 
  - Criado sistema de persistência na colecção MongoDB `background_jobs`
  - Novos endpoints para criar/actualizar/finalizar sessões de importação
  - Frontend actualizado para criar sessões no backend durante upload
- **Novos Endpoints**:
  - `POST /api/ai/bulk/import-session/start` - Criar sessão de importação
  - `POST /api/ai/bulk/import-session/{id}/update` - Actualizar progresso
  - `POST /api/ai/bulk/import-session/{id}/finish` - Finalizar sessão
- **Ficheiros modificados**:
  - `/app/backend/routes/ai_bulk.py` - Novos endpoints e funções de persistência (linhas 51-170)
  - `/app/frontend/src/components/BulkDocumentUpload.js` - Integração com backend
- **Status**: ✅ CORRIGIDO E VERIFICADO (Testes iteration_33)

### ✅ Tarefas Completadas (Sessão 21)

#### P0: Endpoint de Listagem de Ficheiros por Cliente - COMPLETO
- **Problema**: Documentos não apareciam na página do cliente porque o endpoint `/onedrive/files/{client_name}` não existia
- **Solução**: Criado novo endpoint que busca ficheiros do S3 pelo nome do cliente
- **Ficheiro**: `/app/backend/routes/onedrive.py` (linhas 231-269)
- **Endpoint**: `GET /api/onedrive/files/{client_name}`
- **Resposta**: `{files: {...}, folders: [], categories: [...], stats: {...}}`
- **Status**: ✅ CORRIGIDO E VERIFICADO (Testes iteration_32)

#### P2: Selecção Múltipla de Logs para Resolução em Massa - COMPLETO
- **Problema**: Utilizador pediu funcionalidade de "seleccionar erros" nos logs
- **Solução**: Implementado sistema de checkboxes com acções em massa
- **Funcionalidades**:
  - Checkbox "Seleccionar Todos" no cabeçalho da tabela
  - Checkboxes individuais por linha (desactivados para logs já resolvidos)
  - Barra de acções em massa com contador de logs seleccionados
  - Botões "Limpar Selecção" e "Marcar como Resolvidos"
- **Ficheiros**:
  - `/app/frontend/src/pages/UnifiedLogsPage.js` - UI de selecção
  - `/app/backend/routes/admin.py` - Endpoint `POST /api/admin/system-logs/bulk-resolve`
  - `/app/backend/services/system_error_logger.py` - Função `bulk_mark_as_resolved`
- **Status**: ✅ CORRIGIDO E VERIFICADO (Testes iteration_32)

#### P1: Remoção da Aba "Configurações" do StaffDashboard - COMPLETO
- **Problema**: Utilizador reportou aba "Configurações" indesejada no dashboard
- **Solução**: Removido TabsTrigger e TabsContent para a aba "Configurações" do StaffDashboard.js
- **Ficheiro**: `/app/frontend/src/pages/StaffDashboard.js`
- **Status**: ✅ CORRIGIDO E VERIFICADO (Testes iteration_31)

#### P1: Correcção da Sidebar na Página "Mapeamento NIF" - COMPLETO
- **Problema**: Sidebar desaparecia na página /admin/mapeamentos-nif
- **Solução**: Envolvido o conteúdo da página com DashboardLayout
- **Ficheiro**: `/app/frontend/src/pages/NIFMappingsPage.js`
- **Status**: ✅ CORRIGIDO E VERIFICADO (Testes iteration_31)

#### P1: Sistema de Logs para Importação IA Massiva - COMPLETO
- **Problema**: Utilizador pediu sistema de logs para ver sucessos E erros das importações
- **Solução**: Sistema integrado na página unificada de logs com:
  - Registo de Sucessos E Erros
  - Categorização de dados por tabs (Dados Pessoais, Imóvel, Financiamento, Outros)
  - Nova colecção MongoDB `ai_import_logs`
- **Status**: ✅ COMPLETO E TESTADO

### Sessão 19 - Anteriormente Completado

#### P0: Correcção dos Filtros do Kanban - COMPLETO
- **Problema**: Quando consultor_id=none E mediador_id=none eram passados, a segunda atribuição de `query["$or"]` sobrescrevia a primeira
- **Solução**: Implementado uso de `$and` para combinar múltiplas condições de filtro
- **Ficheiro**: `/app/backend/routes/processes.py` (linhas 327-356)
- **Testes**: 
  - Sem filtros: 218 processos
  - consultor_id=none: 78 processos
  - mediador_id=none: 213 processos
  - Ambos none: 74 processos (interseção correcta)
- **Status**: ✅ COMPLETO E TESTADO

#### P0: Correcção da Exclusão de Clientes - COMPLETO
- **Problema**: O endpoint DELETE /api/clients/{id} procurava na colecção `clients` mas os dados estão em `processes`
- **Solução**: Modificado para procurar primeiro em `processes` e depois em `clients` para compatibilidade
- **Funcionalidade adicional**: Agora também elimina documentos, tarefas e histórico associados
- **Ficheiro**: `/app/backend/routes/clients.py` (linhas 571-632)
- **Status**: ✅ COMPLETO E TESTADO

#### P0: Verificação de Preferências de Email - VERIFICADO
- **Endpoints**: 
  - PUT /api/auth/preferences (utilizador actual)
  - GET/PUT /api/admin/notification-preferences (admin para outros utilizadores)
- **Status**: ✅ A FUNCIONAR CORRECTAMENTE

#### P0: Dependência libmagic - RESOLVIDO
- **Problema**: Backend falhava ao iniciar por falta de libmagic.so.1
- **Solução**: Instalado libmagic1 e libmagic-dev via apt-get
- **Status**: ✅ RESOLVIDO (temporariamente - precisa de solução permanente no Dockerfile)

### Sessão 19 - Continuação

#### Correcções de Ambiente
- **libmagic permanente**: Adicionada verificação automática no `server.py` que instala `libmagic1` se não estiver presente ao iniciar o backend

#### Simplificação de UI
- **Removida página "Erros de Importação"**: Erros agora são registados nos "Logs do Sistema" para visualização unificada
- **Integração com System Logs**: A função `log_import_error` agora também grava na colecção `system_error_logs`

#### Verificações de Funcionalidades Existentes
- **"Gestor de Visitas"** (antigo Leads): Verificado como 100% funcional
  - Scraping de URLs implementado
  - Formulário completo para criar leads
  - Kanban drag-and-drop funcional

### Sessão 18 - Anteriormente Completado

### ✅ Tarefas Completadas (Sessão 18)

#### P0: Lógica de Processamento de Documentos (Cenários A/B) - COMPLETO
- **Objectivo**: Implementar lógica diferenciada para upload de documentos
- **Cenário A (Upload Massivo)**: Nome da pasta raiz define o nome do cliente
- **Cenário B (Página do Cliente)**: Parâmetro `force_client_id` associa todos os documentos ao cliente específico
- **Implementação**:
  - Backend: `POST /api/ai/bulk/analyze-single` aceita `force_client_id` como Form parameter
  - Frontend: `BulkDocumentUpload.js` aceita props `forceClientId` e `forceClientName`
  - Quando `forceClientId` está definido, ignora verificação de cliente e processa todos os ficheiros
- **Ficheiros Modificados**:
  - `/app/backend/routes/ai_bulk.py` - Added Form import, force_client_id parameter
  - `/app/frontend/src/components/BulkDocumentUpload.js` - Full refactor for Scenario A/B support
- **Status**: ✅ COMPLETO E TESTADO

#### P1: Skeleton Loaders em Todas as Páginas - COMPLETO
- **Objectivo**: Melhorar UX durante carregamento de dados
- **Implementação**:
  - `ProcessesPage.js`: `TableSkeleton` com 8 rows x 7 columns durante loading
  - `KanbanBoard.js`: Skeleton loader com 5 colunas e 3 cards cada durante loading
  - `ClientsPage.js`: `TableSkeleton` já implementado anteriormente
- **Componentes**: `/app/frontend/src/components/ui/skeletons.jsx`
- **Status**: ✅ COMPLETO E TESTADO

#### Enhancement: Upload de Documentos na Página do Cliente - COMPLETO
- **Objectivo**: Permitir upload directo de documentos na ficha do cliente
- **Implementação**:
  - Adicionado botão "Upload Docs" na página de detalhes do processo
  - Botão usa cor verde-teal para diferenciar do upload massivo (roxo)
  - Usa `BulkDocumentUpload` com `forceClientId={processId}` e `forceClientName={clientName}`
  - Instruções simplificadas no modal para contexto de cliente específico
- **Ficheiros Modificados**:
  - `/app/frontend/src/pages/ProcessDetails.js` - Import e uso do BulkDocumentUpload
  - `/app/frontend/src/components/BulkDocumentUpload.js` - Suporte a variant="compact" e UI adaptada
- **Status**: ✅ COMPLETO E TESTADO

#### Enhancement: Barra de Progresso Global para Uploads - COMPLETO
- **Objectivo**: Mostrar progresso de uploads mesmo quando o utilizador navega para outras páginas
- **Implementação**:
  - Criado `UploadProgressContext` para gestão global de estado de uploads
  - Criado componente `GlobalUploadProgress` fixo no canto inferior direito
  - Integrado no `App.js` com `UploadProgressProvider`
  - `BulkDocumentUpload` actualizado para usar o contexto global
- **Funcionalidades**:
  - Mostra progresso em tempo real (ficheiro actual, % concluído)
  - Minimizável para ícone flutuante
  - Auto-remove após conclusão com sucesso (5 segundos)
  - Múltiplos uploads simultâneos suportados
- **Ficheiros Criados**:
  - `/app/frontend/src/contexts/UploadProgressContext.js`
  - `/app/frontend/src/components/GlobalUploadProgress.js`
- **Ficheiros Modificados**:
  - `/app/frontend/src/App.js` - Import e integração do provider e componente
  - `/app/frontend/src/components/BulkDocumentUpload.js` - Uso do contexto global
- **Status**: ✅ COMPLETO

### ✅ Tarefas Completadas (Sessão 17)

#### P1: Migração CRA → Vite - COMPLETO
- **Objectivo**: Migrar frontend de Create React App para Vite para melhor performance
- **Alterações**:
  - Criado `vite.config.js` com configuração para JSX, variáveis de ambiente REACT_APP_*
  - Criado novo `index.html` na raiz do frontend
  - Criado `src/main.jsx` como entry point
  - Actualizado `package.json` com scripts Vite
  - Actualizado `tailwind.config.js` e `postcss.config.js` para ESM
- **Benefícios**: HMR instantâneo, builds mais rápidos, melhor developer experience
- **Status**: ✅ COMPLETO E TESTADO

#### P1: Correcção Erro S3 Region - COMPLETO
- **Problema**: Região S3 guardada como 'Europa (Estocolmo) eu-north-1' em vez de 'eu-north-1'
- **Solução**: Corrigido valor na base de dados via script
- **Status**: ✅ COMPLETO

#### P1: Enum para Roles (UserRoleEnum) - COMPLETO
- **Problema**: Magic strings para roles (ex: "intermediario", "ceo") sem type-safety
- **Solução**: Criado `UserRoleEnum(str, Enum)` em `backend/models/auth.py`
- **Benefícios**: Evita erros de digitação, auto-complete no IDE, validação em runtime
- **Ficheiros**: `/app/backend/models/auth.py`
- **Status**: ✅ COMPLETO

#### P1: Remoção de "OneDrive não configurado" - COMPLETO
- **Problema**: Mensagens específicas de "OneDrive" quando storage é configurável
- **Solução**:
  - Criado novo componente `DriveLinks.js` (genérico)
  - Criado endpoint `/api/system-config/storage-info`
  - Removidas todas as mensagens "OneDrive não configurado"
  - Terminologia actualizada: "Pasta Drive" em vez de "Pasta OneDrive"
- **Status**: ✅ COMPLETO E TESTADO

#### P1: Processamento de Ficheiros em Threads - COMPLETO
- **Problema**: Processamento de Excel/PDF em async def bloqueava event loop
- **Solução**: Criado `backend/services/file_processor.py` com ThreadPoolExecutor
- **Implementação**:
  - Funções síncronas: `process_excel_sync()`, `process_pdf_sync()`
  - Wrappers async: `process_excel_async()`, `process_pdf_async()`
  - Usa `run_in_executor()` para não bloquear
- **Status**: ✅ COMPLETO

### 📋 Tarefas Pendentes

#### P2 (Média Prioridade)
- [ ] Implementar rate limiting no backend
- [ ] Paginação cursor-based para listas grandes

#### P3 (Baixa Prioridade)
- [ ] Refactoring do `processes.py` (ficheiro muito grande)
- [ ] Cache Redis para dados frequentes (nota: Redis não está disponível no ambiente actual)

### Credenciais de Teste
- **Admin**: admin@admin.com / admin
- **Consultor**: flaviosilva@powerealestate.pt / flavio123

### Ficheiros Importantes
- `/app/frontend/vite.config.js` - Configuração Vite
- `/app/backend/models/auth.py` - UserRoleEnum
- `/app/backend/services/file_processor.py` - Processamento ficheiros em threads
- `/app/frontend/src/components/DriveLinks.js` - Componente de links genérico
- `/app/backend/routes/system_config.py` - Endpoint storage-info
- `/app/frontend/src/components/BulkDocumentUpload.js` - Upload massivo com Cenários A/B
- `/app/backend/routes/ai_bulk.py` - Endpoint analyze-single com force_client_id

### Notas Técnicas
- **Storage Dinâmico**: O admin escolhe o provider (S3, Google Drive, OneDrive, Dropbox) nas configurações do sistema
- **force_client_id**: Quando na página de um cliente, todos os documentos são associados a esse cliente independentemente do nome da pasta
- **ThreadPoolExecutor**: 4 workers para processamento de PDF/Excel (suficiente para operações I/O-bound)
- **Skeleton Loaders**: Componentes reutilizáveis em `/app/frontend/src/components/ui/skeletons.jsx`

### Test Reports
- `/app/test_reports/iteration_29.json` - Último teste completo (100% pass rate)
