# CreditoIMO - Product Requirements Document

## Problema Original
Aplicação de gestão de processos de crédito habitação e transações imobiliárias que funciona como "espelho" de um quadro Trello, com sincronização bidirecional.

## Stack Técnica
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, Pydantic, Motor (MongoDB async)
- **Base de Dados**: MongoDB (DB_NAME: test_database)
- **Integrações**: Trello API & Webhooks, IMAP/SMTP (emails)

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

### Página de Integração Trello Melhorada (Fev 2026)
- ✅ Estatísticas de sincronização (total, do Trello, com/sem atribuição)
- ✅ Mapeamento visual de membros do Trello para utilizadores
- ✅ Avisos quando existem processos sem atribuição
- ✅ Botão "Atribuir Auto" para corrigir processos existentes
- ✅ Informação de diagnóstico detalhada (credenciais, erros)

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

### UI/UX (Jan 2026)
- ✅ Tema de cores teal/dourado (Precision/Power branding)
- ✅ Painel de emails sempre visível na página de detalhes
- ✅ Scroll corrigido no histórico de emails
- ✅ ID interno "CreditoIMO" oculto da interface

### Correções de Bugs
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
- Consultor: `carina@sistema.pt` / `test1234`
- Mediador: `pedro@sistema.pt` / `test1234`

## Arquitetura de Ficheiros Principais
```
/app/backend/
├── services/
│   ├── email_service.py     # Sincronização IMAP
│   └── trello.py            # Integração Trello
├── routes/
│   ├── processes.py         # CRUD processos, Kanban
│   ├── trello.py            # Webhooks Trello, Atribuição Auto
│   └── activities.py        # Comentários/atividades
└── models/
    └── process.py           # Modelo de dados

/app/frontend/src/
├── components/
│   ├── TrelloIntegration.js # Painel Trello melhorado
│   ├── EmailHistoryPanel.js # Painel de emails
│   └── KanbanBoard.js       # Quadro Kanban
├── pages/
│   └── ProcessDetails.js    # Detalhes do processo
└── index.css                # Variáveis de tema
```

## Integrações Ativas
- **OpenAI**: gpt-4o-mini para análise de documentos
- **Trello**: Sincronização bidirecional via API e webhooks
- **Email**: IMAP/SMTP (geral@precisioncredito.pt, geral@powerealestate.pt)

## Notas Importantes para Deployment
- Os utilizadores da aplicação devem ter o **mesmo nome** que os membros do Trello para que a atribuição automática funcione
- A sincronização pode ser feita manualmente via botão "Trello → App" ou automaticamente via webhook
- Processos existentes sem atribuição podem ser corrigidos com "Atribuir Auto"
