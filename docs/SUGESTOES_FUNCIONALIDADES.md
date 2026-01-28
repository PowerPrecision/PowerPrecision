# 🚀 SUGESTÕES DE NOVAS FUNCIONALIDADES E INTEGRAÇÕES

## Sistema CreditoIMO - Roadmap de Evolução

**Última Atualização:** Janeiro 2026

---

## 📋 Índice

1. [Funcionalidades Já Implementadas](#1-funcionalidades-já-implementadas)
2. [Integrações Prioritárias](#2-integrações-prioritárias)
3. [Funcionalidades de Comunicação](#3-funcionalidades-de-comunicação)
4. [Funcionalidades de Produtividade](#4-funcionalidades-de-produtividade)
5. [Inteligência Artificial](#5-inteligência-artificial)
6. [Portal do Cliente](#6-portal-do-cliente)
7. [Integrações Bancárias](#7-integrações-bancárias)
8. [Mobile e Notificações](#8-mobile-e-notificações)
9. [Análise e Relatórios](#9-análise-e-relatórios)
10. [Priorização e Custos](#10-priorização-e-custos)

---

## 1. Funcionalidades Já Implementadas ✅

### Sistema de Notificações em Tempo Real
**Estado: IMPLEMENTADO**

- ✅ Colecção MongoDB `notifications` com índices optimizados
- ✅ WebSocket para notificações em tempo real (`/api/ws/notifications`)
- ✅ Hook React `useWebSocket` com auto-reconnect
- ✅ Dropdown de notificações com som
- ✅ Notificação automática na mudança de fase do processo
- ✅ Tipos: novo registo, idade <35, countdown pré-aprovação, docs a expirar, mudança de estado

---

### Editor de Workflow
**Estado: IMPLEMENTADO**

- ✅ UI completa em Definições > Sistema
- ✅ CRUD de estados (criar, editar, eliminar)
- ✅ Reordenação com setas ↑↓
- ✅ Selecção de cores por estado
- ✅ 14 estados pré-configurados (Trello-like)

---

### Análise de Documentos com IA
**Estado: IMPLEMENTADO**

- ✅ Modelo: `gpt-4o-mini` (económico)
- ✅ Extracção de texto de PDF com `pypdf`
- ✅ Análise de visão apenas quando necessário
- ✅ Redimensionamento de imagens (max 1024px)
- ✅ Tipos suportados: CC, Recibo Vencimento, IRS

---

### Tarefas Agendadas (Cron Jobs)
**Estado: IMPLEMENTADO**

- ✅ Verificação diária de documentos a expirar
- ✅ Verificação de prazos próximos (24h)
- ✅ Countdown de pré-aprovação (90 dias)
- ✅ Limpeza de notificações antigas (30 dias)
- ✅ Modo daemon disponível (`--daemon`)

**Uso:**
```bash
# Executar manualmente
python -m services.scheduled_tasks

# Cron diário às 8h
0 8 * * * cd /app/backend && python -m services.scheduled_tasks
```

---

### CI/CD Pipeline
**Estado: IMPLEMENTADO**

- ✅ GitHub Actions workflow
- ✅ Testes backend (pytest + MongoDB)
- ✅ Testes frontend (Jest)
- ✅ Testes de integração
- ✅ Scan de segurança (Trivy)
- ✅ Deploy automático para main

---

### Segurança e Validação
**Estado: IMPLEMENTADO**

- ✅ Variáveis de ambiente obrigatórias (JWT_SECRET, MONGO_URL)
- ✅ Passwords em variáveis de ambiente (não hardcoded)
- ✅ Validador de NIF (9 dígitos numéricos)
- ✅ Campos legacy removidos dos modelos

---

## 2. Integrações Prioritárias

### 📁 Microsoft OneDrive
**Prioridade: ALTA** | **Estado: PARCIALMENTE IMPLEMENTADO**

A integração base existe mas precisa de:
- [ ] Upload automático de documentos por processo
- [ ] Estrutura de pastas automática por NIF
- [ ] Sincronização bidirecional
- [ ] Preview de documentos no sistema

**Estrutura Sugerida:**
```
/CreditoIMO/
├── Clientes/
│   ├── {NIF_Cliente}/
│   │   ├── Documentos Pessoais/
│   │   ├── Documentos Financeiros/
│   │   ├── Documentos Imóvel/
│   │   └── Correspondência Bancária/
```

---

### 🔗 Integração Trello Bidirecional
**Prioridade: MÉDIA** | **Estado: EM STANDBY**

Base implementada, aguarda activação:
- ✅ Autenticação com API Trello
- ✅ Leitura de quadros e listas
- [ ] Criar cartão no Trello ao criar processo
- [ ] Mover cartão ao mudar fase
- [ ] Webhook para sincronizar Trello → CreditoIMO
- [ ] Campo `trello_card_id` no modelo Process

**Credenciais configuradas:**
- API Key: `f299eb63c0b59a9938051a2e1b05bf5f`
- Board ID: `MyXVV27F`

---

### 📧 Email Transacional (SendGrid/Mailgun)
**Prioridade: ALTA**

- [ ] Templates HTML profissionais
- [ ] Tracking de abertura/cliques
- [ ] Gestão de unsubscribes
- [ ] Integração com variáveis do processo

**Templates Sugeridos:**
1. Boas-vindas ao cliente
2. Pedido de documentos
3. Atualização de estado
4. Aprovação de crédito
5. Agendamento de escritura
6. Documento a expirar (lembrete)

---

### 📱 WhatsApp Business API
**Prioridade: MÉDIA-ALTA**

- [ ] Notificações opt-in
- [ ] Templates aprovados pela Meta
- [ ] Respostas automáticas FAQ
- [ ] Envio de lembretes de documentos

**Fluxo:**
```
Cliente submete formulário → 
WhatsApp de boas-vindas →
Consultor notificado →
Agendamento de contacto
```

---

## 3. Funcionalidades de Comunicação

### 💬 Chat Interno por Processo
**Prioridade: MÉDIA**

- [ ] Mensagens em tempo real (WebSocket já implementado)
- [ ] Menções @utilizador
- [ ] Anexos de ficheiros
- [ ] Histórico pesquisável
- [ ] Notificações de nova mensagem

---

### 📝 Assinatura Digital
**Prioridade: MÉDIA**

**Opções:**
- DocuSign (internacional)
- Autenticação.gov (Portugal - Chave Móvel Digital)

**Documentos para assinatura:**
- CPCV
- Mandatos de intermediação
- Autorizações de consulta

---

## 4. Funcionalidades de Produtividade

### 📋 Templates de Documentos
**Prioridade: ALTA**

- [ ] Geração automática com dados do processo
- [ ] Export para Word/PDF
- [ ] Templates personalizáveis

**Templates Sugeridos:**
```python
# Usando python-docx
templates = [
    "proposta_bancaria.docx",
    "ficha_cliente.docx",
    "relatorio_analise.docx",
    "carta_apresentacao.docx"
]
```

---

### 🔄 Automação de Workflow
**Prioridade: MÉDIA**

Triggers automáticos:
- [ ] Fase "Documental" → Email com checklist
- [ ] Documento expira em 7 dias → Tarefa urgente
- [ ] Crédito aprovado → Notificar todos
- [ ] Semanal → Relatório de pendentes

---

### 📊 Importação em Massa (Excel/CSV)
**Prioridade: MÉDIA**

- [ ] Upload de ficheiro
- [ ] Mapeamento de colunas
- [ ] Validação prévia
- [ ] Prevenção de duplicados
- [ ] Log de importação

---

## 5. Inteligência Artificial

### 🤖 Análise Preditiva de Aprovação
**Prioridade: ALTA**

Usar dados históricos para prever:
- [ ] Probabilidade de aprovação (%)
- [ ] Fatores de risco identificados
- [ ] Banco mais adequado
- [ ] Condições estimadas

**Modelo Sugerido:**
```python
def prever_aprovacao(processo):
    features = {
        'rendimento_mensal': processo['financial_data']['renda_habitacao_atual'],
        'taxa_esforco': calcular_taxa_esforco(processo),
        'idade': calcular_idade(processo['personal_data']['birth_date']),
        'tipo_contrato': processo['financial_data']['efetivo'],
        'valor_entrada': processo['financial_data']['capital_proprio'],
        'menor_35': processo['personal_data']['menor_35_anos'],
    }
    return modelo.predict_proba(features)
```

---

### 💬 Chatbot de Atendimento
**Prioridade: MÉDIA**

- [ ] FAQ automático
- [ ] Verificação de estado do processo
- [ ] Agendamento de reuniões
- [ ] Recepção de documentos
- [ ] Handoff para consultor humano

---

## 6. Portal do Cliente

### 🌐 Área de Cliente Dedicada
**Prioridade: ALTA**

- [ ] Login com email/password ou link mágico
- [ ] Ver estado atual do processo
- [ ] Timeline de progresso visual
- [ ] Upload de documentos
- [ ] Chat com consultor
- [ ] Histórico de interações

---

### 📱 App Móvel (React Native/Flutter)
**Prioridade: MÉDIA**

- [ ] Push notifications nativas
- [ ] Scan de documentos com câmara
- [ ] Assinatura no ecrã
- [ ] Modo offline
- [ ] Biometria para login

---

## 7. Integrações Bancárias

### 🏦 Simuladores de Crédito
**Prioridade: MÉDIA**

- [ ] Cálculo de prestação em tempo real
- [ ] Comparação multi-banco
- [ ] Taxa de esforço
- [ ] Relatório de simulação PDF

**Bancos Prioritários:**
- Millennium BCP
- Caixa Geral de Depósitos
- Santander Totta
- Novo Banco
- BPI

---

### 💰 API Bancárias (Futuro)
**Prioridade: BAIXA** (requer parcerias formais)

- Submissão automática de propostas
- Consulta de pré-aprovações
- Receber decisões em tempo real

---

## 8. Mobile e Notificações

### 🔔 Push Notifications (Browser/Mobile)
**Prioridade: ALTA**

**Já Implementado:**
- ✅ WebSocket para tempo real
- ✅ Som de notificação

**A Implementar:**
- [ ] Web Push API (browser)
- [ ] Firebase Cloud Messaging (mobile)
- [ ] Service Worker para offline
- [ ] Preferências de notificação por utilizador

---

### 📍 Geolocalização para Visitas
**Prioridade: BAIXA**

- [ ] Routing optimizado
- [ ] Check-in no local
- [ ] Mapa de imóveis
- [ ] Tempo de viagem estimado

---

## 9. Análise e Relatórios

### 📈 Business Intelligence
**Prioridade: MÉDIA**

**Dashboards Sugeridos:**
- Funil de conversão por fase
- Performance por consultor/mês
- Tempo médio por fase
- Taxa de aprovação por banco
- Valor total financiado

**Ferramentas:**
- Metabase (open-source)
- PowerBI (Microsoft)
- Google Data Studio (grátis)

---

### 📊 Exportação Avançada
**Prioridade: MÉDIA**

- [ ] Excel com formatação
- [ ] PDF com gráficos
- [ ] CSV para análise
- [ ] API para integrações

---

## 10. Priorização e Custos

### 📅 Roadmap Sugerido

#### Fase 1 - Concluída ✅
1. ✅ Sistema de Notificações em Tempo Real
2. ✅ Editor de Workflow
3. ✅ Análise de Documentos com IA
4. ✅ CI/CD Pipeline
5. ✅ Tarefas Agendadas

#### Fase 2 - Próximos Passos (1-2 meses)
1. 🔄 Activar integração Trello
2. 📧 Templates de Email profissionais
3. 📋 Templates de Documentos Word/PDF
4. 🔔 Push Notifications (browser)

#### Fase 3 - Médio Prazo (2-4 meses)
5. 📱 WhatsApp Business API
6. 🌐 Portal do Cliente básico
7. 🤖 IA Preditiva de aprovação
8. 📊 Exportação avançada

#### Fase 4 - Longo Prazo (4-6 meses)
9. 📱 App Móvel
10. 💬 Chatbot IA
11. 📝 Assinatura Digital
12. 🏦 Simuladores Bancários

---

### 💰 Estimativa de Custos Mensais

| Serviço | Uso Estimado | Custo/Mês |
|---------|-------------|-----------|
| **Já Incluídos** | | |
| MongoDB Atlas | 512MB | Grátis |
| OpenAI (gpt-4o-mini) | ~1k docs | ~€5-10 |
| | | |
| **A Implementar** | | |
| SendGrid | 50k emails | ~€15 |
| WhatsApp Business | 1k conversas | ~€50 |
| Firebase Push | 10k mensagens | Grátis |
| OneDrive API | Incluído M365 | - |
| DocuSign | 50 envelopes | ~€25 |

---

### ⚠️ Considerações Técnicas

1. **RGPD:** Todas as integrações devem cumprir regulamento de proteção de dados
2. **API Keys:** Gestão segura via variáveis de ambiente (já implementado)
3. **Rate Limits:** Implementar circuit breakers para APIs externas
4. **Backups:** MongoDB com backups automáticos diários
5. **Logging:** Centralizar logs para debugging

---

### 📞 Contactos para Integrações

| Serviço | URL | Notas |
|---------|-----|-------|
| SendGrid | sendgrid.com | API key gratuita até 100 emails/dia |
| WhatsApp Business | business.whatsapp.com | Requer verificação de empresa |
| DocuSign | docusign.com | Sandbox disponível para testes |
| Autenticação.gov | autenticacao.gov.pt | Apenas para empresas portuguesas |

---

*Documento de roadmap - CreditoIMO v2.1*
*Última atualização: Janeiro 2026*
