# CreditoIMO - Product Requirements Document

## Problema Original
Aplicação de gestão de processos de crédito habitação e transações imobiliárias que funciona como "espelho" de um quadro Trello, com sincronização bidirecional.

## Stack Técnica
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, Pydantic, Motor (MongoDB async)
- **Base de Dados**: MongoDB Atlas (Cluster: cluster0.c8livu.mongodb.net)
  - **Desenvolvimento/Testes**: `powerprecision_dev`
  - **Produção**: `powerprecision`
- **Integrações**: Trello API & Webhooks, IMAP/SMTP (emails), Cloud Storage (OneDrive, S3, Google Drive), Gemini 2.0 Flash (scraping), AWS S3 (documentos)

## Última Actualização - 13 Fevereiro 2026 (Sessão 16)

### ✅ Tarefas P1 Completas

#### P1: Unificação das Abas "Documentos" e "Drive" - COMPLETO
- **Problema**: Existiam duas secções separadas: "Documentos" (S3) e "Links Drive" (OneDrive Links)
- **Solução**: Criado componente `UnifiedDocumentsPanel.js` que combina ambas funcionalidades
- **Nova Estrutura**:
  - Accordion "Documentos" no sidebar direito da ficha do processo
  - Dentro: tabs "Ficheiros" (upload S3) e "Links Drive" (links externos)
- **Ficheiros Modificados**:
  - `/app/frontend/src/components/UnifiedDocumentsPanel.js` (novo)
  - `/app/frontend/src/pages/ProcessDetails.js` (integração)
- **Status**: ✅ COMPLETO E TESTADO

#### P1: Funcionalidade de Emails com CC - COMPLETO
- **Problema**: Sistema não capturava emails em CC
- **Solução**: 
  - Backend: Adicionado campo `cc_emails` na sincronização IMAP (3 locais)
  - Frontend: Exibição de CC na lista de emails do processo
- **Ficheiros Modificados**:
  - `/app/backend/services/email_service.py`
  - `/app/frontend/src/components/EmailHistoryPanel.js`
- **Status**: ✅ COMPLETO

### ✅ Bugs Corrigidos (Sessão 16)

#### Bug P0: Workflow do Consultor Não Funcionava - CORRIGIDO
- **Problema Reportado**: Utilizador `flaviosilva@powerealestate.pt` (role consultor) não conseguia realizar operações básicas (adicionar links, criar processos)
- **Causa Raiz 1**: Endpoint `POST /api/processes/create-client` não incluía role `consultor` na lista de permitidos
- **Causa Raiz 2**: Endpoint `GET /api/onedrive/links/{process_id}` retornava 404 para processos sem links (bug de dict vazio em Python)
- **Causa Raiz 3**: Endpoints `GET/POST/PUT/DELETE /api/onedrive/links/{process_id}` não existiam no backend
- **Soluções Implementadas**:
  1. Adicionado `consultor` à lista de roles permitidos em `/create-client`
  2. Criados endpoints completos para gestão de links (GET, POST, PUT, DELETE)
  3. Corrigida verificação de existência de processo (separada da busca de links)
- **Ficheiros Modificados**: `/app/backend/routes/onedrive.py`, `/app/backend/routes/processes.py`
- **Testes**: 13/13 testes passaram (100% success rate)
- **Status**: ✅ CORRIGIDO E TESTADO

#### Bug P1: Dark Mode com Problemas de Visualização - CORRIGIDO
- **Problema Reportado**: Ícones que não se viam bem, textos difíceis de ler, Kanban com má visualização
- **Soluções Implementadas**:
  1. Reformuladas variáveis CSS do tema escuro para melhor contraste
  2. Adicionados estilos específicos para:
     - Colunas do Kanban (cores de fundo e headers)
     - Cartões de processos (fundo e bordas)
     - Badges de status (cores adaptadas)
     - Inputs, tabelas e textos
  3. Melhorada visibilidade de ícones em modo escuro
- **Ficheiros Modificados**: `/app/frontend/src/index.css`, `/app/frontend/src/components/KanbanBoard.js`
- **Status**: ✅ CORRIGIDO

#### Bug P1: Logs de Erro Não Apareciam - CORRIGIDO
- **Problema Reportado**: Erros reportados pelo utilizador não apareciam no menu "Log do Sistema"
- **Causa**: O sistema apenas logava erros de importação, não erros HTTP gerais
- **Solução**: Adicionado exception handler global no FastAPI que regista automaticamente erros 4xx e 5xx no sistema de logs
- **Ficheiro Modificado**: `/app/backend/server.py`
- **Status**: ✅ CORRIGIDO

#### Nomenclatura: OneDrive → Drive - ACTUALIZADO
- **Problema**: Sistema usava "OneDrive" quando suporta múltiplos providers de cloud
- **Solução**: Substituído todas as referências visíveis ao utilizador de "OneDrive" para "Drive" genérico
- **Ficheiros Modificados**: Múltiplos ficheiros frontend (AdminDashboard, ConsultorDashboard, MediadorDashboard, BackupsPage, OneDriveLinks, ProcessDetails)
- **Status**: ✅ ACTUALIZADO

#### Tab "Links Drive" Renomeada para "Drive" - ACTUALIZADO
- **Local**: ProcessDetails.js - Side Tabs
- **Status**: ✅ ACTUALIZADO

### Novos Endpoints de Links de Drive
- `GET /api/onedrive/links/{process_id}` - Listar links de um processo
- `POST /api/onedrive/links/{process_id}` - Adicionar link (suporta OneDrive, Google Drive, S3, SharePoint)
- `PUT /api/onedrive/links/{process_id}/{link_id}` - Actualizar link
- `DELETE /api/onedrive/links/{process_id}/{link_id}` - Remover link

### Credenciais de Teste Verificadas
- **Consultor**: `flaviosilva@powerealestate.pt` / `flavio123` (role: consultor)
- **Admin**: `admin@admin.com` / `admin` (role: admin)

---

## Última Actualização - 13 Fevereiro 2026 (Sessão 15 - Parte 2)

### ✅ Funcionalidades Implementadas (Sessão 15 - Parte 2)

#### Novas Páginas de Administração
1. **NIFMappingsPage** (`/admin/mapeamentos-nif`)
   - Visualizar mapeamentos pasta→cliente em cache
   - Adicionar mapeamentos manualmente
   - Limpar cache (memória + DB)
   - Status: ✅ IMPLEMENTADO

2. **ImportErrorsPage** (`/admin/erros-importacao`)
   - Dashboard de erros de upload massivo
   - Filtros por tipo de erro
   - Botão "Resolver" para associar pastas a clientes
   - Exportar CSV de erros
   - Status: ✅ IMPLEMENTADO

#### Melhorias de User Experience (Doc 4)
1. **Dark Mode Toggle**
   - Alterna entre tema claro/escuro
   - Detecta preferência do sistema
   - Persiste escolha no localStorage
   - Ficheiros: `ThemeContext.js`, `index.css` (variáveis .dark)
   - Status: ✅ IMPLEMENTADO

2. **Keyboard Shortcuts (Ctrl+K)**
   - `Ctrl+K` - Abrir pesquisa global
   - `Ctrl+N` - Novo processo
   - `Ctrl+/` - Mostrar atalhos
   - `ESC` - Fechar modal
   - Ficheiros: `useKeyboardShortcuts.js`, `GlobalSearchModal.jsx`
   - Status: ✅ IMPLEMENTADO

3. **Global Search Modal**
   - Pesquisa unificada em processos, clientes e tarefas
   - Navegação por teclado (↑↓ Enter)
   - Resultados instantâneos com debounce
   - Endpoint: `GET /api/search/global`
   - Status: ✅ IMPLEMENTADO

4. **Mobile Bottom Navigation**
   - Navegação fixa no fundo para mobile
   - Links: Kanban, Tarefas, Agenda, Perfil
   - Visível apenas em ecrãs < md
   - Ficheiro: `MobileBottomNav.jsx`
   - Status: ✅ IMPLEMENTADO

5. **Skeleton Loaders**
   - Componentes de loading elegantes
   - Tipos: ProcessCard, Table, Stats, Form
   - Ficheiro: `skeletons.jsx`
   - Status: ✅ IMPLEMENTADO

6. **Auto-save Draft (D1)**
   - Guarda automaticamente rascunho no localStorage
   - Debounce de 2 segundos
   - Detecta rascunho ao reabrir formulário
   - Limpa após submissão bem sucedida
   - Ficheiro: `PublicClientForm.js`
   - Status: ✅ IMPLEMENTADO

7. **Progress Bar com Percentagem (D2)**
   - Mostra "Passo X de Y"
   - Percentagem de campos obrigatórios preenchidos
   - Indicadores visuais de passos (círculos)
   - Componente: `FormProgressBar`
   - Status: ✅ IMPLEMENTADO

8. **Acessibilidade (D7)**
   - Focus outlines visíveis (`:focus-visible`)
   - Skip link para navegação por teclado
   - Touch targets mínimos 44x44px para mobile
   - Respeita `prefers-reduced-motion`
   - Safe area padding para notch
   - Scrollbar estilizada
   - Ficheiro: `index.css`
   - Status: ✅ IMPLEMENTADO

#### Novos Endpoints Backend
- `GET /api/search/global` - Pesquisa unificada
- `GET /api/search/processes` - Pesquisa avançada processos
- `GET /api/search/suggestions` - Sugestões de pesquisa

#### Scraper Idealista (Doc 1) - JÁ EXISTENTE
- ✅ `agency_link` - Link para página da agência
- ✅ `referencia` - Referência do imóvel
- ✅ `certificado_energetico` - Certificado energético
- ✅ Deep link navigation
- ✅ Extracção de telefone de agências

### ✅ Cache de Sessão NIF (Item 17) - COM PERSISTÊNCIA
- **Problema**: Documentos da mesma pasta precisavam de matching por nome repetidamente
- **Solução**: Quando um CC é analisado e o NIF extraído, o mapeamento pasta→cliente é guardado em cache E na base de dados
- **Persistência**: 
  - Mapeamentos guardados na coleção `nif_mappings` da MongoDB
  - Sobrevivem a reinícios do servidor
  - TTL de 30 dias (automático)
- **Benefícios**:
  - Lookup instantâneo para documentos subsequentes da mesma pasta
  - Redução de chamadas fuzzy matching à base de dados
  - Maior fiabilidade (NIF é único e imutável)
  - Mapeamentos persistem entre sessões de upload
- **Ficheiro**: `/app/backend/routes/ai_bulk.py`
- **Funções Adicionadas**:
  - `cache_nif_mapping()` - Guardar mapeamento
  - `get_cached_nif_mapping()` - Obter mapeamento
  - `find_client_by_nif()` - Encontrar cliente por NIF
  - `clear_expired_nif_cache()` - Limpeza automática
- **Novos Endpoints**:
  - `GET /api/ai/bulk/nif-cache/stats` - Ver estatísticas do cache
  - `POST /api/ai/bulk/nif-cache/clear` - Limpar cache
  - `POST /api/ai/bulk/nif-cache/add-mapping` - Adicionar mapeamento manual
- **TTL**: 2 horas (sessão típica de upload)
- **Status**: ✅ IMPLEMENTADO E TESTADO

### ✅ Bugs Corrigidos (Sessão 15)

#### Bug P0: Erro "Acesso Negado" para Consultores - CORRIGIDO
- **Problema**: O utilizador Flávio (consultor) não conseguia aceder à ficha da cliente Bruna Caetano
- **Causa Raiz**: A função `can_view_process()` verificava campos incorrectos (`consultant_id`, `mediador_id`) em vez dos campos reais (`assigned_consultor_id`, `assigned_mediador_id`)
- **Solução Implementada**:
  1. Corrigida função `can_view_process()` em `/app/backend/services/process_service.py`
  2. Alterada lógica para permitir que TODOS os staff vejam TODOS os processos
  3. Atribuído processo Bruna Caetano ao Flávio da Silva
- **Ficheiros Modificados**: `/app/backend/services/process_service.py`
- **Nova Lógica de Permissões**:
  - Staff (admin, ceo, diretor, administrativo, consultor, mediador, intermediario): vêem TODOS os processos
  - Clientes: apenas os seus próprios processos
- **Status**: ✅ CORRIGIDO E TESTADO

#### Clarificação: Emails Monitorizados - FUNCIONALIDADE EXISTENTE
- **Situação**: Utilizador não encontrava a funcionalidade de adicionar emails à pesquisa
- **Localização**: Botão de engrenagem (⚙️) no cabeçalho do painel "Histórico de Emails"
- **Como Usar**:
  1. Abrir ficha do processo
  2. Ir ao painel "Histórico de Emails" 
  3. Clicar no ícone ⚙️ (Settings)
  4. Adicionar emails adicionais no diálogo "Emails Monitorizados"
- **Ficheiro**: `/app/frontend/src/components/EmailHistoryPanel.js` (linhas 302-309, 551-660)
- **Status**: ✅ FUNCIONALIDADE JÁ EXISTIA - Documentado para referência

---

## Última Actualização - 13 Fevereiro 2026 (Sessão 14 - Continuação)

### ✅ Bugs Corrigidos (Sessão 14 - Continuação)

#### Bug 1: "Adicionar Link" mencionava OneDrive - CORRIGIDO
- **Problema**: O diálogo dizia "OneDrive" quando o sistema suporta múltiplos drives
- **Solução**: Mudado todos os textos de "OneDrive" para "Drive" genérico
- **Ficheiros**: `/app/frontend/src/components/OneDriveLinks.js`
- **Status**: ✅ CORRIGIDO

#### Bug 2: Links S3 davam erro "Not Found" - CORRIGIDO
- **Problema**: Validação só aceitava URLs do OneDrive
- **Solução**: Expandida validação para aceitar S3, Google Drive, SharePoint, e qualquer HTTP/HTTPS
- **Ficheiros**: `/app/backend/routes/onedrive.py`
- **Padrões aceites**: `s3://`, `https://drive.google.com/`, `.sharepoint.com/`, `https://1drv.ms/`
- **Status**: ✅ CORRIGIDO E TESTADO

#### Bug 3: Router OneDrive não estava registado - CORRIGIDO
- **Problema**: Router de onedrive não estava incluído no server.py
- **Solução**: Adicionado import e include_router para onedrive_router
- **Ficheiro**: `/app/backend/server.py`
- **Status**: ✅ CORRIGIDO

### ✅ Novas Funcionalidades UI (Sessão 14 - Continuação)

#### 1. Página de Treino do Agente IA - IMPLEMENTADO
- **Rota**: `/configuracoes/treino-ia`
- **Funcionalidades**:
  - CRUD de entradas de treino
  - 5 categorias: Tipos de Documentos, Mapeamento de Campos, Padrões de Clientes, Regras Personalizadas, Dicas de Extração
  - Visualização do prompt gerado
  - Activar/desactivar entradas
- **Ficheiro**: `/app/frontend/src/pages/AITrainingPage.js`
- **Status**: ✅ IMPLEMENTADO

#### 2. Página de Processos em Background - IMPLEMENTADO
- **Rota**: `/admin/processos-background`
- **Funcionalidades**:
  - Visualização de jobs em tempo real (auto-refresh 5s)
  - Filtros por estado (running, success, failed)
  - Barra de progresso para jobs a correr
  - Limpeza de jobs terminados
- **Ficheiro**: `/app/frontend/src/pages/BackgroundJobsPage.js`
- **Status**: ✅ IMPLEMENTADO

#### 3. Novos Links no Menu Lateral - IMPLEMENTADO
- **Ferramentas IA**: Adicionado "Treino do Agente"
- **Sistema**: Adicionado "Processos Background"
- **Ficheiro**: `/app/frontend/src/layouts/DashboardLayout.js`
- **Status**: ✅ IMPLEMENTADO

### Sobre Emails Monitorizados
- **Funcionalidade existe**: Botão de Settings (engrenagem) no painel de Histórico de Email
- **Como usar**: Clicar no ícone ⚙️ no canto superior direito do painel de emails
- **Ficheiro**: `/app/frontend/src/components/EmailHistoryPanel.js` (linhas 550-665)

---

## Última Actualização - 13 Fevereiro 2026 (Sessão 14)

### ✅ Funcionalidades Implementadas (Sessão 14)

#### 1. Security Headers Middleware - IMPLEMENTADO
- **X-Frame-Options**: DENY (previne clickjacking)
- **X-Content-Type-Options**: nosniff (previne MIME-type sniffing)
- **X-XSS-Protection**: 1; mode=block
- **Strict-Transport-Security**: max-age=31536000; includeSubDomains
- **Referrer-Policy**: strict-origin-when-cross-origin
- **Content-Security-Policy**: default-src 'self'; frame-ancestors 'none'
- **Permissions-Policy**: camera=(), microphone=(), etc.
- **Ficheiro**: `/app/backend/server.py` (linhas 74-129)
- **Status**: ✅ IMPLEMENTADO E TESTADO

#### 2. Input Sanitization - IMPLEMENTADO
- Novo módulo: `/app/backend/utils/input_sanitization.py`
- Funções: `sanitize_string()`, `sanitize_html()`, `sanitize_email()`, `sanitize_phone()`, `sanitize_nif()`, `sanitize_name()`, `sanitize_url()`
- Usa biblioteca `bleach` para limpeza segura de HTML
- **Status**: ✅ IMPLEMENTADO E TESTADO

#### 3. Field Constraints em Pydantic - IMPLEMENTADO
- `PersonalData`: Campos com `Field(max_length=...)`, validators para sanitização
- `PublicClientRegistration`: Validação de nome, email, telefone
- **Ficheiro**: `/app/backend/models/process.py`
- **Status**: ✅ IMPLEMENTADO

#### 4. Melhorias no Scraper Idealista - IMPLEMENTADO
- Extração de referência do anúncio
- Extração de link da agência
- Extração de nome do consultor/agente
- Extração de certificado energético
- **Ficheiro**: `/app/backend/services/scraper.py` (método `_parse_idealista`)
- **Status**: ✅ IMPLEMENTADO

#### 5. Melhor Extração de Telefones Portugueses - IMPLEMENTADO
- Novos padrões regex priorizando telemóveis (9X) sobre fixos (2X)
- Selectores específicos por agência (REMAX, ERA, Century21, etc.)
- Método `_extract_contacts_from_soup()` para extração via DOM
- **Ficheiro**: `/app/backend/services/scraper.py`
- **Status**: ✅ IMPLEMENTADO

#### 6. Fuzzy Matching com FuzzyWuzzy - IMPLEMENTADO
- `find_client_by_name()` agora usa `fuzz.token_set_ratio`
- Bónus de +20 para primeiro nome igual
- Score mínimo aumentado para 70 (era 40)
- **Ficheiro**: `/app/backend/routes/ai_bulk.py`
- **Status**: ✅ IMPLEMENTADO E TESTADO

#### 7. Endpoint /suggest-clients - IMPLEMENTADO
- `GET /api/ai/bulk/suggest-clients?query=X&limit=5`
- Retorna sugestões com fuzzy matching
- Inclui score, nome, id e contagem de documentos
- **Ficheiro**: `/app/backend/routes/ai_bulk.py` (linhas 1183-1252)
- **Status**: ✅ IMPLEMENTADO E TESTADO

#### 8. Tracking de Processos em Background - IMPLEMENTADO
- Novo dicionário `background_processes` para tracking
- `GET /api/ai/bulk/background-jobs` - Listar jobs
- `GET /api/ai/bulk/background-jobs/{job_id}` - Estado de job específico
- `DELETE /api/ai/bulk/background-jobs` - Limpar jobs terminados
- **Ficheiro**: `/app/backend/routes/ai_bulk.py` (linhas 47-97, 1074-1180)
- **Status**: ✅ IMPLEMENTADO E TESTADO

#### 9. Logs de Importação IA no Sistema de Logs - IMPLEMENTADO
- `GET /api/admin/ai-import-logs` - Listar logs de importação
- Filtros: status, days, client_name
- Estatísticas: total_errors, unresolved, resolved
- `POST /api/admin/ai-import-logs/{log_id}/resolve` - Marcar como resolvido
- **Ficheiro**: `/app/backend/routes/admin.py` (linhas 1567-1662)
- **Status**: ✅ IMPLEMENTADO E TESTADO

#### 10. Input para Treinar o Agente IA - IMPLEMENTADO
- `GET /api/admin/ai-training` - Listar dados de treino
- `POST /api/admin/ai-training` - Adicionar entrada
- `PUT /api/admin/ai-training/{id}` - Actualizar entrada
- `DELETE /api/admin/ai-training/{id}` - Remover entrada
- `GET /api/admin/ai-training/prompt` - Gerar prompt consolidado
- Categorias: document_types, field_mappings, client_patterns, custom_rules, extraction_tips
- **Ficheiro**: `/app/backend/routes/admin.py` (linhas 1309-1504)
- **Status**: ✅ IMPLEMENTADO E TESTADO

#### 11. Documentos para Imóveis da Empresa - IMPLEMENTADO
- `POST /api/properties/{id}/documents` - Upload de documento
- `GET /api/properties/{id}/documents` - Listar documentos
- `DELETE /api/properties/{id}/documents/{doc_id}` - Remover documento
- Tipos: caderneta_predial, certidao_registo, licenca_utilizacao, planta, cpcv, contrato, foto, outro
- Armazenamento em S3
- **Ficheiro**: `/app/backend/routes/properties.py` (linhas 962-1150)
- **Status**: ✅ IMPLEMENTADO E TESTADO

#### 12. Melhorias em detect_document_type() - IMPLEMENTADO
- Mais padrões de keywords para cada tipo de documento
- Suporte para abreviaturas comuns
- **Ficheiro**: `/app/backend/services/ai_document.py`
- **Status**: ✅ IMPLEMENTADO

#### 13. Melhorias em log_import_error() - IMPLEMENTADO
- Novos campos: folder_name, attempted_matches, best_match_score, best_match_name, extracted_names, full_path
- **Ficheiro**: `/app/backend/routes/ai_bulk.py`
- **Status**: ✅ IMPLEMENTADO

### Resultados do Testing Agent (Sessão 14)
- **Backend**: 100% (20/20 testes passaram)
- **Retest Necessário**: NÃO

### Novas Dependências Adicionadas (Sessão 14)
- `bleach==6.3.0` - Sanitização de HTML
- `fuzzywuzzy==0.18.0` - Fuzzy string matching
- `python-Levenshtein==0.27.3` - Performance para fuzzywuzzy

---

## Última Actualização - 12 Fevereiro 2026 (Sessão 13)

### ✅ Funcionalidades Corrigidas (Sessão 13)

#### 1. Bug Fix P0: Conflito de Índice idx_location - RESOLVIDO
- **Problema**: Erro de conflito de índice ao criar/importar imóveis
  - Índice antigo: `idx_location` em campos `(distrito, concelho)` 
  - Índice novo: `idx_location` em campos `(address.district, address.municipality)`
- **Causa**: Discrepância entre estrutura de dados antiga e nova
- **Solução**: Adicionado `idx_location` à lista `DEPRECATED_INDEXES` em `db_indexes.py`
- **Ficheiros Modificados**: `/app/backend/services/db_indexes.py`
- **Verificação**: Criados múltiplos imóveis com mesma localização sem erros - **Teste Passou**
- **Status**: ✅ RESOLVIDO E TESTADO

#### 2. Dependência libmagic - INSTALADA
- **Problema**: Backend não iniciava por falta de `libmagic1`
- **Solução**: `apt-get install libmagic1` executado
- **Status**: ✅ RESOLVIDO

#### 3. Verificação das Correções Anteriores (Sessão 12)
- ✅ **Sidebar mantém estado expandido** - useEffect actualiza `openSections` correctamente
- ✅ **Toast de notificações** - `sonner` mostra "Preferências de notificação guardadas!"
- ✅ **Tab Manutenção** - Botões "Reparar Índices", "Limpar Jobs", "Limpar Logs" funcionais
- ✅ **Importação Excel** - Endpoint `/api/properties/bulk/import-excel` funcional

### Resultados do Testing Agent (Sessão 13)
- **Backend**: 100% (8/8 testes passaram)
- **Frontend**: 100% (todas as funcionalidades UI verificadas)
- **Retest Necessário**: NÃO

---

## Última Actualização - 12 Fevereiro 2026 (Sessão 12 - Parte 2)

### ✅ Funcionalidades Implementadas (Sessão 12 - Parte 2)

#### 5. Painel de Manutenção do Sistema
- **Nova tab "Manutenção"** na página de Configurações do Sistema
- **Funcionalidades**:
  - **Reparar Índices**: Botão para executar `/api/admin/db/indexes/repair` directamente
  - **Ver Estado dos Índices**: Mostra estatísticas de índices por colecção
  - **Limpar Jobs Antigos**: Remove jobs de importação com mais de 7 dias
  - **Limpar Logs de Erro**: Remove logs com mais de 30 dias
- **Ficheiros Modificados**: `/app/frontend/src/pages/SystemConfigPage.js`, `/app/backend/routes/admin.py`
- **Status**: ✅ IMPLEMENTADO

#### 6. Importação de Minutas via Ficheiros
- **Nova funcionalidade**: Importar minutas de ficheiros Word (.docx) e PDF
- **Endpoint**: `POST /api/minutas/import`
- **Suporta**: .docx, .doc, .pdf, .txt
- **Auto-detecta categoria** pelo nome do ficheiro
- **Bibliotecas adicionadas**: python-docx, pypdf
- **Ficheiros Modificados**: `/app/backend/routes/minutas.py`, `/app/frontend/src/pages/MinutasPage.js`
- **Status**: ✅ IMPLEMENTADO

#### 7. Menu Lateral - Manter Submenu Selecionado
- **Problema**: Submenus colapsavam ao navegar entre páginas
- **Solução**: useEffect que detecta rota actual e expande a secção correspondente
- **Ficheiros Modificados**: `/app/frontend/src/layouts/DashboardLayout.js`
- **Status**: ✅ IMPLEMENTADO

#### 8. Feedback Toast nas Preferências de Notificações
- **Problema**: Botão "Guardar Preferências" não mostrava feedback visual
- **Solução**: Migrado de `useToast` para `sonner` com toast.success/error
- **Ficheiros Modificados**: `/app/frontend/src/pages/SettingsPage.js`
- **Status**: ✅ IMPLEMENTADO

#### 9. Popup Upload Massivo - Fechar e Notificar em Background
- **Problema**: Modal de upload massivo ficava aberto durante processamento
- **Solução**: 
  - Modal fecha imediatamente ao iniciar upload
  - Processamento continua em background
  - Notificação toast com resultado final (8 segundos de duração)
- **Ficheiros Modificados**: `/app/frontend/src/components/BulkDocumentUpload.js`
- **Status**: ✅ IMPLEMENTADO

#### 10. UI Revisão de Dados IA - Completa
- **Página**: `/revisao-dados-ia`
- **Funcionalidades**:
  - Tab "Revisão de Dados": Lista processos com dados pendentes, permite aplicar ou descartar
  - Tab "Relatório Semanal": Estatísticas de análise IA com gráficos
  - Cards de resumo: Processos pendentes, itens para revisão, tipos de documentos
  - Dialog de detalhes com comparação lado-a-lado
  - Configuração de frequência e destinatários do relatório
- **Status**: ✅ IMPLEMENTADO E TESTADO

---

### ✅ Funcionalidades Implementadas (Sessão 12 - Parte 1)

#### 1. Bug Fix P0: Erro E11000 Duplicate Key - Correcção Definitiva
- **Problema Reportado**: Erro `E11000 duplicate key error on idx_internal_ref` persistia em produção
- **Causa Raiz Identificada**: Discrepância entre nome do campo no código (`internal_reference`) e no índice de produção (`internal_ref`)
- **Solução Implementada**:
  - Adicionado sistema de limpeza de índices antigos em `db_indexes.py`
  - Lista `DEPRECATED_INDEXES` remove automaticamente `idx_internal_ref` no startup
  - Novo endpoint `POST /api/admin/db/indexes/repair` para corrigir índices manualmente
  - Endpoint `GET /api/admin/db/indexes` para diagnóstico
  - Endpoint `DELETE /api/admin/db/indexes/{collection}/{index_name}` para remover índices específicos
- **Ficheiros Modificados**: `/app/backend/services/db_indexes.py`, `/app/backend/routes/admin.py`
- **Status**: ✅ RESOLVIDO - Utilizador deve executar `/api/admin/db/indexes/repair` em produção

#### 2. Background Processing para Importações (P0.2)
- **Funcionalidade**: Importação Excel agora processa em background
- **Implementação**:
  - Novo serviço `/app/backend/services/background_jobs.py`
  - Endpoint `/api/properties/bulk/import-excel` retorna imediatamente com `job_id`
  - Endpoint `/api/properties/bulk/job/{job_id}` para consultar progresso
  - Endpoint `/api/properties/bulk/jobs` para listar jobs do utilizador
  - Frontend com polling de progresso via toast notifications
- **Benefícios**: UI não bloqueia durante importações grandes
- **Ficheiros Modificados**: 
  - `/app/backend/routes/properties.py`
  - `/app/backend/services/background_jobs.py` (novo)
  - `/app/frontend/src/pages/PropertiesPage.jsx`
- **Status**: ✅ IMPLEMENTADO

#### 3. Refatoração Menu Admin (P1)
- **Problema**: Menu lateral do admin tinha muitos itens e era difícil de usar
- **Solução**: Grupos colapsáveis com secções organizadas
  - **Principais** (sempre visíveis): Dashboard, Estatísticas, Quadro Geral
  - **Negócio** (colapsável): Utilizadores, Processos, Clientes, Leads, Imóveis, Minutas
  - **Ferramentas IA** (colapsável): Configuração IA, Agente IA, Revisão Dados IA
  - **Sistema** (colapsável): Backups, Definições, Configurações, Notificações, Logs
- **Ficheiros Modificados**: `/app/frontend/src/layouts/DashboardLayout.js`
- **Status**: ✅ IMPLEMENTADO

#### 4. Remoção Branding Emergent (P2)
- **Problema**: Badge "Made with Emergent" aparecia na aplicação
- **Solução**: Removido o bloco HTML do badge em `index.html`
- **Ficheiros Modificados**: `/app/frontend/public/index.html`
- **Status**: ✅ IMPLEMENTADO

---

## Sessão 11 - 12 Fevereiro 2026
- **Nova Página**: `/revisao-dados-ia` - Interface para administradores compararem dados extraídos pela IA
- **Funcionalidades**:
  - Lista de processos com dados pendentes de revisão
  - Comparação lado-a-lado: dados actuais vs. dados extraídos pela IA
  - Aplicar ou descartar dados pendentes
  - Visualizar histórico de extracções
  - Filtro por diferenças e campos pendentes
- **Endpoints Backend Utilizados**:
  - `GET /api/ai/bulk/pending-reviews` - Lista processos pendentes
  - `GET /api/ai/bulk/compare-data/{process_id}` - Compara dados
  - `POST /api/ai/bulk/apply-pending/{process_id}` - Aplica dados
  - `DELETE /api/ai/bulk/discard-pending/{process_id}` - Descarta dados
- **Permissões**: Admin, CEO, Administrativo
- **Ficheiros Criados**:
  - `/app/frontend/src/pages/AIDataReviewPage.js` - Componente React
  - Modificados: `App.js`, `DashboardLayout.js`
- **Status**: ✅ IMPLEMENTADO e TESTADO

#### 3. Relatório Semanal de Extracções IA (NOVA FUNCIONALIDADE)
- **Nova Aba**: "Relatório Semanal" na página de Revisão de Dados IA
- **Métricas Incluídas**:
  - Total de documentos analisados (com variação vs. semana anterior)
  - Taxa de sucesso das extracções
  - Número de extracções bem-sucedidas
  - Período do relatório
- **Visualizações**:
  - Distribuição por tipo de documento (com barras de progresso)
  - Top 10 campos mais extraídos (tabela)
  - Insights automáticos (sucesso, alerta ou informativo)
- **Envio Automático por Email**:
  - Configurável: diário, semanal, mensal ou desactivado
  - Dia da semana e hora personalizáveis
  - Botão "Enviar por Email" para envio manual a qualquer momento
- **Configurações Avançadas** (Modal):
  - Frequência: Diário, Semanal, Mensal, Desactivado
  - Dia de envio (para frequência semanal)
  - Hora de envio (0-23h)
  - Destinatários: Admins/CEOs, Toda a Equipa, ou lista personalizada
  - Opções: incluir insights e gráficos
- **Endpoints Backend**:
  - `GET /api/admin/ai-weekly-report` - Gera relatório
  - `POST /api/admin/ai-weekly-report/send` - Envia manualmente
  - `GET /api/admin/ai-report-config` - Obtém configuração
  - `PUT /api/admin/ai-report-config` - Actualiza configuração
  - `GET /api/admin/ai-report-recipients` - Lista destinatários disponíveis
- **Ficheiros Modificados**:
  - `/app/backend/routes/admin.py` - Novos endpoints
  - `/app/backend/services/scheduled_tasks.py` - Tarefa agendada configurável
  - `/app/backend/models/system_config.py` - Modelos de configuração
  - `/app/frontend/src/pages/AIDataReviewPage.js` - UI completa
- **Status**: ✅ IMPLEMENTADO e TESTADO

---

## Sessão 10 - 12 Fevereiro 2026

### ✅ Funcionalidades Implementadas (Sessão 10)

#### 1. Correção de Bugs nas Configurações do Sistema
- ✅ **Teste de conexão Storage (S3)**: Corrigido erro "Provider não suportado para teste"
  - Código agora detecta correctamente o provider `aws_s3`
  - Mensagens de erro mais detalhadas (403, 404, configuração em falta)
  - Suporte para múltiplos providers: aws_s3, onedrive, google_drive, dropbox, local
  - **Ficheiro**: `/app/backend/routes/system_config.py`

- ✅ **Teste de conexão Email (SMTP)**: Corrigido erro "please run connect() first"
  - Validação prévia de credenciais (servidor, utilizador, password)
  - Mensagens claras quando credenciais estão em falta
  - Suporte para SSL e STARTTLS
  - Tratamento de erros específicos (autenticação, conexão, timeout)
  - **Ficheiro**: `/app/backend/routes/system_config.py`

#### 2. Importação de Imóveis via Excel (formato HCPro/CRM)
- Actualizado endpoint `POST /api/properties/bulk/import-excel` para suportar formato HCPro
- Mapeamento automático de colunas com aliases
- Parser de preços europeus (700.000€ → 700000)
- Corrigido índice único `idx_internal_reference` com `sparse=True` (permite nulls)
- **Ficheiros**: `/app/backend/routes/properties.py`, `/app/backend/services/db_indexes.py`
- **Teste**: 12 imóveis importados com sucesso

#### 3. Alertas para Processos Finalizados
- ✅ Processos com status `concluido`, `desistido`, `cancelado`, `arquivado` não geram alertas
- Deadlines destes processos são excluídos automaticamente
- **Ficheiros**: `/app/backend/services/alerts.py`, `/app/backend/routes/deadlines.py`

#### 4. Sistema de Importação Massiva com IA (Melhorado)
Implementadas as 3 regras de importação sugeridas pelo utilizador:

**Regra 1: Processos finalizados não são alterados**
- Dados extraídos de processos concluídos/desistidos são guardados para revisão manual
- Novo campo `ai_pending_review` guarda dados pendentes

**Regra 2: Análise ficheiro-a-ficheiro com comparação**
- Histórico de extracções guardado em `ai_extraction_history`
- Endpoint `GET /api/ai/bulk/compare-data/{process_id}` para comparar dados

**Regra 3: Dados do utilizador não são sobrescritos**
- Campo `manually_edited_fields` marca campos editados manualmente
- IA não sobrescreve estes campos durante importação
- Endpoint `POST /api/ai/bulk/mark-field-manual/{process_id}` para marcar campos

**Novos Endpoints de Revisão:**
- `GET /api/ai/bulk/extraction-history/{process_id}` - Ver histórico de extracções
- `GET /api/ai/bulk/pending-reviews` - Listar processos com dados pendentes
- `POST /api/ai/bulk/apply-pending/{process_id}` - Aplicar dados pendentes
- `DELETE /api/ai/bulk/discard-pending/{process_id}` - Descartar dados pendentes
- `GET /api/ai/bulk/compare-data/{process_id}` - Comparar dados extraídos vs. actuais
- `POST /api/ai/bulk/mark-field-manual/{process_id}` - Marcar campo como manual
- `DELETE /api/ai/bulk/unmark-field-manual/{process_id}` - Desmarcar campo manual

---

## Última Actualização - 12 Fevereiro 2026 (Sessão 9)

### ✅ Funcionalidades Implementadas (Sessão 9)

#### 1. Normalização de Nomes de Ficheiros no Upload S3
**Funcionalidade:** Sanitização automática de nomes de ficheiros durante o upload
- Remove acentos e caracteres especiais
- Formato: `{Categoria}_{Data}_{NomeOriginalNormalizado}.{ext}`
- Limita tamanho a 50 caracteres
- **Ficheiro**: `/app/backend/routes/documents.py`

#### 2. Conversão Automática de Imagens para PDF
**Funcionalidade:** Converte imagens (JPG, PNG, TIFF) para PDF automaticamente durante o upload
- Usa biblioteca `img2pdf`
- Retorna informação sobre se foi convertido: `converted_to_pdf: true/false`
- **Ficheiros**:
  - `/app/backend/services/document_processor.py` (já existia)
  - `/app/backend/routes/documents.py` (integração)

#### 3. Validação de Campos Obrigatórios para Minutas
**Funcionalidade:** Antes de gerar uma minuta, verifica se os dados necessários estão preenchidos
- Retorna erro 400 com lista de campos em falta se dados incompletos
- Campos obrigatórios variam por tipo de template
- **CPCV requer**: Nome do Comprador, NIF do Comprador, Morada do Imóvel, Artigo Matricial
- **UI mostra alerta visual** com lista de campos a preencher
- **Ficheiros**:
  - `/app/backend/services/template_generator.py` - Função `validate_template_requirements()`
  - `/app/backend/routes/templates.py` - Endpoints retornam 400 com detalhes
  - `/app/frontend/src/components/TemplatesPanel.js` - Alerta visual com campos em falta

#### 4. Botões Webmail no Painel de Emails
**Funcionalidade:** Adicionados botões para abrir webmail directamente no painel de Histórico de Emails
- Botões "Precision" e "Power" com ícone de link externo
- Mesmos URLs do painel de Templates
- **Ficheiro**: `/app/frontend/src/components/EmailHistoryPanel.js`

#### 5. Refatoração de Processos (Parte 1)
**Objectivo:** Separar lógica de negócio dos endpoints seguindo Single Responsibility Principle
- **Novos serviços criados:**
  - `/app/backend/services/process_service.py` - Lógica principal (validação, criação, queries)
  - `/app/backend/services/process_assignment.py` - Atribuições de consultores/mediadores
  - `/app/backend/services/process_kanban.py` - Lógica específica do Kanban
- **Resultado:** `routes/processes.py` reduzido de 1035 para 934 linhas (~10%)
- **Benefícios:** Código mais testável, manutenção simplificada, reutilização de lógica

#### 6. Correções de Bugs (Sessão 9)
- ✅ **Guardar Notificações sem feedback** - Adicionado endpoint `PUT /api/auth/preferences` e toast de confirmação
- ✅ **WorkflowEditor ocupava muito espaço** - Layout compacto com max-height 384px e scroll, linhas mais curtas, setas horizontais
- ⚠️ **Teste de email em SystemConfig** - A API funciona (`/api/emails/test-connection`), mas o SystemConfigPage usa uma API diferente que requer configuração de credenciais

---

### ✅ Parte 2 - Automações Avançadas (IMPLEMENTADAS - Sessão 8)

#### 5. Templates e Minutas com Download
**Funcionalidades:**
- Geração automática de CPCV (Contrato Promessa Compra e Venda)
- Geração de email de Apelação de Avaliação ("Botão de Pânico")
- Geração de Lembrete de Escritura
- Geração de Pedido de Documentos

**Fluxo de Utilização:**
1. Utilizador clica no botão de pré-visualização ou download
2. Template é gerado com dados do processo preenchidos
3. Utilizador pode copiar o texto ou descarregar como ficheiro .txt
4. Utilizador abre o webmail (Precision ou Power)
5. Cola o texto no corpo do email

**Ficheiros Criados:**
- `/app/backend/services/template_generator.py` - Gerador de templates
- `/app/backend/routes/templates.py` - Endpoints da API
- `/app/frontend/src/components/TemplatesPanel.js` - Componente React

**API Endpoints:**
- `GET /api/templates/webmail-urls` - URLs dos webmails
- `GET /api/templates/document-types` - Lista de tipos de documentos
- `GET /api/templates/process/{id}/cpcv` - Template CPCV
- `GET /api/templates/process/{id}/cpcv/download` - Download CPCV
- `GET /api/templates/process/{id}/valuation-appeal` - Apelação de Avaliação
- `GET /api/templates/process/{id}/deed-reminder` - Lembrete de Escritura
- `GET /api/templates/process/{id}/document-checklist` - Checklist de documentos

#### 6. Webmail Integration
**URLs Configurados:**
- Precision: `http://webmail.precisioncredito.pt/`
- Power: `https://webmail2.hcpro.pt/Mondo/lang/sys/login.aspx`

**Nota:** A aplicação NÃO envia emails automaticamente. O utilizador faz download/copia a minuta e cola manualmente no webmail.

---

### ✅ Optimizações de Segurança e Performance (IMPLEMENTADAS)

#### Parte 3 - Optimizações Técnicas

**8. Índices de BD para Performance**
- Criado ficheiro `/app/backend/services/db_indexes.py`
- Índices criados automaticamente no startup da app
- Colecções indexadas: `processes`, `users`, `system_error_logs`, `properties`, `tasks`
- TTL index de 90 dias para logs (limpeza automática)

**11. Validação JWT Secret Robusta**
- Verificação de comprimento mínimo (32 chars)
- Detecção de valores de exemplo inseguros
- Verificação de complexidade (entropia)
- Em DEV: apenas aviso | Em PROD: bloqueio fatal
- Ficheiro: `/app/backend/config.py`

**12. Validação Checksum NIF Português**
- Algoritmo completo de validação do dígito de controlo
- Validação de prefixos válidos (1,2,3,5,6,7,8,9)
- Opção para permitir/bloquear NIFs de empresa (5xxxxx)
- Ficheiro: `/app/backend/models/process.py`

**14. Rate Limiting Configurável**
- Limites por tipo de endpoint: auth, read, write, upload, export, ai
- Configurável via variáveis de ambiente
- Headers X-RateLimit-* nas respostas
- Ficheiro: `/app/backend/middleware/rate_limit.py`

---

#### Parte 1 - Lógica de Negócio

**1. ServiceTypeEnum**
- Novo enum: `CREDITO_APENAS`, `IMOBILIARIO_APENAS`, `COMPLETO`
- Ficheiro: `/app/backend/models/process.py`

**2. Campos de Avaliação Bancária**
- Novos campos em `CreditData`: `valuation_value`, `valuation_date`, `valuation_bank`, `valuation_notes`
- Ficheiro: `/app/backend/models/process.py`

**3. Pastas S3 com Múltiplos Titulares**
- Formato: `clientes/{id}_{nome1}_e_{nome2}/`
- Aplicado apenas a NOVOS processos
- Ficheiro: `/app/backend/services/s3_storage.py`

**4. Alerta Automático de Avaliação Bancária**
- Novo tipo: `VALUATION_BELOW_PURCHASE`
- Detecta quando avaliação < valor de compra
- Calcula diferença e percentagem
- Envia notificações para consultores e admins
- Inclui recomendações de acção
- Ficheiro: `/app/backend/services/alerts.py`

---

### ✅ Correcções Anteriores (Sessão 7)

**Bug Fix: Atribuições - Dropdowns Vazios**
- Problema: Dropdowns de Consultor e Mediador apareciam vazios
- Solução: Função `openAssignDialog` convertida para async com await
- Ficheiro: `/app/frontend/src/pages/ProcessDetails.js`

**Integração HCPro**
- Upload de Excel para criar imóveis
- Botão de login HCPro no formulário de novo imóvel
- URL: https://crmhcpro.pt/login

**Sistema de Logs Corrigido**
- Logs de importação Excel agora aparecem na página de Logs do Sistema
- Colecção: `system_error_logs` (centralizada)

---

#### 2. Botão Login HCPro no Formulário de Novo Imóvel
- **Localização**: Topo do formulário "Novo Imóvel"
- **URL**: https://crmhcpro.pt/login
- **Comportamento**: Abre numa nova janela do browser
- **UI**: Secção destacada em azul com ícone de link externo

**Ficheiros Alterados**:
- `/app/frontend/src/pages/PropertiesPage.jsx`:
  - Adicionada constante `HCPRO_URL`
  - Adicionado ícone `ExternalLink` aos imports
  - Adicionada secção "Integração HCPro" no `PropertyForm`

**Teste Realizado**:
- ✅ Importação Excel: 2 imóveis importados com sucesso
- ✅ Botão HCPro: Visível e funcional no formulário
- ✅ Referências automáticas: IMO-004, IMO-005 criados

---

## Última Actualização - 11 Fevereiro 2026 (Sessão 6)

### ✅ Implementações Completas (11 Fevereiro 2026 - Noite)

#### 1. S3 File Manager - Gestão de Documentos AWS S3
- **Componente Frontend**: `/app/frontend/src/components/S3FileManager.js`
- **Serviço Backend**: `/app/backend/services/s3_storage.py`
- **Rotas API**: `/app/backend/routes/documents.py`
- **Funcionalidades**:
  - Upload de ficheiros organizado por categorias (Pessoais, Financeiros, Imóvel, Bancários, Outros)
  - Download com URLs temporários (presigned URLs)
  - Eliminação de ficheiros
  - Criação automática de estrutura de pastas
  - Barra de progresso para uploads
  - Interface com tabs por categoria
- **Configuração AWS** (em `/app/backend/.env`):
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_BUCKET_NAME=powerprecision-docs-storage`
  - `AWS_REGION=eu-north-1`

#### 2. Agente de Melhoria com IA
- **Serviço Backend**: `/app/backend/services/ai_improvement_agent.py`
- **Rotas API**: `/app/backend/routes/ai_agent.py`
- **Página Frontend**: `/app/frontend/src/pages/AIInsightsPage.js`
- **Rota**: `/ai-insights` (apenas admin e CEO)
- **Funcionalidades**:
  - Análise preditiva de todos os processos activos
  - Estatísticas: total analisado, parados, tempo médio
  - Distribuição por estado e consultor
  - Sistema de alertas com prioridades (high, medium, low)
  - Sugestões automáticas baseadas em regras
  - Integração com LLM para insights personalizados
  - Análise de processo individual
- **Endpoints**:
  - `GET /api/ai-agent/analyze` - Análise completa
  - `GET /api/ai-agent/analyze/{process_id}` - Análise de processo
  - `GET /api/ai-agent/suggestions` - Apenas sugestões
  - `GET /api/ai-agent/alerts` - Alertas filtráveis
  - `GET /api/ai-agent/stats` - Estatísticas

### Análise do ficheiro `ideias CreditoIMO.txt`

| Funcionalidade | Estado |
|---------------|--------|
| 1. Página Imóveis + Scraping | ✅ Implementado |
| 2. Deep Scraping (nome agente) | ✅ Implementado |
| 3. Painel Imobiliário (dados comercial) | ✅ Implementado |
| 4. Gestão de Leads/Kanban | ✅ Implementado |
| 5. Checklist Docs (agora S3) | ✅ Implementado |
| 6. Minutas/Templates | ✅ Implementado |
| 7. Entidades Cliente + Imóvel | ✅ Implementado |
| 8. Dashboard/Estatísticas | ✅ Implementado |
| Agente IA - Nível 1 (Descritivo) | ✅ Implementado |
| Agente IA - Nível 2 (Preditivo) | ✅ Implementado |
| Agente IA - Nível 3 (Prescritivo) | ✅ Implementado |
| Integração HCPRO | ❌ Não implementado (requer documentação externa) |

## Última Actualização - 11 Fevereiro 2026 (Sessão 5)

### ✅ Implementação Completa do Ponto 2 (11 Fevereiro 2026 - Noite)

#### Novas Funcionalidades Implementadas:

1. **c) Deep Link Melhorado - Extracção Nome do Agente**
   - Scraper agora extrai o nome do consultor/agente a partir do link adicional
   - Novas funções: `_extract_agent_name()`, `_extract_agency_name()`
   - Procura em selectores CSS típicos e padrões de texto
   - Ficheiro: `/app/backend/services/scraper.py`

2. **d) UI de Gestão de Backups**
   - Nova página `/admin/backups` (apenas admin)
   - Interface para criar backups manualmente
   - Visualização de estatísticas e histórico
   - Verificação de integridade dos backups
   - Ficheiros: `/app/frontend/src/pages/BackupsPage.js`, `/app/backend/routes/backup.py`

3. **e) Mensagens Amigáveis no Scraper**
   - Quando o scraping falha, retorna mensagem user-friendly em português
   - Códigos de erro: `blocked`, `timeout`, `not_found`, `quota_exceeded`, `parse_error`, `ssl_error`
   - Flag `suggest_manual` para indicar quando inserir dados manualmente
   - Flag `can_retry` para indicar se vale a pena tentar novamente
   - Ficheiro: `/app/backend/routes/scraper.py`

4. **f) Suporte a Proxies no Scraper**
   - Configurável via variável de ambiente `SCRAPER_PROXIES`
   - Formato: lista separada por vírgulas (ex: `http://host1:port,http://host2:port`)
   - Rotação round-robin automática entre proxies
   - Fallback quando proxy é bloqueada
   - Ficheiro: `/app/backend/services/scraper.py`

5. **g) Limpeza Automática de Ficheiros Temporários**
   - Nova tarefa `cleanup_temp_files()` nas tarefas agendadas
   - Limpa ficheiros com mais de 24 horas em `/tmp/creditoimo_*`
   - Nova tarefa `cleanup_scraper_cache()` para cache expirado
   - Ficheiro: `/app/backend/services/scheduled_tasks.py`

6. **l) Secção Minutas**
   - Nova página `/minutas` (disponível para todos os staff)
   - CRUD completo para minutas/templates de documentos
   - Categorias: Contratos, Procurações, Declarações, Cartas, Outros
   - Funcionalidades: copiar, descarregar, pesquisar, filtrar por categoria, tags
   - Suporte a placeholders (ex: `[NOME_CLIENTE]`, `[DATA]`)
   - Ficheiros: `/app/frontend/src/pages/MinutasPage.js`, `/app/backend/routes/minutas.py`

#### Menu Lateral Actualizado:
- **Admin**: Vê "Minutas" e "Backups" no menu
- **Staff**: Vê "Minutas" no menu
- **Intermediários/Mediadores**: Não vêem "Imóveis" nem "Todos os Processos"

---

### ✅ Correcções Bug Batch (11 Fevereiro 2026 - Tarde)

1. **Bug h - Dados Pessoais Não Guardados (CORRIGIDO)**
   - Adicionados novos campos ao modelo `PersonalData`: `data_nascimento`, `data_validade_cc`, `sexo`, `altura`, `nome_pai`, `nome_mae`
   - Campos são agora correctamente guardados via PUT /api/processes/{id}
   - Ficheiro: `/app/backend/models/process.py`

2. **Bug i - Consultores Redirecionados para Login (CORRIGIDO)**
   - Função `can_view_process()` actualizada para verificar `created_by` tanto por ID como por email
   - Adicionado suporte para role `INTERMEDIARIO` na verificação de permissões
   - Ficheiro: `/app/backend/routes/processes.py`

3. **Bug j - "Os Meus Clientes" Mostra Clientes Errados (CORRIGIDO)**
   - Endpoint `/api/processes/my-clients` agora suporta `MEDIADOR` e `INTERMEDIARIO`
   - Filtra correctamente por `assigned_consultor_id` ou `assigned_mediador_id` dependendo do papel
   - API `/api/clients` corrigida para filtrar por campos correctos (antes usava `assigned_to` genérico)
   - Ficheiros: `/app/backend/routes/processes.py`, `/app/backend/routes/clients.py`

4. **Bug k - Menu Lateral para Intermediários (CORRIGIDO)**
   - Intermediários e Mediadores agora não vêem "Imóveis" nem "Todos os Processos" no menu
   - Menu "Os Meus Clientes" adicionado para intermediários e mediadores
   - Ficheiro: `/app/frontend/src/layouts/DashboardLayout.js`

### ✅ Correcções e Melhorias Anteriores

1. **UI Kanban - Visibilidade de Nomes de Clientes (P0)**
   - Nomes de clientes agora são **totalmente visíveis** mesmo quando longos
   - Layout reestruturado: Número do processo em cima, nome do cliente em destaque abaixo
   - Texto usa `break-words` e `overflow-wrap: anywhere` para evitar truncamento
   - Fonte aumentada para `text-sm` com `font-semibold` para melhor legibilidade
   - Consultor mostrado em linha separada com ícone de utilizador

2. **Hybrid Scraper com Deep Link (P0)**
   - Implementada lógica "Deep Link" para encontrar contactos de agentes
   - Scraper agora segue links externos para sites de agências (Remax, ERA, Century21, etc.)
   - Extracção de contactos via regex: telefones (+351, 9XX, 2XX) e emails
   - Fallback gracioso quando quota Gemini está excedida
   - Novos campos extraídos: `agente_nome`, `agente_telefone`, `agente_email`, `agencia_nome`
   - Tratamento de erro `quota_exceeded` - scraper continua apenas com BeautifulSoup

3. **Limpeza de Dados de Teste (P2)**
   - Script `cleanup_test_data.py` criado para eliminar dados de teste
   - **33 registos eliminados**: 3 utilizadores de teste + 30 processos de teste
   - Base de dados limpa: apenas dados reais de produção permanecem
   - Script suporta modo dry-run para pré-visualização

4. **Configuração Dinâmica de IA (P1) - NOVO**
   - Admin pode agora escolher qual modelo usar para cada tarefa via `/api/admin/ai-config`
   - Modelos disponíveis: `gemini-2.0-flash`, `gpt-4o-mini`, `gpt-4o`
   - Tarefas configuráveis: scraping, análise de documentos, relatório semanal, análise de erros
   - Scraper e serviços de IA lêem configuração dinamicamente da DB

5. **Sistema de Cache para Scraping - NOVO**
   - Cache local guarda resultados de scraping por 7 dias
   - Evita chamadas repetidas à API Gemini/OpenAI
   - Novos endpoints:
     - `GET /api/scraper/cache/stats` - estatísticas do cache
     - `DELETE /api/scraper/cache/clear` - limpar cache
     - `POST /api/scraper/cache/refresh` - forçar refresh
   - Parâmetro `use_cache` no endpoint `/api/scraper/single`

6. **UI de Configuração de IA - NOVO**
   - Nova página `/configuracoes/ia` com 3 tabs:
     - **Configuração de Tarefas**: Mostra todas as tarefas e permite alterar o modelo de cada uma
     - **Modelos de IA**: CRUD completo para adicionar/editar/remover modelos
     - **Cache & Notificações**: Estatísticas de cache com barra de progresso e configurações de alertas
   - Botões "Nova Tarefa" e "Novo Modelo" para adicionar via UI
   - Modelos e tarefas são agora guardados na DB (não hardcoded)
   - Notificações automáticas quando cache atinge limite configurado

7. **Sistema de Notificações de Cache - NOVO**
   - Configurações: Limite do cache (default: 1000) e % para alertar (default: 80%)
   - Barra de progresso visual mostra utilização do cache
   - Alerta amarelo aparece automaticamente quando limite é atingido
   - Endpoints: `GET/PUT /api/admin/cache-settings`

8. **Log de Uso de IA (Tracking de Custos) - NOVO**
   - Novo serviço `ai_usage_tracker.py` regista cada chamada à IA
   - Métricas: chamadas, tokens (input/output), custo estimado, tempo de resposta, taxa de sucesso
   - Resumos diários guardados na colecção `ai_usage_summary`
   - Endpoints:
     - `GET /api/admin/ai-usage/summary` - Resumo geral
     - `GET /api/admin/ai-usage/by-task` - Agregado por tarefa
     - `GET /api/admin/ai-usage/by-model` - Agregado por modelo
     - `GET /api/admin/ai-usage/trend` - Tendência diária
   - Nova tab "Uso & Custos" na página de configuração de IA
   - Filtro por período: Hoje, Última Semana, Este Mês, Tudo
   - Gráfico de barras para tendência diária

9. **Correcção de Segurança Bandit - CORRIGIDO**
   - Substituído MD5 por SHA-256 no hash de URLs do cache
   - **0 problemas de alta severidade** no Bandit

10. **Correcções Técnicas**
   - Instalado `libmagic1` para validação de ficheiros
   - Instalado `h2` para suporte HTTP/2 no scraper
   - Nova chave Gemini API configurada no `.env`

11. **Sistema de Controlo de Notificações - NOVO**
   - Admin pode configurar preferências de email/notificação por utilizador
   - Tipos de notificação configuráveis:
     - Emails: novo processo, mudança status, documento, tarefa, prazos, urgentes, resumo diário, relatório semanal
     - In-App: novo processo, mudança status, documento, tarefa, comentários
   - **Utilizadores de Teste**: Podem ser marcados para não receber emails
   - Acções em massa: marcar/desmarcar múltiplos utilizadores como teste
   - Nova página: `/configuracoes/notificacoes`
   - Endpoints:
     - `GET /api/admin/notification-preferences` - Lista todos
     - `GET/PUT /api/admin/notification-preferences/{user_id}` - Individual
     - `POST /api/admin/notification-preferences/bulk-update` - Em massa

12. **Correcção de Validação de Datas - NOVO**
   - Datas em formato português ("19 de outubro de 1949") são convertidas para ISO
   - Erros de validação agora são mostrados correctamente (não causam página em branco)

13. **Filtros na Página de Clientes - NOVO**
   - Filtros: Todos | Com Processos | Sem Processos
   - Ordenação: Mais Recentes | Mais Antigos | Nome (A-Z/Z-A) | Processos
   - Cabeçalhos da tabela clicáveis para ordenar

## Funcionalidades Implementadas

### Core
- ✅ Sincronização bidirecional com Trello
- ✅ Sistema de workflow com 14 fases
- ✅ Gestão de processos (CRUD completo)
- ✅ Sistema de autenticação JWT
- ✅ Gestão de utilizadores por roles (admin, consultor, mediador, cliente)

### Atribuição Automática de Processos (Fev 2026)
- ✅ **Mapeamento automático Membros Trello ↔ Utilizadores da App**
- ✅ Atribuição automática durante importação/sincronização do Trello
- ✅ Endpoint `/api/trello/assign-existing` para atribuir processos já existentes
- ✅ Visibilidade de processos por papel (consultor vê só os seus, mediador idem)
- ✅ Interface de diagnóstico com estatísticas de sincronização
- ✅ **Dialog de atribuição manual** - permite atribuir consultor e intermediário via UI

### Página de Integração Trello Melhorada (Fev 2026)
- ✅ Estatísticas de sincronização (total, do Trello, com/sem atribuição)
- ✅ Mapeamento visual de membros do Trello para utilizadores
- ✅ Avisos quando existem processos sem atribuição
- ✅ Botão "Atribuir Auto" para corrigir processos existentes
- ✅ Informação de diagnóstico detalhada (credenciais, erros)

### Importação de Comentários do Trello (Fev 2026)
- ✅ Endpoint `POST /api/trello/sync/comments` para importar comentários
- ✅ Botão "Comentários" na página de Integração Trello
- ✅ Comentários aparecem na secção "Atividade" de cada processo
- ✅ Identificados com ícone 📋 e badge "trello"
- ✅ Importação idempotente (não duplica ao re-executar)

### Análise de Documentos com IA (Fev 2026)
- ✅ Botão "✨ Analisar com IA" na página de detalhes do processo
- ✅ Upload de ficheiros (PDF, JPG, PNG, WebP)
- ✅ Análise via URL/link do OneDrive
- ✅ Suporta: CC, Recibo Vencimento, IRS, Contrato Trabalho, Caderneta Predial
- ✅ Preenche automaticamente os campos da ficha do cliente
- ✅ Usa GPT-4o-mini via Emergent LLM Key

### Integração OneDrive (Fev 2026)
- ✅ **Workaround via link partilhado** - utiliza link de partilha da pasta principal
- ✅ Botão "Abrir no OneDrive" na página de detalhes do processo
- ✅ Possibilidade de guardar link específico da pasta do cliente
- ✅ Separador "Ficheiros" com links adicionais do OneDrive
- ✅ Configuração via variáveis de ambiente (ONEDRIVE_SHARED_LINK)

### Sistema de Emails (Jan 2026)
- ✅ Visualização de emails por processo
- ✅ Sincronização IMAP com 2 contas (Precision, Power)
- ✅ Busca por nome do cliente no assunto
- ✅ Busca por nome do cliente no corpo do email
- ✅ Busca em subpastas IMAP nomeadas com cliente
- ✅ Emails monitorizados configuráveis por processo

### Identificação de Processos (Jan 2026)
- ✅ Número sequencial simples (#1, #2, #3...)
- ✅ Migração de processos existentes
- ✅ Exibição no Kanban e detalhes

### UI/UX (Jan-Fev 2026)
- ✅ Tema de cores teal/dourado (Precision/Power branding)
- ✅ Painel de emails sempre visível na página de detalhes
- ✅ Scroll corrigido no histórico de emails
- ✅ ID interno "CreditoIMO" oculto da interface
- ✅ **Layout Kanban corrigido** - botões de ação sempre visíveis (grid layout)

### Correções de Bugs
- ✅ (Fev 2026) **Botões Kanban** - Layout reestruturado com CSS Grid para garantir visibilidade
- ✅ (Fev 2026) Processos não visíveis para não-admins - CORRIGIDO
- ✅ (Jan 2026) Removido ID CreditoIMO das notas (151 processos limpos)
- ✅ (Jan 2026) Corrigido erro de validação em atividades incompletas
- ✅ (Jan 2026) Endpoint /health para deployment

## Tarefas Pendentes

### P1 - Alta Prioridade
- [ ] Dashboard de Gestão com KPIs e métricas
- [ ] Exportação de relatórios PDF

### P2 - Média Prioridade
- [ ] Melhorias no sistema de documentos (conversão PDF, validação)
- [ ] Sistema de faturação
- [ ] Análise de documentos com IA (testar com ficheiros reais)

## Credenciais de Teste
- Admin: `admin@sistema.pt` / `admin2026`
- Consultor: criar via painel admin
- Mediador: criar via painel admin

## Arquitetura de Ficheiros Principais
```
/app/backend/
├── services/
│   ├── email_service.py     # Sincronização IMAP
│   └── trello.py            # Integração Trello
├── routes/
│   ├── processes.py         # CRUD processos, Kanban, Atribuição
│   ├── trello.py            # Webhooks Trello, Atribuição Auto
│   ├── onedrive.py          # Integração OneDrive (link partilhado)
│   └── activities.py        # Comentários/atividades
└── models/
    └── process.py           # Modelo de dados

/app/frontend/src/
├── components/
│   ├── TrelloIntegration.js # Painel Trello melhorado
│   ├── EmailHistoryPanel.js # Painel de emails
│   ├── OneDriveLinks.js     # Componente de ficheiros OneDrive
│   └── KanbanBoard.js       # Quadro Kanban (layout corrigido)
├── pages/
│   └── ProcessDetails.js    # Detalhes do processo
└── index.css                # Variáveis de tema
```

## Integrações Ativas
- **OpenAI**: gpt-4o-mini para análise de documentos
- **Trello**: Sincronização bidirecional via API e webhooks
- **Email**: IMAP/SMTP (geral@precisioncredito.pt, geral@powerealestate.pt)
- **OneDrive**: Via link partilhado (workaround - não usa OAuth)

## Endpoints da API Principais
- `POST /api/processes/{process_id}/assign` - Atribuir consultor/intermediário
- `GET /api/onedrive/process/{process_id}/folder-url` - URL da pasta OneDrive
- `PUT /api/onedrive/process/{process_id}/folder-url` - Guardar link específico
- `GET /api/processes/kanban` - Dados do quadro Kanban
- `POST /api/trello/sync` - Sincronizar com Trello

## Notas Importantes para Deployment
- Os utilizadores da aplicação devem ter o **mesmo nome** que os membros do Trello para que a atribuição automática funcione
- A sincronização pode ser feita manualmente via botão "Trello → App" ou automaticamente via webhook
- Processos existentes sem atribuição podem ser corrigidos com "Atribuir Auto"
- OneDrive usa **link partilhado** - não requer OAuth (configurar ONEDRIVE_SHARED_LINK no .env)

## Última Actualização
**11 Fevereiro 2026 - Sessão 3**
- ✅ **P1 Completo - Sistema de Notificações com Preferências**:
  - Novo serviço `services/notification_service.py` que verifica preferências antes de enviar emails
  - Função `send_notification_with_preference_check()` substitui chamadas directas de email
  - Integrado em: `routes/processes.py`, `routes/deadlines.py`, `services/alerts.py`
  - Tipos de notificação suportados: new_process, status_change, document_upload, task_assigned, deadline_reminder
  - Admin pode configurar preferências via `/api/admin/notification-preferences/{user_id}`
  - Utilizadores marcados como `is_test_user` não recebem emails
- ✅ **Melhoria - Mensagens de Erro Claras por Campo**:
  - Novo utilitário `frontend/src/utils/errorFormatter.js` para traduzir erros Pydantic
  - Mapeamento de campos para nomes em português (client_email → "Email do Cliente")
  - Tradução de mensagens comuns (e.g., "Input should be a valid number" → "deve ser um número")
  - Erros mostram lista de campos com problema em vez de mensagem genérica
  - Implementado em `ProcessDetails.js` e `LeadsKanban.js`
- ✅ **Bug Fix - NIF aceita números**:
  - Validators em `PersonalData` e `Titular2Data` convertem int/float para string antes de validar
  - Corrige erro quando frontend envia NIF como número em vez de string

**11 Fevereiro 2026 - Sessão 2**
- ✅ **Bug Fix - Validação Email/Telefone (P0)**: Corrigido erro "Input should be a valid number" ao guardar ficha de cliente:
  - Adicionado `@field_validator` no modelo `ProcessUpdate` para converter `client_email` e `client_phone` para string
  - Frontend converte explicitamente para `String()` antes de enviar
  - Testado e verificado: guardar funciona sem erros de validação
- ✅ **Nova Funcionalidade - Criação de Leads via URL (P0)**:
  - Novo endpoint `POST /api/leads/from-url` que extrai dados e cria lead automaticamente
  - Verifica duplicados antes de criar
  - Regista erros de scraping no sistema de logs
  - Retorna lead criado com dados extraídos
- ✅ **Nova Funcionalidade - Página de Logs do Sistema (P0)**:
  - Nova página `/admin/logs` para visualizar erros do sistema
  - Endpoints implementados:
    - `GET /api/admin/system-logs` - Lista com filtros e paginação
    - `GET /api/admin/system-logs/stats` - Estatísticas (total, não lidos, críticos)
    - `POST /api/admin/system-logs/mark-read` - Marcar como lido
    - `POST /api/admin/system-logs/{id}/resolve` - Resolver erro
    - `DELETE /api/admin/system-logs/cleanup` - Limpar antigos
  - UI com:
    - Cards de estatísticas (Total, Não Lidos, Por Resolver, Críticos)
    - Filtros por severidade, componente, estado, período
    - Tabela paginada com detalhes
    - Dialog para ver detalhes e resolver erros
  - Link adicionado no menu Admin
- ✅ **Serviço de Error Logging**: Novo serviço `system_error_logger.py` centralizado

**10 Fevereiro 2026**
- ✅ **Bug Fix Crítico - Extração NIF de CC**: Corrigido bug onde NIF era extraído incorretamente de documentos CC (começava por 5 em vez do valor real):
  - Alterado `detail` de `'low'` para `'high'` na API de visão para documentos CC/CPCV
  - Aumentado DPI de conversão PDF→imagem de 200 para 300 para documentos CC/CPCV
  - Imagens de CC não são mais redimensionadas para preservar qualidade
  - Prompts melhorados com instruções específicas sobre localização do NIF no verso do cartão
  - Testado com CC da Carolina Silva: NIF 268494622 extraído correctamente
- ✅ **Nova Funcionalidade - Lista de Clientes para Consultores (P0)**:
  - Novo endpoint `GET /api/processes/my-clients` com filtro por consultor
  - Nova página `/meus-clientes` com:
    - Estatísticas: Total de Clientes, Com Tarefas Pendentes, Com Imóvel Associado
    - Pesquisa por nome, email ou nº processo
    - Filtro por fase do workflow
    - Tabela com: Nº, Cliente, Fase, Ações Pendentes, Última Atualização, Ações
  - Link "Os Meus Clientes" adicionado na navegação para consultores
- ✅ **Bug Fix - Dados CPCV não guardados (P2)**:
  - Adicionados campos ao modelo `RealEstateData`: valor_imovel, data_cpcv, data_escritura_prevista, tipologia, etc.
  - Adicionados campos ao modelo `FinancialData`: valor_entrada, valor_pretendido, data_sinal, etc.
  - Adicionados campos ao modelo `ProcessUpdate`: co_buyers, vendedor, mediador
  - Adicionados campos ao modelo `ProcessResponse` para retornar dados do CPCV
  - Endpoint `PUT /processes/{id}` agora guarda todos os campos do CPCV
- ✅ **Instalação libmagic**: Corrigido erro de importação do python-magic para validação de ficheiros

**9 Fevereiro 2026**
- ✅ **Segurança: SlowAPI Rate Limiting**: Implementado nas rotas públicas e de autenticação
  - Login: 5 requests/minuto
  - Register: 3 requests/minuto
  - Client Registration: 3 requests/minuto
- ✅ **Segurança: CORS Estrito**: Refatorado para usar variáveis de ambiente com validação
  - CORS_ORIGINS aceita lista de origens separadas por vírgula
  - Validação de formato de URLs
  - Avisos em modo desenvolvimento
- ✅ **Segurança: CI/CD Security Scan**: Workflow GitHub Actions criado
  - Safety para vulnerabilidades de dependências
  - Bandit para análise estática de código
  - Execução semanal automática + em PRs
- ✅ **Página Leads para Consultores**: Adicionada rota `/leads` e link de navegação
- ✅ **Bug Fix LeadsKanban**: Corrigido bug SelectItem com valor vazio
- ✅ **Verificação Trello**: Confirmado funcional (14 listas, 152 processos)
- ✅ **Impersonation Testado**: admin→consultor→admin funciona
- ✅ **Visibilidade Clientes**: Consultor vê 100 clientes baseado em processos

### Issues Verificados e Resolvidos
| Issue | Estado | Notas |
|-------|--------|-------|
| Trello 401 Error | ✅ RESOLVIDO | API conectada |
| Impersonation Error | ✅ RESOLVIDO | Fluxo completo testado |
| Bulk Upload postMessage | ✅ WORKAROUND | Patch aplicado |
| Consultor não vê clientes | ✅ RESOLVIDO | 100 clientes visíveis |
| Leads para Consultor | ✅ RESOLVIDO | Rota e navegação adicionadas |
| Rate Limiting | ✅ IMPLEMENTADO | SlowAPI em rotas públicas |
| CORS Estrito | ✅ IMPLEMENTADO | Validação via .env |
| Security Scan CI/CD | ✅ IMPLEMENTADO | GitHub Actions workflow |

**10 Fevereiro 2026**
- ✅ **Correção de Testes Unitários**: Resolvido problema de asyncio event loop com Motor driver
  - Actualizado `conftest.py` com `reset_db_connection()` entre testes
  - Criado `DatabaseProxy` em `database.py` para conexões on-demand
  - Corrigidos fixtures de autenticação (admin, consultor, mediador)
  - Todos os 16 testes passam (test_auth.py + test_processes.py)
- ✅ **Melhorias no Módulo de Gestão de Leads**:
  - Novo endpoint `POST /api/leads/{id}/refresh` para verificar se preço mudou
  - Botão "🔄 Verificar Preço" no card de cada lead
  - Filtro por Consultor no Kanban de Leads
  - Filtro por Estado no Kanban de Leads
  - Endpoint `GET /api/leads/consultores` para lista de consultores
  - Data de entrada nos cards ("Há X dias")
  - Destaque visual (borda vermelha) para leads antigas (>7 dias em "Novo")
- ✅ **Nova Página de Estatísticas de Leads**:
  - Tab "Funil de Leads" com gráfico de barras (5 fases)
  - Tab "Ranking Consultores" com top 5 consultores por leads angariados
  - Endpoint `GET /api/stats/leads` retorna estatísticas
  - Endpoint `GET /api/stats/conversion` retorna tempo médio de conversão
  - KPIs: Total de Leads, Tempo Médio de Conversão, Leads Convertidos
- ✅ **Correção de Bug UI**: Toast notifications movidas para bottom-right (não tapam botões)
- ✅ **Correção de Bug de Acesso**: Consultores podem agora aceder a processos que criaram
  - Função `can_view_process()` actualizada para verificar `created_by`
- ✅ **Melhorias no Scraper**: Adicionado fallback SSL, parser ERA melhorado
- ✅ **Tab CPCV na página de detalhes**: Nova secção dedicada ao Contrato Promessa Compra e Venda com:
  - Dados do Imóvel (valor, tipologia, área, morada)
  - Dados do Vendedor (nome, NIF, telefone, email, morada)
  - Compradores (principal + co-compradores do CPCV)
  - Valores e Datas (entrada, sinal, data CPCV, escritura prevista)
  - Mediador (se existir)
- ✅ **Cartões do Kanban compactados**: Tamanho reduzido para melhor visualização
- ✅ **Ficheiros de teste temporários limpos**
- ✅ **Sistema de Logging de Erros de Importação**:
  - Novo endpoint `GET /api/ai/bulk/import-errors` - lista erros de importação
  - Novo endpoint `GET /api/ai/bulk/import-errors/summary` - resumo estatístico
  - Novo endpoint `POST /api/ai/bulk/import-errors/{id}/resolve` - marcar como resolvido
  - Novo endpoint `DELETE /api/ai/bulk/import-errors/clear` - limpar erros antigos
  - Erros guardados na colecção `import_errors` com: cliente, ficheiro, tipo, erro, timestamp
  - Agrupamento por tipo de erro para identificar padrões
- ✅ **Sistema de Matching - UI Clientes Sugeridos**:
  - Botão sparkles (✨) no cartão de lead para ver clientes compatíveis
  - Dialog mostra clientes com score de match e razões do match
  - Corrigido bug em `client_match.py` (NoneType error em financial_data)
- ✅ **Scraper melhorado**:
  - Headers mais realistas (Sec-Fetch, Cache-Control)
  - Delay aleatório entre requests
  - Suporte HTTP/2
  - Handling correcto de erros SSL
- ✅ **Bug login consultor VERIFICADO**: Consultor consegue aceder a processos atribuídos

**11 Fevereiro 2026**
- ✅ **Cartões do Quadro Geral de Processos Ultra-Compactos**:
  - Reduzido padding de p-2 para p-1.5
  - Fonte do nome de text-xs para text-[11px]
  - Número do processo de text-[10px] para text-[9px]
  - Removidos badges de Trello e Consultor para economizar espaço
  - Layout em linha única: nome + número + badge prioridade + botão ver
  - Adicionado data-testid para testes automatizados
- ✅ **Validação de NIF para Clientes Particulares**:
  - Backend: função `validate_nif()` actualizada para rejeitar NIFs começados por 5 (empresas)
  - Frontend: validação em tempo real no campo NIF com mensagem de erro
  - Erro mostrado: "NIF de empresa (começa por 5) não é permitido para clientes particulares"
  - Campo fica com borda vermelha quando inválido
  - Validação também bloqueia guardar o processo se NIF for inválido
- ✅ **Importar Imóveis via Excel**:
  - Novo endpoint `POST /api/properties/bulk/import-excel`
  - Aceita ficheiros .xlsx e .xls
  - Colunas obrigatórias: titulo, preco, distrito, concelho, proprietario_nome
  - 14 colunas opcionais: tipo, quartos, area_util, estado, etc.
  - Retorna estatísticas: total, importados, erros com linha
  - Erros são logados na colecção `error_logs` para análise
  - Novo endpoint `GET /api/properties/bulk/import-template` com instruções
  - Botão "Importar Excel" na página de Imóveis
  - Dialog mostra resultados da importação com erros detalhados
- ✅ **Sistema de Sugestões de Melhoria (Aprender com Erros)**:
  - Novo endpoint `GET /api/ai/bulk/import-errors/suggestions`
  - Analisa padrões nos erros de importação
  - Gera sugestões categorizadas por: validation, format, data_quality, geography, owner_data
  - Cada sugestão tem: título, descrição, acção recomendada, prioridade
  - Identifica erros de: campos em falta, formato errado, NIFs inválidos, localização

**8 Fevereiro 2026** (noite - final)
- ✅ **UI Gestão de Clientes**: Nova página `/clientes` com:
  - Lista de clientes com pesquisa por nome/email/NIF
  - Estatísticas (total clientes, com processos activos)
  - Criar novos clientes
  - Criar processos para clientes existentes
  - Eliminar clientes (se sem processos activos)
- ✅ **Múltiplos Processos por Cliente**: Backend completo e testado
  - `POST /api/clients/{id}/create-process` - processo #153 criado com sucesso
- ❌ **Removida integração Idealista**: A pedido do utilizador, para evitar ban da conta empresarial

**8 Fevereiro 2026** (noite - continuação)
- ✅ **Múltiplos Processos por Cliente**: Nova arquitectura que permite um cliente ter múltiplos processos de compra:
  - Novo modelo `Client` separado do `Process`
  - Rotas CRUD em `/api/clients`
  - Endpoints: `POST /clients/{id}/link-process`, `POST /clients/{id}/create-process`, `GET /clients/{id}/processes`
  - Endpoint `POST /clients/find-or-create` para encontrar ou criar cliente automaticamente
- ✅ **Co-Compradores no Frontend**: Secção visual na ficha de cliente mostrando co-compradores e co-proponentes detectados em documentos (CPCV, IRS conjunto, simulações)
- ✅ **Integração API Idealista**: Serviço `services/idealista_api.py` com OAuth2, pesquisa por localização, filtros de preço/tipologia
  - Endpoints: `POST /api/leads/search/idealista`, `GET /api/leads/search/idealista/status`
  - Requer configuração: `IDEALISTA_API_KEY` e `IDEALISTA_API_SECRET` no .env

**8 Fevereiro 2026** (noite)
- ✅ **Bug Fix Crítico - Análise de Documentos**: Corrigido bug onde dados extraídos de documentos não eram guardados quando `personal_data`, `financial_data` ou `real_estate_data` eram `None` (em vez de `{}`). O problema estava na função `build_update_data_from_extraction` em `services/ai_document.py` que usava `.get("key", {})` que retorna `None` quando a chave existe mas tem valor `None`, causando erro `NoneType.update()`. Corrigido para usar `.get("key") or {}`.
- ✅ **Deteção de Documentos Duplicados (P1)**: Implementada persistência de hashes de documentos na base de dados para evitar re-análise de documentos idênticos, mesmo após reinício do servidor:
  - Novos campos `analyzed_documents` array em cada processo
  - Função `check_duplicate_comprehensive()` verifica cache + DB
  - Função `persist_document_analysis()` guarda hash, tipo, data, campos extraídos
  - Novo endpoint `GET /api/ai/bulk/analyzed-documents/{process_id}` lista documentos analisados
  - Expandido para mais tipos: recibo_vencimento, extrato_bancario, irs, contrato_trabalho, certidao
- ✅ **Múltiplos Compradores/Proponentes (P2)**: Sistema detecta automaticamente múltiplas pessoas em documentos:
  - **CPCV**: Extrai array `compradores` com dados de todos os compradores (casal/parceiros)
  - **Simulação Crédito**: Extrai array `proponentes` e calcula `rendimento_agregado`
  - **IRS Conjunto**: Detecta cônjuge (sujeito passivo B) e guarda em `co_applicants`
  - Prompts da IA actualizados para identificar "Proponente 1", "Proponente 2", "Cônjuge"
  - Novos campos no processo: `co_buyers`, `co_applicants`
  - Endpoint de diagnóstico mostra co-compradores se existirem

**11 Fevereiro 2026** (continuação)
- ✅ **Pipeline CI/CD Corrigida**:
  - Adicionado `seed.py` ao workflow para criar utilizadores de teste
  - Adicionado `libmagic1` como dependência de sistema
  - Adicionado `arq` ao requirements.txt
  - Testes agora passam no GitHub Actions
- ✅ **Redução de Emails para Admin**:
  - Emails de novo cliente enviados apenas para o PRIMEIRO admin/ceo
  - Outros admins recebem notificação via sistema interno (sem spam)
- ✅ **Smart Crawler (Navegação Recursiva)**:
  - Novo método `crawl_recursive(start_url, max_pages, max_depth)` em `scraper.py`
  - Novo endpoint `POST /api/scraper/crawl` para crawling de múltiplas páginas
  - Extrai automaticamente links de imóveis dentro do mesmo domínio
  - Suporta até 50 páginas e profundidade 3
  - Endpoint `GET /api/scraper/supported-sites` lista sites suportados
- ✅ **Motor de Validação de Documentos**:
  - Novo serviço `document_processor.py`
  - Conversão automática de imagens para PDF (img2pdf)
  - Campo `data_emissao` adicionado ao modelo de documento
  - Validação de validade: documentos com mais de 180 dias (6 meses) são alertados
  - Função `validate_document_for_process()` verifica todos os documentos
- ✅ **Calendário Global (Visão CEO)**:
  - Endpoint `GET /api/tasks` aceita `?user_id=all` para admin/ceo
  - Retorna tarefas de toda a equipa para calendário global
  - Filtro `?user_id=<id>` para ver tarefas de utilizador específico
  - Permissões: apenas admin/ceo/diretor podem ver tarefas de outros
- ✅ **Webhooks Trello Bidirecionais**:
  - Endpoint `POST /api/trello/webhook` melhorado
  - Processa `addMemberToCard`: atribui consultor/mediador automaticamente
  - Processa `removeMemberFromCard`: remove atribuição
  - Movimento de cartões actualiza status do processo
  - Usa mapeamento `trello_member_mappings` para identificar utilizadores

**8 Fevereiro 2026**
- ✅ **Upload de Fotos para Imóveis**: Novos endpoints `/api/properties/{id}/upload-photo` e `DELETE /photo`
- ✅ **Notificações Automáticas de Match**: Sistema notifica quando imóvel novo tem clientes compatíveis (score ≥50%)
- ✅ **Filtro de Extracção de Nomes**: Lista de palavras bloqueadas (seguradoras, bancos) para evitar extracção incorrecta
- ✅ **Match Automático Cliente ↔ Imóvel (P1 Completo)**:
  - Novo endpoint `/api/match/client/{id}/all` combina leads + imóveis angariados
  - Novo endpoint `/api/match/property/{id}/clients` encontra clientes para imóvel angariado
  - Score baseado em preço (40pts), localização (35pts), tipologia (25pts)
- ✅ **Módulo Imóveis Angariados (P0 Completo)**:
  - Backend: Modelo `Property` com dados completos
  - API CRUD: `/api/properties` com filtros, estatísticas
  - Frontend: Página `/imoveis` com cards, filtros, formulário
  - Referências automáticas (IMO-001, IMO-002...)
- ✅ **ScraperAPI Integrado**: Para contornar bloqueios de portais imobiliários
- ✅ **Sanitização de Emails**: Função `sanitize_email()` em 3 locais críticos

**6 Fevereiro 2026**
- ✅ Sincronizado ambiente de desenvolvimento com MongoDB Atlas de produção
- ✅ Configurada separação de dados: `powerprecision_dev` (testes) vs `powerprecision` (produção)
- ✅ Código local mantido (inclui otimização de verificação de cliente no upload massivo)
- ✅ Comparadas diferenças com repositório GitHub - código local mais avançado

**5 Fevereiro 2026**
- Corrigido bug de layout dos botões no Kanban (CSS Grid)
- Implementado botão "Abrir no OneDrive" na página de detalhes
- Limpeza de código (removido onedrive_shared.py redundante)
- Testada funcionalidade de atribuição de processos via API
