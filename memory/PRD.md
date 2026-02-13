# CreditoIMO - Product Requirements Document

## Problema Original
Aplicação de gestão de processos de crédito habitação e transações imobiliárias que funciona como "espelho" de um quadro Trello, com sincronização bidirecional.

## Stack Técnica
- **Frontend**: React + Vite (migrado de CRA), Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, Pydantic, Motor (MongoDB async)
- **Base de Dados**: MongoDB Atlas (Cluster: cluster0.c8livu.mongodb.net)
  - **Desenvolvimento/Testes**: `powerprecision_dev`
  - **Produção**: `powerprecision`
- **Integrações**: Trello API & Webhooks, IMAP/SMTP (emails), Cloud Storage (S3, Google Drive, OneDrive, Dropbox - configurável pelo admin), Gemini 2.0 Flash (scraping), AWS S3 (documentos)

## Última Actualização - 13 Fevereiro 2026 (Sessão 21)

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

#### P0: Correcção do Erro 401 OpenAI - EM ANÁLISE
- **Problema**: Erro 401 Unauthorized ao chamar API OpenAI durante importações massivas
- **Solução Aplicada**: Modificado ai_document.py para usar emergentintegrations/litellm em vez de chamadas directas à API OpenAI
- **Ficheiros**: `/app/backend/services/ai_document.py`
- **Status**: ⏳ CÓDIGO ACTUALIZADO, AGUARDA TESTE COM DOCUMENTOS REAIS

### ✅ Tarefas Completadas (Sessão 20)

#### P1: Unificação das Páginas de Logs - COMPLETO
- **Problema**: Utilizador pediu para juntar as páginas de logs
- **Solução**: Criada página unificada `UnifiedLogsPage.js` com duas tabs:
  - Tab "Erros do Sistema" - Logs de erros da aplicação
  - Tab "Importações IA" - Logs de importação massiva com dados categorizados
- **Funcionalidades**:
  - Cards de estatísticas para ambas as tabs
  - Filtros avançados (severidade, componente, estado, período, tipo documento, cliente)
  - Visualização detalhada com dados organizados por categoria (Dados Pessoais, Imóvel, Financiamento, Outros)
- **Ficheiros modificados**:
  - `/app/frontend/src/pages/UnifiedLogsPage.js` - Nova página criada
  - `/app/frontend/src/App.js` - Rota actualizada
  - `/app/frontend/src/layouts/DashboardLayout.js` - Menu simplificado
- **Ficheiros removidos**:
  - `/app/frontend/src/pages/SystemLogsPage.js`
  - `/app/frontend/src/pages/AIImportLogsPage.js`
- **Status**: ✅ COMPLETO E TESTADO

#### P0: Correcção das Preferências de Email - COMPLETO
- **Problema**: Preferências de notificação não eram carregadas do servidor
- **Solução**: Adicionado `useEffect` para carregar preferências ao abrir a página de definições
- **Ficheiro**: `/app/frontend/src/pages/SettingsPage.js`
- **Status**: ✅ CORRIGIDO

#### P1: Correcção da Página "Mapeamento NIF" - COMPLETO
- **Problema**: Erro toast ao carregar página devido a URL duplicada `/api/api/...`
- **Solução**: Corrigidos os paths da API (removido `/api` duplicado)
- **Ficheiro**: `/app/frontend/src/pages/NIFMappingsPage.js`
- **Status**: ✅ CORRIGIDO

#### P1: Correcção do Menu Mobile - COMPLETO
- **Problema**: Potencial sobreposição de z-index entre sidebar e bottom nav
- **Solução**: Ajustado z-index do MobileBottomNav de z-50 para z-40
- **Ficheiro**: `/app/frontend/src/components/layout/MobileBottomNav.jsx`
- **Status**: ✅ CORRIGIDO

#### P1: Configuração SMTP - VERIFICADO
- **Problema**: Utilizador pediu para finalizar configuração SMTP
- **Solução**: Verificado que a configuração SMTP já existia e está funcional
- **Localização**: Página `/configuracoes` → Tab "Configuração"
- **Status**: ✅ JÁ IMPLEMENTADO E FUNCIONAL

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
