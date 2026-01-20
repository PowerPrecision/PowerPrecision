# CreditoIMO - Sistema de Registo de Clientes

## Problem Statement
Sistema de registo de clientes que podem precisar de crédito e de ajuda imobiliária ou as duas coisas. O cliente preenche os dados que depois podem ser alterados e adicionados campos pelo consultor ou pelo mediador. Alguns campos só podem ser preenchidos depois do processo ter autorização bancária. O processo tem de ter um calendário associado para saber os prazos.

## User Personas
1. **Cliente** - Cria processos, preenche dados pessoais e financeiros, adiciona comentários
2. **Consultor** - Gere dados imobiliários, altera estados, adiciona prazos
3. **Mediador** - Gere dados de crédito (após autorização bancária), altera estados
4. **Admin** - Gestão de utilizadores, gestão de fluxos de processos, configurações

## Core Requirements (Static)
- Autenticação JWT com 4 roles
- Processos com fases configuráveis pelo admin
- Dados pessoais e financeiros editáveis por cliente
- Dados imobiliários editáveis apenas por consultor
- Dados de crédito editáveis apenas por mediador (após autorização bancária)
- Calendário de prazos por processo
- Histórico de alterações
- Sistema de comentários/atividade
- Integração OneDrive para documentos
- Notificações por email

## Architecture
- **Backend**: FastAPI + MongoDB + JWT Auth
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Database**: MongoDB com collections: users, processes, deadlines, activities, history, workflow_statuses, email_logs
- **Integração**: OneDrive via Microsoft Graph API (preparado)

## What's Been Implemented

### Fase 1 (2026-01-20)
- ✅ Sistema de autenticação completo (login/registo/JWT)
- ✅ 4 dashboards por role (Cliente, Consultor, Mediador, Admin)
- ✅ Criação de processos com wizard de 3 passos
- ✅ Formulários de dados pessoais, financeiros, imobiliários e crédito
- ✅ Sistema de prazos com calendário visual
- ✅ Gestão de utilizadores pelo admin
- ✅ Controle de acesso por role
- ✅ Notificações por email (SIMULADAS/logs)

### Fase 2 (2026-01-20)
- ✅ Histórico de alterações de processos (todas as alterações são registadas)
- ✅ Sistema de comentários/atividade por processo
- ✅ Gestão de estados de fluxo pelo admin (adicionar/editar/eliminar fases)
- ✅ Integração OneDrive preparada (requer configuração Azure AD)
- ✅ Clientes de teste criados automaticamente
- ✅ Campo "Pasta OneDrive" nos utilizadores

## Integração OneDrive
- **Estado**: Preparado, aguarda configuração
- **Estrutura**: /Os meus ficheiros/Documentação Clientes/[NomeCliente]
- **Variáveis de ambiente necessárias**:
  - ONEDRIVE_TENANT_ID
  - ONEDRIVE_CLIENT_ID
  - ONEDRIVE_CLIENT_SECRET
  - ONEDRIVE_BASE_PATH (default: "Documentação Clientes")

## Prioritized Backlog

### P0 (Crítico) - Done
- [x] Auth system
- [x] Process CRUD
- [x] Role-based access
- [x] Deadline management
- [x] Histórico de alterações
- [x] Comentários/atividade
- [x] Gestão de fluxos pelo admin

### P1 (Importante)
- [ ] Configurar OneDrive (requer credenciais Azure AD)
- [ ] Notificações por email reais (SendGrid/Resend)
- [ ] Dashboard com gráficos de estatísticas

### P2 (Nice to Have)
- [ ] Notificações push
- [ ] Exportar processos para PDF
- [ ] Relatórios mensais

## Credentials (Dev)
- **Admin**: admin@sistema.pt / admin123
- **Consultor**: consultor@sistema.pt / consultor123
- **Mediador**: mediador@sistema.pt / mediador123
- **Clientes de teste**: 
  - joao.silva@email.pt / cliente123
  - maria.santos@email.pt / cliente123
  - pedro.costa@email.pt / cliente123

## Next Tasks
1. **Configurar OneDrive**: 
   - Registar aplicação no Azure Portal (portal.azure.com)
   - Obter Tenant ID, Client ID, Client Secret
   - Adicionar às variáveis de ambiente
2. Integrar serviço de email real

## MOCKED APIs
- **Email**: Notificações são registadas em log e na coleção email_logs
- **OneDrive**: Preparado mas não configurado (mostra instruções no painel admin)
