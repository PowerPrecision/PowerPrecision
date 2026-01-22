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
3. **Consultor/Mediador** - Pode fazer tarefas de consultor E mediador
4. **Consultor** - Gere dados imobiliários, vê apenas os seus clientes atribuídos
5. **Mediador** - Gere dados de crédito, vê apenas os seus clientes atribuídos
6. **Cliente** - Preenche formulário público (sem login no sistema)

## Credenciais de Acesso
| Nome | Email | Role | Password |
|------|-------|------|----------|
| Pedro Borges | pedro@powerealestate.pt | CEO | power2026 |
| Tiago Borges | tiago@powerealestate.pt | Consultor | power2026 |
| Flávio da Silva | flavio@powerealestate.pt | Consultor | power2026 |
| Estácio Miranda | estacio@precisioncredito.pt | Mediador | power2026 |
| Fernando Andrade | fernando@precisioncredito.pt | Mediador | power2026 |
| Carina Amuedo | carina@powerealestate.pt | Consultor/Mediador | power2026 |
| Marisa Rodrigues | marisa@powerealestate.pt | Consultor/Mediador | power2026 |
| Admin | admin@sistema.pt | Admin | admin2026 |

## What's Been Implemented

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
- [ ] Preencher documentação (GUIA_UTILIZADOR.md, APRESENTACAO.md)
- [ ] Comentar código fonte
- [ ] CI/CD Pipeline para testes automatizados
- [ ] Testar análise AI com documentos reais
