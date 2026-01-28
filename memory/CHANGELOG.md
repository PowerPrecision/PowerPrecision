# CreditoIMO - Changelog

Registo de alterações do sistema CreditoIMO.

---

## [2026-01-25] - Página "Itens Pendentes" Dedicada

### Adicionado
- **Nova página `/pendentes`** - Lista unificada de todos os itens pendentes
  - Combina tarefas e prazos numa única lista
  - Ordenada por urgência (mais urgente primeiro)
  - Cards de filtro: Total, Tarefas, Prazos (clicáveis)
  - Badges visuais: tipo (Tarefa/Prazo) + urgência
  - Checkbox para marcar tarefas como concluídas
  - Link para ver processo associado
  - Responsivo para mobile

- **Card "Pendentes" no Dashboard**
  - Agora navega para `/pendentes` em vez do separador de tarefas
  - Mostra total combinado (tarefas + prazos)

---

## [2026-01-25] - Data de Vencimento nas Tarefas e Alertas Automáticos

### Adicionado
- **Campo "Data de Vencimento" nas Tarefas (opcional)**
  - Campo de data no dialog de criação de tarefa
  - Não obrigatório - tarefas podem ou não ter prazo
  - Validação: data mínima é hoje

- **Badges Visuais de Prazo nas Tarefas**
  - 🔴 Vermelho: "Atrasada (X dias)"
  - 🔴 Vermelho: "Vence hoje"
  - 🟠 Laranja: "Vence amanhã"
  - 🟡 Laranja claro: "X dias" (3 dias ou menos)
  - ⚪ Cinza: Data do prazo (mais de 3 dias)

- **Sistema de Alertas Automáticos para Tarefas**
  - Alerta 3 dias antes do vencimento
  - Alerta 1 dia antes (amanhã)
  - Alerta no dia do vencimento
  - Alerta quando atrasada
  - Notificações enviadas aos utilizadores atribuídos

- **Endpoint Atualizado**
  - `POST /api/tasks` - aceita campo `due_date` opcional
  - `GET /api/tasks` - retorna `due_date`, `is_overdue`, `days_until_due`

---

## [2026-01-25] - Separador "Minhas Tarefas" e Melhorias Mobile

### Adicionado
- **Separador "Minhas Tarefas" no StaffDashboard**
  - Novo separador visível para todos os utilizadores
  - Cada utilizador vê apenas as tarefas que lhe foram atribuídas
  - Endpoint `GET /api/tasks/my-tasks` filtra por utilizador

- **Card "Pendentes" Melhorado**
  - Agora mostra total de prazos + tarefas pendentes
  - Detalhe: "X tarefas • Y prazos"
  - Ao clicar, abre separador de tarefas

- **Botões "Todos" e "Nenhum" nas Tarefas**
  - Adicionados ao dialog de criação de tarefa
  - "Todos" selecciona todos os utilizadores
  - "Nenhum" limpa a selecção

- **Responsividade Mobile Melhorada**
  - Dashboard adaptado com grid 2x2 para cards de estatísticas
  - Separadores compactos (Quadro, Tarefas, Cal., Docs)
  - Kanban com navegação por setas entre colunas
  - Formulário público e ficha do cliente optimizados

### Alterado
- Contagem de "Pendentes" inclui agora tarefas + prazos (não apenas prazos)
- Endpoint `/api/stats` retorna `total_pending`, `pending_tasks`, `pending_deadlines`

---

## [2026-01-25] - Bloqueio de Duplicados e Alertas de Documentos

### Adicionado
- **Bloqueio de Registo Duplicado**
  - Verifica email existente antes de criar processo
  - Verifica NIF existente antes de criar processo
  - Mensagem amigável: "A nossa equipa entrará em contacto"
  - Contactos de ambas as empresas para dúvidas

- **Alerta de Verificação de Documentos**
  - Enviado quando processo muda para CH Aprovado, Fase Escritura ou Escritura Agendada
  - Notifica todos os envolvidos (consultor, mediador, staff)
  - Inclui lista de documentos em falta
  - Email + Notificação em tempo real

- **Etiqueta "Tem Imóvel" no Kanban**
  - Badge verde para processos com `has_property=True`
  - Visível no cartão do processo
  - Ajuda CEO a não atribuir a Consultor Imobiliário por engano

### Corrigido
- Erro 500 ao mover processo para fases de escritura (parâmetro `priority` inválido)
- Erro de encoding em emails com caracteres especiais (ex: `luís@...`)

---

## [2026-01-25] - Integração IMAP/SMTP Email

### Adicionado
- **Integração com dois servidores de email**
  - Precision: geral@precisioncredito.pt
  - Power Real Estate: geral@powerealestate.pt
- **Sincronização automática via IMAP**
  - Busca emails dos últimos 60 dias
  - Filtra por email do cliente
  - Remove duplicados
- **Envio de emails via SMTP**
- **Botão de sincronização** no painel de emails
- **Endpoints**: /test-connection, /accounts, /sync/{id}, /send

---

## [2026-01-25] - Calendário CEO e Histórico de Emails

### Adicionado
- **Filtro de utilizadores no Calendário**
  - Visível apenas para admin/CEO
  - Dropdown com todos os utilizadores staff
  - Filtra eventos por participante/atribuído

- **Sistema de Histórico de Emails**
  - Backend CRUD em `/api/emails`
  - Separador "Emails" na ficha do cliente
  - Filtros: Todos, Enviados, Recebidos
  - Dialog para criar emails enviados/recebidos
  - Email do cliente pré-preenchido
  - Estatísticas de emails por processo

---

## [2026-01-25] - Melhorias UI e Navegação

### Adicionado
- **Cards clicáveis no Dashboard**
  - Total, Ativos, Concluídos, Desistências, Prazos Pendentes
  - Navegação para `/processos-filtrados?filter=...`

- **Página FilteredProcessList**
  - Lista de processos filtrada por status
  - Pesquisa local por nome, email, telefone
  - Coluna especial "Prazo" para prazos pendentes

- **Pesquisa com Vista Lista no Kanban**
  - Toggle entre Kanban e Lista quando pesquisa tem 2+ caracteres
  - Vista lista com tabela detalhada

- **ProcessSummaryCard**
  - Resumo do processo no topo da ficha do cliente
  - Mostra: Cliente, Contacto, Imóvel, Financiamento, Equipa, Dias no Sistema

### Corrigido
- React hydration warning: Badge (div) dentro de p tag no StaffDashboard

---

## [2026-01-25] - Sistema de Tarefas e Melhorias

### Adicionado
- **Sistema de Tarefas Completo**
  - CRUD completo via `/api/tasks`
  - Separador "Tarefas" no Admin Dashboard
  - Painel de tarefas na ficha do cliente
  - Atribuição a múltiplos utilizadores
  - Notificações automáticas quando tarefa atribuída
  - Prefixo automático `[Nome do Cliente]` quando criada da ficha

- **Alertas Automáticos**
  - Alerta para clientes em espera há 15+ dias (CEO/Diretor)
  - Lembrete mensal (1º dia) para pedir recibo e extrato
  - Email automático ao cliente para documentos mensais

### Alterado
- **Layout do Calendário**: Calendário mensal à esquerda, eventos à direita
- **Renomeado**: "Próximos Prazos" → "Próximos Eventos"

---

## [2026-01-24] - Push Notifications e WebSocket Fix

### Adicionado
- **Push Notifications com VAPID**
  - Endpoints `/api/notifications/push/subscribe`, `/unsubscribe`, `/status`
  - Biblioteca `pywebpush` para envio real de notificações
  - Service Worker para receber notificações (`sw-push.js`)
  - Componente de configuração em Definições > Notificações
  - Integração: push enviado quando utilizador não está online via WebSocket

### Corrigido
- **Bug WebSocket URL**: Corrigida construção da URL usando API `URL()`
- Resolvido erro `ws://localhost:443/ws` em ambiente de preview

---

## [2026-01-23] - Refatorização e Correções

### Adicionado
- **Funcionalidade Impersonate**
  - Admin pode "ver como" outro utilizador
  - Banner amarelo quando em modo impersonate
  - Auditoria registada

### Alterado
- **Refatorização AdminDashboard**
  - Reduzido de 1200 para 315 linhas (~74%)
  - Componentes modulares em `/components/admin/`

### Corrigido
- Endpoint `/api/admin/workflow-statuses` no frontend
- Imports em falta no `ProcessDetails.js`
- Endpoint `/api/auth/me` para campos de impersonate

### Removido
- Rotas não utilizadas (`/cliente`, `ClientDashboard.js`, etc.)

---

## [2026-01-22] - Alertas e Notificações

### Adicionado
- **Sistema de Alertas**
  - Alerta de idade (<35 anos) para Apoio ao Estado
  - Countdown de 90 dias após pré-aprovação
  - Alerta de documentos a expirar (15 dias antes)
  - Alerta de escritura automático no calendário

- **Notificações em Tempo Real**
  - WebSocket para notificações instantâneas
  - Som de notificação (ativável/desativável)
  - Badge de contagem não lidas no ícone

### Alterado
- Novos perfis: Diretor(a) e Administrativo(a)
- Checkbox "Menor de 35 anos" no formulário público
- Layout ProcessDetails: Atividade na sidebar direita

---

## [2026-01-20] - Importação Trello

### Adicionado
- 155 processos importados do Trello
- 14 fases de workflow configuradas
- Badge "Trello" nos cartões sincronizados

---

## [2026-01] - Lançamento Inicial

### Adicionado
- Quadro Kanban visual (estilo Trello)
- Formulário público de registo
- Sistema de login com roles (Admin, CEO, Diretor, Consultor, Intermediário)
- Gestão de processos de crédito imobiliário
- Email SMTP funcional
- Links OneDrive para documentos
- Editor de workflow
- CI/CD Pipeline com GitHub Actions
- Análise de documentos com IA (GPT-4o-mini)

---

## Legenda

- **Adicionado**: Novas funcionalidades
- **Alterado**: Alterações em funcionalidades existentes
- **Corrigido**: Correções de bugs
- **Removido**: Funcionalidades removidas
- **Segurança**: Alterações relacionadas com segurança
