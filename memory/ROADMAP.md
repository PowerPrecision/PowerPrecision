# CreditoIMO - Roadmap

Plano de desenvolvimento priorizado do sistema CreditoIMO.

---

## ✅ Concluído

### Sistema Base
- [x] Quadro Kanban visual (estilo Trello)
- [x] Sistema de login com roles
- [x] Gestão de processos de crédito
- [x] Email SMTP funcional
- [x] Links OneDrive para documentos
- [x] Editor de workflow
- [x] CI/CD Pipeline

### Notificações
- [x] WebSocket para tempo real
- [x] Push Notifications com VAPID
- [x] Som de notificação configurável
- [x] Alertas de documentos a expirar
- [x] Countdown de pré-aprovação (90 dias)

### Tarefas
- [x] Sistema de tarefas completo (CRUD)
- [x] Separador "Tarefas" no Admin Dashboard
- [x] Painel de tarefas na ficha do cliente
- [x] Notificações quando tarefa atribuída

### Alertas Automáticos
- [x] Clientes em espera 15+ dias
- [x] Lembrete mensal (1º dia do mês)
- [x] Email automático ao cliente

### UI/UX
- [x] Calendário: layout com eventos à direita
- [x] "Próximos Prazos" → "Próximos Eventos"
- [x] Refatorização AdminDashboard (componentes modulares)
- [x] Funcionalidade Impersonate

---

## 🟡 Prioridade Média (Próximas)

### Melhorias UI
- [x] Pesquisa com resultados em lista no Quadro Geral
- [x] Resumo do processo no topo da ficha do cliente
- [x] Links clicáveis no dashboard para filtrar processos
- [ ] CEO ver calendário de todos os utilizadores
  - Clique em "Desistências" → Lista de processos desistidos
  - Clique em "Prazos Pendentes" → Lista com motivo

---

## ⏸️ Em Stand-by

### Sistema de Documentos
- [ ] Alerta CPCV/Escritura com verificação de documentos
- [ ] Lista de documentos necessários para cada fase
- [ ] Verificar validade de documentos na data da escritura
- [ ] Conversão automática para PDF
- [ ] Documentos com mais de 6 meses = inválidos

**Bloqueio**: Aguarda lista de documentos por fase (CPCV vs Escritura)

### Integrações
- [ ] Integração bidirecional com Trello
- [ ] Histórico de emails na ficha do cliente
- [ ] Testar análise AI com documentos reais

### Faturação
- [ ] Preparar sistema para opção de faturação

---

## 📋 Ideias Futuras

- Dashboard de KPIs e métricas de conversão
- Relatórios PDF
- App mobile ou PWA
- Integração com bancos (API)
- Assinatura digital de documentos
- Portal de cliente (auto-serviço)
- Chat interno entre utilizadores

---

## Notas

- **Stand-by** significa que a funcionalidade está planeada mas aguarda input do utilizador ou está pausada por decisão de negócio.
- Prioridades podem ser alteradas conforme necessidades do negócio.
- Última atualização: 2026-01-25
