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

## Última Actualização - 13 Fevereiro 2026 (Sessão 24)

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

#### P0 (Críticas - Próximas)
- [ ] **Documentos não aparecem na página do cliente** - O endpoint `/onedrive/files/{clientName}` não existe no backend. Precisa implementação ou verificação da integração OneDrive/S3
- [ ] **Teste da correcção OpenAI 401** - O código foi actualizado para usar emergentintegrations mas precisa teste com importação real de documentos

#### P1 (Alta Prioridade)
- [x] **"Gestor de Visitas"** - Funcionalidade já implementada! Renomeado de "Leads". Inclui:
  - Kanban com estados: Novo, Contactado, Visita Agendada, Proposta, Reservado, Descartado
  - Extração automática de dados de URLs de imóveis (scraping)
  - Formulário completo para criar leads manualmente
  - Filtros por consultor e estado

#### P1 (Bugs Menores)
- [ ] **ImportErrorsPage** - Campo `error_type` não existe na API, usa `error` (ajustar filtros)
- [ ] **Toast de erro** - Algumas páginas mostram toast "Erro ao carregar" mesmo quando dados carregam

#### P2 (Média Prioridade)
- [ ] Implementar rate limiting no backend
- [ ] Paginação cursor-based para listas grandes
- [ ] Funcionalidade "selecionar erros" nos logs - Precisa clarificação do utilizador sobre o objectivo

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
