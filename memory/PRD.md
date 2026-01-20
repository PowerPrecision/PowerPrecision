# CreditoIMO - Sistema de Registo de Clientes

## Problem Statement
Sistema de registo de clientes que podem precisar de crédito e de ajuda imobiliária ou as duas coisas. O cliente preenche um formulário público inicial (sem login). O mediador e o consultor gerem depois o cliente.

## User Personas
1. **Cliente** - Preenche formulário público (sem login), recebe acompanhamento
2. **Consultor** - Gere dados imobiliários, altera estados, adiciona prazos
3. **Mediador** - Gere dados de crédito (após autorização bancária), altera estados
4. **Admin** - Gestão de utilizadores, gestão de fluxos de processos, configurações

## Core Requirements
- Formulário público para clientes (sem autenticação)
- Autenticação JWT apenas para staff (consultor, mediador, admin)
- Processos com fases configuráveis pelo admin
- Histórico de alterações
- Sistema de comentários/atividade
- Integração OneDrive para documentos (preparado)
- Notificações por email (simuladas)

## Architecture
- **Backend**: FastAPI + MongoDB + JWT Auth
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Database**: MongoDB

### Backend Structure (Refatorado 2026-01-20)
```
/app/backend/
├── server.py          # Main app (~130 linhas)
├── config.py          # Configurações
├── database.py        # Conexão MongoDB
├── models/            # Pydantic models
│   ├── auth.py        # UserRole, UserResponse, etc
│   ├── process.py     # ProcessCreate, ProcessResponse, etc
│   ├── deadline.py    # DeadlineCreate, DeadlineResponse
│   ├── workflow.py    # WorkflowStatusCreate, etc
│   ├── activity.py    # ActivityCreate, HistoryResponse
│   └── onedrive.py    # OneDriveFile
├── routes/            # API endpoints
│   ├── auth.py        # /api/auth/*
│   ├── public.py      # /api/public/*
│   ├── processes.py   # /api/processes/*
│   ├── admin.py       # /api/users/*, /api/workflow-statuses/*
│   ├── deadlines.py   # /api/deadlines/*
│   ├── activities.py  # /api/activities/*, /api/history
│   ├── onedrive.py    # /api/onedrive/*
│   └── stats.py       # /api/stats, /api/health
└── services/          # Business logic
    ├── auth.py        # JWT, password hashing
    ├── email.py       # Email notifications
    ├── history.py     # Change logging
    └── onedrive.py    # OneDrive integration
```

## What's Been Implemented

### Fase 1 (2026-01-20)
- ✅ Sistema de autenticação para staff
- ✅ 4 dashboards por role
- ✅ Sistema de prazos com calendário

### Fase 2 (2026-01-20)
- ✅ Histórico de alterações
- ✅ Sistema de comentários/atividade
- ✅ Gestão de estados de fluxo pelo admin
- ✅ Integração OneDrive preparada

### Fase 3 (2026-01-20)
- ✅ Formulário público para clientes (sem login)
- ✅ Processos de simulação criados
- ✅ Fluxo completo: cliente regista-se → consultor/mediador gerem

### Fase 4 - Refatoração (2026-01-20)
- ✅ Backend refatorado de 1340 linhas para estrutura modular
- ✅ Separação em models/, routes/, services/
- ✅ server.py simplificado (~130 linhas)
- ✅ Código mais manutenível e escalável
- ✅ Suite de testes pytest criada (37 testes API)
- ✅ Cobertura API: auth, processos, admin, activities, public
- ✅ Suite de testes E2E Playwright (17 testes)
- ✅ Cobertura E2E: formulário público, login, dashboards, navegação, responsividade

### Fase 5 - Novo Formulário Completo (2026-01-20)
- ✅ Formulário baseado na ficha de cliente PDF do Microsoft Forms
- ✅ 6 passos: Dados Pessoais > 2º Titular > Imóvel > Situação Financeira > Créditos/Capital > Confirmação
- ✅ Campos: NIF, CC/Passaporte, Naturalidade, Estado Civil, Tipo Compra
- ✅ Imóvel: Tipo, Quartos, Localização, Características obrigatórias
- ✅ Financeiro: Portal Finanças, Chave Móvel, Salário, Bancos com créditos, Capital próprio
- ✅ Suporte para 2º titular (compra conjunta)
- ✅ Backend atualizado com novos modelos de dados
- ✅ Mensagens de ajuda em todos os campos (ícone info com descrição)

### Fase 6 - Dashboard Admin Avançado (2026-01-20)
- ✅ Nova tab "Visão Geral" com filtros por consultor/mediador
- ✅ Nova tab "Calendário" com calendário visual e filtros
- ✅ Visualização de prazos por data com informação de cliente/consultor/mediador
- ✅ API /api/deadlines/calendar para obter todos os prazos com filtros
- ✅ Estatísticas: Total Processos, Utilizadores, Prazos Pendentes, Estados
- ✅ Tabs: Visão Geral, Calendário, Utilizadores, Fluxo, Configurações
- ✅ Branding atualizado: Power Real Estate & Precision

## Processos de Simulação
| Cliente | Tipo | Estado |
|---------|------|--------|
| António Ferreira | Crédito | Pedido Inicial |
| Carla Rodrigues | Imobiliária | Pedido Inicial |
| Rui Mendes | Crédito + Imobiliária | Autorização Bancária |
| Sofia Almeida | Crédito | Pedido Inicial |

## Integrações Pendentes
- [ ] OneDrive (requer credenciais Azure AD)
- [ ] HCPRO (dados imobiliários) - para futuro
- [ ] CRMCREDITO (dados de crédito) - para futuro

## Credentials (Dev)
- **Admin**: admin@sistema.pt / admin123
- **Consultor**: consultor@sistema.pt / consultor123
- **Mediador**: mediador@sistema.pt / mediador123

## URLs
- **Formulário Público**: / ou /registo
- **Login Staff**: /login

## MOCKED APIs
- **Email**: Notificações simuladas (logs)
- **OneDrive**: Preparado, não configurado
