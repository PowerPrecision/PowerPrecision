# CreditoIMO - Sistema de Registo de Clientes
## Power Real Estate & Precision

## Problem Statement
Sistema de registo de clientes para crédito e assistência imobiliária. Clientes preenchem formulário público (sem login). Consultores, mediadores e CEO gerem os processos num quadro Kanban visual estilo Trello.

## Sites de Referência
- **Imobiliária**: https://www.powerealestate.pt/
- **Crédito**: https://precision-credito.pt/

## User Roles (Hierarquia)
1. **Admin** - Gestão total do sistema, utilizadores e workflow
2. **CEO** - Vê todos os processos, pode fazer tudo que consultor e mediador fazem
3. **Diretor(a)** - Pode fazer tarefas de consultor E mediador
4. **Administrativo(a)** - Gestão administrativa, vê todos os processos
5. **Consultor** - Gere dados imobiliários, vê apenas os seus clientes atribuídos
6. **Intermediário/Mediador** - Gere dados de crédito, vê apenas os seus clientes atribuídos
7. **Cliente** - Preenche formulário público (sem login no sistema)

## Credenciais de Acesso
| Nome | Email | Role | Password |
|------|-------|------|----------|
| Pedro Borges | pedro@powerealestate.pt | CEO | power2026 |
| Tiago Borges | tiago@powerealestate.pt | Consultor | power2026 |
| Flávio da Silva | flavio@powerealestate.pt | Consultor | power2026 |
| Estácio Miranda | estacio@precisioncredito.pt | Intermediário | power2026 |
| Fernando Andrade | fernando@precisioncredito.pt | Intermediário | power2026 |
| Carina Amuedo | carina@powerealestate.pt | Diretor(a) | power2026 |
| Marisa Rodrigues | marisa@powerealestate.pt | Administrativo(a) | power2026 |
| Admin | admin@sistema.pt | Admin | admin2026 |

## What's Been Implemented

### ✅ Impersonate - Admin Ver Como Outro Utilizador (2026-01-23)
- Endpoint POST `/api/admin/impersonate/{user_id}`
- Endpoint POST `/api/admin/stop-impersonate`
- Banner amarelo no frontend quando em modo impersonate
- Botão "Ver como" (ícone de olho) na página de gestão de utilizadores
- Auditoria registada na colecção history
- **BUG FIX (2026-01-23)**: Corrigido endpoint `/api/auth/me` para retornar campos `is_impersonated`, `impersonated_by`, `impersonated_by_name`

### ✅ Refatorização AdminDashboard (2026-01-23)
- AdminDashboard.js reduzido de 1200 para 315 linhas (~74% redução)
- Criados componentes modulares em `/components/admin/`:
  - `CalendarTab.js` - Gestão de calendário e prazos
  - `DocumentsTab.js` - Lista de documentos a expirar
  - `UsersTab.js` - Lista e gestão de utilizadores
  - `ClientSearchTab.js` - Pesquisa de clientes
  - `AIAnalysisTab.js` - Análise de documentos por IA
  - `CreateEventDialog.js` - Dialog para criar eventos
- Melhor manutenção e testabilidade do código

### ✅ Integração IMAP/SMTP de Email (2026-01-25)
- **Duas contas configuradas**:
  - Precision: geral@precisioncredito.pt (mail.precisioncredito.pt)
  - Power: geral@powerealestate.pt (webmail2.hcpro.pt)
- **Sincronização automática** de emails via IMAP:
  - Busca INBOX e Sent folders
  - Filtra por email do cliente
  - Detecta duplicados
- **Envio de emails** via SMTP
- **Endpoints**:
  - `GET /api/emails/test-connection` - Testar conexão
  - `GET /api/emails/accounts` - Listar contas
  - `POST /api/emails/sync/{process_id}` - Sincronizar emails
  - `POST /api/emails/send` - Enviar email
- **Frontend**: Botão de sincronização no EmailHistoryPanel

### ✅ Calendário CEO/Admin - Ver Todos os Utilizadores (2026-01-25)
- **Filtro de utilizadores** no calendário (apenas visível para admin/CEO)
- Dropdown com todos os utilizadores staff (excluindo clientes)
- Mostra nome e role de cada utilizador
- Filtra eventos por participante/atribuído
- Funciona em conjunto com filtros de prioridade e consultor

### ✅ Histórico de Emails (2026-01-25)
- **Backend CRUD completo** em `/routes/emails.py`:
  - `POST /api/emails` - Criar registo de email
  - `GET /api/emails/process/{id}` - Listar emails do processo
  - `GET /api/emails/stats/{id}` - Estatísticas (total, enviados, recebidos)
  - `DELETE /api/emails/{id}` - Eliminar email
- **Frontend** - Componente `EmailHistoryPanel.js`:
  - Separador "Emails" na ficha do cliente
  - Filtros: Todos, Enviados, Recebidos
  - Lista de emails com expand/collapse
  - Ícones de direção (enviado/recebido)
  - Dialog para criar email com tipo, de, para, assunto, corpo, notas
  - Email do cliente pré-preenchido

### ✅ Melhorias UI - Dashboard e Pesquisa (2026-01-25)
- **Cards clicáveis no dashboard**: Navegam para lista filtrada
  - Total → /processos
  - Ativos → /processos-filtrados?filter=active
  - Concluídos → /processos-filtrados?filter=concluded
  - Desistências → /processos-filtrados?filter=dropped
  - Prazos Pendentes → /processos-filtrados?filter=pending_deadlines
- **Página FilteredProcessList**: Lista filtrada com pesquisa, tabela com detalhes
- **Pesquisa no Quadro Geral**: Toggle entre vista Kanban e Lista (2+ caracteres)
- **ProcessSummaryCard**: Resumo no topo da ficha do cliente (Cliente, Contacto, Imóvel, Financiamento, Equipa, Dias no Sistema)

### ✅ Sistema de Tarefas (2026-01-25)
- **Backend CRUD completo** em `/routes/tasks.py`:
  - `POST /api/tasks` - Criar tarefa
  - `GET /api/tasks` - Listar tarefas (filtros: process_id, assigned_to_me, include_completed)
  - `GET /api/tasks/my-tasks` - Tarefas atribuídas a mim
  - `PUT /api/tasks/{id}/complete` - Marcar como concluída
  - `PUT /api/tasks/{id}/reopen` - Reabrir tarefa
  - `DELETE /api/tasks/{id}` - Eliminar tarefa
- **Frontend** - Componente `TasksPanel.js`:
  - Criar tarefas com título, descrição, utilizadores
  - Atribuir a múltiplos utilizadores
  - Marcar como concluída/reabrir
  - Filtrar por concluídas
- **Integração**:
  - Separador "Tarefas" no Admin Dashboard
  - Painel de tarefas na ficha do cliente (ProcessDetails)
  - Prefixo automático `[Nome do Cliente]` quando criada da ficha
- **Notificações**: Enviadas quando tarefa é atribuída

### ✅ Melhorias no Calendário (2026-01-25)
- **Novo layout**: Calendário mensal à esquerda, "Próximos Eventos" à direita
- **Renomeado** "Próximos Prazos" → "Próximos Eventos"
- Filtros de prioridade e consultor abaixo do calendário
- Mostra até 10 próximos eventos com detalhes

### ✅ Alertas Automáticos (2026-01-25)
- **Clientes em espera 15+ dias**: Alerta para CEO/Diretor/Admin
- **Lembrete mensal (1º dia)**: 
  - Notificação para consultor/intermediário
  - Email automático ao cliente para pedir recibo e extrato
- Implementado em `services/scheduled_tasks.py`
- Executar via: `python -m services.scheduled_tasks` ou modo daemon

### ✅ Push Notifications - Completo com VAPID (2026-01-24)
- **Backend endpoints** implementados em `/routes/push_notifications.py`:
  - `POST /api/notifications/push/subscribe` - Registar subscrição
  - `POST /api/notifications/push/unsubscribe` - Cancelar subscrição
  - `GET /api/notifications/push/status` - Estado das subscrições
- **VAPID configurado** para envio de push notifications reais:
  - Biblioteca `pywebpush` instalada
  - Chaves VAPID geradas e configuradas
  - Backend envia push via Web Push API
- **Service Worker** para receber notificações push (`/public/sw-push.js`)
- **Serviço de gestão** de notificações (`/services/pushNotifications.js`) com integração backend
- **Hook React** para gestão de estado (`/hooks/usePushNotifications.js`)
- **Componente de configuração** (`/components/NotificationSettings.js`) em Definições > Notificações
- **Colecção MongoDB** `push_subscriptions` para armazenar subscrições
- **Integração com notificações em tempo real**: Push enviado quando utilizador offline
- **Auto-limpeza**: Subscrições expiradas ou inválidas são desactivadas automaticamente
- Tipos de notificação: novos processos, alterações, documentos a expirar, prazos

### ✅ Correção WebSocket URL (2026-01-24)
- Corrigida construção de URL do WebSocket no hook `useWebSocket.js`
- Usa API `URL()` para parsing correto de protocolo e host
- Resolve bug `ws://localhost:443/ws` em ambiente de preview
- Transforma corretamente `https://` → `wss://` e `http://` → `ws://`
- Adicionada validação de URL antes de conectar
- Melhor tratamento de erros de conexão

### ✅ Email Templates HTML Profissionais (2026-01)
- Template base com estilos consistentes
- Confirmação de registo (enviado ao cliente automaticamente)
- Lista de documentos necessários
- Aprovação de crédito
- Notificação de novo cliente (para staff)
- Actualização de estado

### ✅ Botão Email Rápido no Kanban (2026-01)
- Ícone de email em cada cartão de cliente
- Abre mailto: com email e nome do cliente preenchidos

### ✅ Cliente NÃO é Utilizador (2026-01)
- Registo público cria apenas documento em Processes
- Dados do cliente guardados directamente no processo
- Removida criação de utilizador no registo público
- Email de confirmação enviado automaticamente ao cliente

### ✅ Optimização Análise de Documentos AI (2026-01)
- Modelo alterado para `gpt-4o-mini` (mais económico)
- Extracção de texto de PDF com `pypdf` primeiro
- Se texto suficiente (>100 chars), usa apenas texto (sem visão)
- Redimensionamento de imagens para max 1024px antes de enviar
- Compressão JPEG com qualidade 85%

### ✅ Segurança e Configuração (2026-01)
- Variáveis de ambiente obrigatórias (JWT_SECRET, MONGO_URL, DB_NAME)
- Falha rápida se variáveis críticas não definidas
- Passwords movidas para variáveis de ambiente no seed.py
- Validador de NIF (9 dígitos numéricos) nos modelos Pydantic
- Campos legacy removidos dos modelos (address, monthly_income, etc.)

### ✅ Tarefas Agendadas - Cron Jobs (2026-01)
- `services/scheduled_tasks.py` - Sistema de tarefas agendadas
- Verificação diária de documentos a expirar
- Verificação de prazos próximos (24h)
- Countdown de pré-aprovação (90 dias)
- Limpeza de notificações antigas
- Suporte a modo daemon (--daemon) e execução manual

### ✅ Colecção Notifications MongoDB (2026-01)
- Índices criados no startup do servidor
- Notificações criadas quando processo muda de fase
- Frontend actualizado com ícone para `process_status_change`
- Integração com WebSocket para tempo real

### ✅ CI/CD Pipeline (2026-01)
- GitHub Actions workflow completo (`.github/workflows/ci-cd.yml`)
- Testes backend (pytest com MongoDB)
- Testes frontend (Jest)
- Testes de integração
- Scan de segurança (Trivy)
- Deploy automático para main

### ✅ WebSocket para Notificações em Tempo Real (2026-01)
- `services/websocket_manager.py` - Gestor de conexões
- `services/realtime_notifications.py` - Serviço de notificações
- `routes/websocket.py` - Endpoints WebSocket
- `hooks/useWebSocket.js` - Hook React para frontend
- Suporte a heartbeat e reconexão automática

### ✅ Editor de Fluxos de Workflow (2026-01)
- **Nova UI completa** na página de Definições para gerir estados do workflow
- Criar, editar, eliminar e reordenar estados
- Selecção de cores e descrições
- Protecção contra eliminação de estados em uso

### ✅ Indicador Visual Trello (2026-01)
- Badge "Trello" visível nos cartões Kanban sincronizados
- Preparado para integração bidirecional futura

### ✅ Refatorização Admin Dashboard (2026-01)
- Tab de Utilizadores simplificada com estatísticas rápidas
- Redireccionamento para página dedicada de gestão
- Remoção de código duplicado

### ✅ Correções de Bugs Críticos (2026-01-23)
- **BUG FIX**: Endpoint `/api/workflow-statuses` não existia - frontend agora usa `/api/admin/workflow-statuses`
- **BUG FIX**: `ProcessDetails.js` tinha imports em falta (`getClientOneDriveFiles`, `getOneDriveDownloadUrl`)
- **Ficheiros corrigidos**: `/app/frontend/src/services/api.js`, `/app/frontend/src/pages/ProcessDetails.js`, `/app/backend/routes/auth.py`

### ✅ Múltiplas Melhorias de UI e Funcionalidades (2026-01-22)
- **Credenciais de teste removidas** da página de login
- **Novos perfis de utilizador**: Diretor(a) e Administrativo(a) substituem Consultor/Mediador
- **Checkbox "Menor de 35 anos"** no formulário público para Apoio ao Estado
- **Layout ProcessDetails reorganizado**: Atividade movida para sidebar direita
- **Criação de eventos corrigida**: assigned_user_ids inicializado corretamente
- **Notificações filtradas por papel**: Admin/CEO/Diretor vêem todas as notificações
- **Botão de edição de workflow** adicionado nas Definições (admin)

### ✅ Sistema de Alertas e Notificações (2026-01-22)
- **Alerta de Idade (<35 anos)**: Clientes elegíveis para Apoio ao Estado identificados automaticamente
- **Countdown de 90 dias**: Após pré-aprovação, contador regressivo visível na página do processo
- **Alerta de Documentos**: Notificação 15 dias antes da expiração de CC, Passaporte ou IRS
- **Verificação de Documentos do Imóvel**: Ao mover para avaliação, verifica docs em falta
- **Alerta de Escritura**: Lembrete automático no calendário 15 dias antes
- **UI de Notificações**: Ícone de sino no header com badge de contagem não lidas
- **Componente ProcessAlerts**: Painel colapsível com alertas na página de detalhes
- **Notificações em Tempo Real**: Polling a cada 10 segundos com toast e som quando chega nova notificação
- **Controlo de Som**: Botão para ativar/desativar som das notificações

### ✅ Dados Importados do Trello (2026-01-20)
- **155 processos** no sistema com dados de teste
- **14 fases** do workflow conforme Trello

### ✅ Quadro Kanban Visual (Estilo Trello)
- Colunas coloridas por fase
- Drag & drop para mover clientes entre fases
- Filtro automático por role (Admin/CEO vêem tudo, staff vê apenas os seus)
- Cards com nome, telefone, valor, prioridade, badges de atribuição
- Badge "<35 anos" para clientes elegíveis ao Apoio ao Estado

### ✅ Email SMTP Funcional
- Servidor: mail.precisioncredito.pt:465 (SSL)
- Email de envio: admin@precisioncredito.pt
- Notificações automáticas quando cliente muda de fase

### ✅ OneDrive - Links de Partilha Manual
- Cada processo pode ter múltiplos links de pastas partilhadas
- Interface simples para adicionar/remover links
- Instruções integradas de como criar links de partilha
- Não requer subscrição Microsoft 365 Business

### ✅ Gestão de Eventos/Calendário
- Criação de eventos por todos os utilizadores (exceto clientes)
- Utilizador sempre adicionado ao próprio evento
- Pode convidar outros utilizadores para eventos
- Filtro por consultor/intermediário

### ✅ Documentos a Expirar
- Vista agrupada por cliente
- Ordenação por data de validade (mais urgentes primeiro)
- Código de cores por urgência (vermelho ≤7 dias, âmbar ≤30 dias, azul >30 dias)

## 14 Fases do Workflow
1. Clientes em Espera (Amarelo)
2. Fase Documental (Azul)
3. Fase Documental II (Azul)
4. Enviado ao Bruno (Roxo)
5. Enviado ao Luís (Roxo)
6. Enviado BCP Rui (Roxo)
7. Entradas Precision (Laranja)
8. Fase Bancária - Pré Aprovação (Laranja)
9. Fase de Visitas (Azul)
10. CH Aprovado - Avaliação (Verde)
11. Fase de Escritura (Verde)
12. Escritura Agendada (Verde)
13. Concluídos (Verde)
14. Desistências (Vermelho)

## URLs
- **Formulário Público**: / ou /registo
- **Login Staff**: /login
- **Dashboard Staff**: /staff (Kanban)
- **Dashboard Admin**: /admin
- **Detalhes Processo**: /process/{id}
- **Definições**: /definicoes

## Integrações
| Integração | Estado | Config |
|------------|--------|--------|
| SMTP Email | ✅ FUNCIONAL | mail.precisioncredito.pt:465 |
| OneDrive (Links) | ✅ FUNCIONAL | Links de partilha manuais |
| GPT-4o (AI) | ⏳ Preparado | EMERGENT_LLM_KEY |

## APIs de Alertas
- `GET /api/processes/{id}/alerts` - Todos os alertas do processo
- `GET /api/alerts/notifications` - Notificações do utilizador
- `PUT /api/alerts/notifications/{id}/read` - Marcar como lida
- `GET /api/alerts/age-check/{id}` - Verificar elegibilidade idade
- `GET /api/alerts/pre-approval/{id}` - Countdown pré-aprovação
- `GET /api/alerts/documents/{id}` - Documentos a expirar

## APIs de Tarefas
- `POST /api/tasks` - Criar tarefa
- `GET /api/tasks` - Listar tarefas (filtros: process_id, assigned_to_me, created_by_me, include_completed)
- `GET /api/tasks/my-tasks` - Tarefas atribuídas ao utilizador atual
- `GET /api/tasks/{id}` - Detalhes de uma tarefa
- `PUT /api/tasks/{id}` - Atualizar tarefa
- `PUT /api/tasks/{id}/complete` - Marcar como concluída
- `PUT /api/tasks/{id}/reopen` - Reabrir tarefa concluída
- `DELETE /api/tasks/{id}` - Eliminar tarefa

## APIs de Push Notifications
- `POST /api/notifications/push/subscribe` - Registar subscrição
- `POST /api/notifications/push/unsubscribe` - Cancelar subscrição
- `GET /api/notifications/push/status` - Estado das subscrições do utilizador

## APIs de Emails
- `POST /api/emails` - Criar registo de email
- `GET /api/emails/process/{id}` - Listar emails de um processo (filtro: direction)
- `GET /api/emails/{id}` - Detalhes de um email
- `PUT /api/emails/{id}` - Atualizar email (subject, body, notes, status)
- `DELETE /api/emails/{id}` - Eliminar email
- `GET /api/emails/stats/{id}` - Estatísticas (total, sent, received)

## Tarefas Agendadas (Cron)
Executar: `cd /app/backend && python -m services.scheduled_tasks`
Ou modo daemon: `python -m services.scheduled_tasks --daemon`

| Tarefa | Descrição | Frequência |
|--------|-----------|------------|
| check_expiring_documents | Documentos a expirar nos próximos 7 dias | Diária |
| check_upcoming_deadlines | Prazos nas próximas 24 horas | Diária |
| check_pre_approval_countdown | Pré-aprovações a expirar (90 dias) | Diária |
| check_clients_waiting_too_long | Clientes em espera 15+ dias | Diária |
| send_monthly_document_reminder | Lembrete para recibo/extrato | 1º dia do mês |
| cleanup_old_notifications | Limpar notificações lidas >30 dias | Diária |

## Próximas Tarefas (Backlog)

### 🟡 Prioridade Média - Melhorias UI
- [ ] Pesquisa com resultados em lista no Quadro Geral
- [ ] Resumo do processo no topo da ficha do cliente
- [ ] CEO ver calendário de todos os utilizadores
- [ ] Links clicáveis no dashboard para filtrar processos

### ⏸️ Em Stand-by
- [ ] Sistema de Documentos CPCV/Escritura (aguarda lista de documentos)
- [ ] Integração bidirecional com Trello
- [ ] Testar análise AI com documentos reais
- [ ] Histórico de emails na ficha do cliente
- [ ] Faturação
