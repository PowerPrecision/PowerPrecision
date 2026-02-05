# CreditoIMO - Product Requirements Document

## Problema Original
Aplicação de gestão de processos de crédito habitação e transações imobiliárias que funciona como "espelho" de um quadro Trello, com sincronização bidirecional.

## Stack Técnica
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, Pydantic, Motor (MongoDB async)
- **Base de Dados**: MongoDB (DB_NAME: test_database)
- **Integrações**: Trello API & Webhooks, IMAP/SMTP (emails), OneDrive (via link partilhado)

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
**5 Fevereiro 2026**
- Corrigido bug de layout dos botões no Kanban (CSS Grid)
- Implementado botão "Abrir no OneDrive" na página de detalhes
- Limpeza de código (removido onedrive_shared.py redundante)
- Testada funcionalidade de atribuição de processos via API
