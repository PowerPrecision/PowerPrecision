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

## Última Actualização - 13 Fevereiro 2026 (Sessão 18)

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
