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

## Última Actualização - 13 Fevereiro 2026 (Sessão 17)

### ✅ Tarefas P1 Completas (Sessão 17)

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

#### P1: Parâmetro force_client_id na Extração - COMPLETO
- **Problema**: Necessidade de forçar associação de documentos a um cliente específico
- **Cenário A (Upload Massivo)**: Nome da pasta = nome do cliente
- **Cenário B (Página do Cliente)**: Usa force_client_id, ignora nome da pasta
- **Solução**: Adicionado parâmetro `force_client_id` ao endpoint `/api/ai/bulk/analyze-single`
- **Ficheiros**: `/app/backend/routes/ai_bulk.py`
- **Status**: ✅ COMPLETO

#### P1: Processamento de Ficheiros em Threads - COMPLETO
- **Problema**: Processamento de Excel/PDF em async def bloqueava event loop
- **Solução**: Criado `backend/services/file_processor.py` com ThreadPoolExecutor
- **Implementação**:
  - Funções síncronas: `process_excel_sync()`, `process_pdf_sync()`
  - Wrappers async: `process_excel_async()`, `process_pdf_async()`
  - Usa `run_in_executor()` para não bloquear
- **Status**: ✅ COMPLETO

#### P1: Remoção de "OneDrive não configurado" - COMPLETO
- **Problema**: Mensagens específicas de "OneDrive" quando storage é configurável
- **Solução**:
  - Criado novo componente `DriveLinks.js` (genérico)
  - Criado endpoint `/api/system-config/storage-info`
  - Removidas todas as mensagens "OneDrive não configurado"
  - Terminologia actualizada: "Pasta Drive" em vez de "Pasta OneDrive"
- **Ficheiros Modificados**:
  - `/app/frontend/src/components/DriveLinks.js` (novo)
  - `/app/frontend/src/components/UnifiedDocumentsPanel.js`
  - `/app/frontend/src/pages/UsersManagementPage.js`
  - `/app/frontend/src/components/AIDocumentAnalyzer.js`
  - `/app/frontend/src/components/DocumentChecklist.js`
  - `/app/backend/routes/system_config.py`
- **Status**: ✅ COMPLETO

#### P1: Skeleton Loaders - PARCIALMENTE IMPLEMENTADO
- **Estado**: Componentes existem em `/app/frontend/src/components/ui/skeletons.jsx`
- **Integração**: `TableSkeleton` integrado na página de Clientes
- **Pendente**: Integrar em mais páginas (Dashboard, Processos)

### Bugs Corrigidos (Sessão 17)

#### Bug: "OneDrive não configurado" aparecia mesmo com S3 configurado
- **Causa**: Componente verificava apenas link do OneDrive, não o storage activo
- **Solução**: Novo componente DriveLinks busca `/api/system-config/storage-info` para saber qual storage está activo
- **Status**: ✅ CORRIGIDO

### 📋 Tarefas Pendentes

#### P1 (Alta Prioridade)
- [ ] Completar integração de skeleton loaders em todas as páginas

#### P2 (Média Prioridade)
- [ ] Implementar rate limiting no backend
- [ ] Paginação cursor-based para listas grandes

#### P3 (Baixa Prioridade)
- [ ] Refactoring do `processes.py` (ficheiro muito grande)
- [ ] Cache Redis para dados frequentes

### Credenciais de Teste
- **Admin**: admin@admin.com / admin
- **Consultor**: flaviosilva@powerealestate.pt / flavio123

### Ficheiros Importantes
- `/app/frontend/vite.config.js` - Configuração Vite
- `/app/backend/models/auth.py` - UserRoleEnum
- `/app/backend/services/file_processor.py` - Processamento ficheiros em threads
- `/app/frontend/src/components/DriveLinks.js` - Componente de links genérico
- `/app/backend/routes/system_config.py` - Endpoint storage-info

### Notas Técnicas
- **Storage Dinâmico**: O admin escolhe o provider (S3, Google Drive, OneDrive, Dropbox) nas configurações do sistema
- **force_client_id**: Quando na página de um cliente, todos os documentos são associados a esse cliente independentemente do nome da pasta
- **ThreadPoolExecutor**: 4 workers para processamento de PDF/Excel (suficiente para operações I/O-bound)
