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

### ✅ Impersonate - Admin Ver Como Outro Utilizador (2026-01)
- Endpoint POST `/api/admin/impersonate/{user_id}`
- Endpoint POST `/api/admin/stop-impersonate`
- Banner amarelo no frontend quando em modo impersonate
- Botão "Ver como" na página de gestão de utilizadores
- Auditoria registada na colecção history

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

## Próximas Tarefas
- [x] Sistema de Alertas e Notificações (Completo)
- [x] Notificações em Tempo Real com Som (Completo)
- [x] Editor de Fluxos de Workflow (Completo)
- [x] Indicador Visual Trello (Completo)
- [x] Refatorização Admin Dashboard (Completo)
- [x] Documentação completa (GUIA_UTILIZADOR.md, APRESENTACAO.md) (Completo)
- [x] CI/CD Pipeline para testes automatizados (Completo)
- [x] WebSocket para notificações em tempo real (Completo)
- [ ] Integração bidirecional com Trello (em standby por testes)
- [ ] Testar análise AI com documentos reais (em standby)
