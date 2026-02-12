# CreditoIMO - Product Requirements Document

## Problema Original
Aplicação de gestão de processos de crédito habitação e transações imobiliárias que funciona como "espelho" de um quadro Trello, com sincronização bidirecional.

## Stack Técnica
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, Pydantic, Motor (MongoDB async)
- **Base de Dados**: MongoDB Atlas (Cluster: cluster0.c8livu.mongodb.net)
  - **Desenvolvimento/Testes**: `powerprecision_dev`
  - **Produção**: `powerprecision`
- **Integrações**: Trello API & Webhooks, IMAP/SMTP (emails), OneDrive (via link partilhado), Gemini 2.0 Flash (scraping), AWS S3 (documentos)

## Última Actualização - 12 Fevereiro 2026 (Sessão 9)

### ✅ Funcionalidades Implementadas (Sessão 9)

#### 1. Normalização de Nomes de Ficheiros no Upload S3
**Funcionalidade:** Sanitização automática de nomes de ficheiros durante o upload
- Remove acentos e caracteres especiais
- Formato: `{Categoria}_{Data}_{NomeOriginalNormalizado}.{ext}`
- Limita tamanho a 50 caracteres
- **Ficheiro**: `/app/backend/routes/documents.py`

#### 2. Conversão Automática de Imagens para PDF
**Funcionalidade:** Converte imagens (JPG, PNG, TIFF) para PDF automaticamente durante o upload
- Usa biblioteca `img2pdf`
- Retorna informação sobre se foi convertido: `converted_to_pdf: true/false`
- **Ficheiros**:
  - `/app/backend/services/document_processor.py` (já existia)
  - `/app/backend/routes/documents.py` (integração)

#### 3. Validação de Campos Obrigatórios para Minutas
**Funcionalidade:** Antes de gerar uma minuta, verifica se os dados necessários estão preenchidos
- Retorna erro 400 com lista de campos em falta se dados incompletos
- Campos obrigatórios variam por tipo de template
- **CPCV requer**: Nome do Comprador, NIF do Comprador, Morada do Imóvel, Artigo Matricial
- **UI mostra alerta visual** com lista de campos a preencher
- **Ficheiros**:
  - `/app/backend/services/template_generator.py` - Função `validate_template_requirements()`
  - `/app/backend/routes/templates.py` - Endpoints retornam 400 com detalhes
  - `/app/frontend/src/components/TemplatesPanel.js` - Alerta visual com campos em falta

#### 4. Botões Webmail no Painel de Emails
**Funcionalidade:** Adicionados botões para abrir webmail directamente no painel de Histórico de Emails
- Botões "Precision" e "Power" com ícone de link externo
- Mesmos URLs do painel de Templates
- **Ficheiro**: `/app/frontend/src/components/EmailHistoryPanel.js`

---

### ✅ Parte 2 - Automações Avançadas (IMPLEMENTADAS - Sessão 8)

#### 5. Templates e Minutas com Download
**Funcionalidades:**
- Geração automática de CPCV (Contrato Promessa Compra e Venda)
- Geração de email de Apelação de Avaliação ("Botão de Pânico")
- Geração de Lembrete de Escritura
- Geração de Pedido de Documentos

**Fluxo de Utilização:**
1. Utilizador clica no botão de pré-visualização ou download
2. Template é gerado com dados do processo preenchidos
3. Utilizador pode copiar o texto ou descarregar como ficheiro .txt
4. Utilizador abre o webmail (Precision ou Power)
5. Cola o texto no corpo do email

**Ficheiros Criados:**
- `/app/backend/services/template_generator.py` - Gerador de templates
- `/app/backend/routes/templates.py` - Endpoints da API
- `/app/frontend/src/components/TemplatesPanel.js` - Componente React

**API Endpoints:**
- `GET /api/templates/webmail-urls` - URLs dos webmails
- `GET /api/templates/document-types` - Lista de tipos de documentos
- `GET /api/templates/process/{id}/cpcv` - Template CPCV
- `GET /api/templates/process/{id}/cpcv/download` - Download CPCV
- `GET /api/templates/process/{id}/valuation-appeal` - Apelação de Avaliação
- `GET /api/templates/process/{id}/deed-reminder` - Lembrete de Escritura
- `GET /api/templates/process/{id}/document-checklist` - Checklist de documentos

#### 6. Webmail Integration
**URLs Configurados:**
- Precision: `http://webmail.precisioncredito.pt/`
- Power: `https://webmail2.hcpro.pt/Mondo/lang/sys/login.aspx`

**Nota:** A aplicação NÃO envia emails automaticamente. O utilizador faz download/copia a minuta e cola manualmente no webmail.

---

### ✅ Optimizações de Segurança e Performance (IMPLEMENTADAS)

#### Parte 3 - Optimizações Técnicas

**8. Índices de BD para Performance**
- Criado ficheiro `/app/backend/services/db_indexes.py`
- Índices criados automaticamente no startup da app
- Colecções indexadas: `processes`, `users`, `system_error_logs`, `properties`, `tasks`
- TTL index de 90 dias para logs (limpeza automática)

**11. Validação JWT Secret Robusta**
- Verificação de comprimento mínimo (32 chars)
- Detecção de valores de exemplo inseguros
- Verificação de complexidade (entropia)
- Em DEV: apenas aviso | Em PROD: bloqueio fatal
- Ficheiro: `/app/backend/config.py`

**12. Validação Checksum NIF Português**
- Algoritmo completo de validação do dígito de controlo
- Validação de prefixos válidos (1,2,3,5,6,7,8,9)
- Opção para permitir/bloquear NIFs de empresa (5xxxxx)
- Ficheiro: `/app/backend/models/process.py`

**14. Rate Limiting Configurável**
- Limites por tipo de endpoint: auth, read, write, upload, export, ai
- Configurável via variáveis de ambiente
- Headers X-RateLimit-* nas respostas
- Ficheiro: `/app/backend/middleware/rate_limit.py`

---

#### Parte 1 - Lógica de Negócio

**1. ServiceTypeEnum**
- Novo enum: `CREDITO_APENAS`, `IMOBILIARIO_APENAS`, `COMPLETO`
- Ficheiro: `/app/backend/models/process.py`

**2. Campos de Avaliação Bancária**
- Novos campos em `CreditData`: `valuation_value`, `valuation_date`, `valuation_bank`, `valuation_notes`
- Ficheiro: `/app/backend/models/process.py`

**3. Pastas S3 com Múltiplos Titulares**
- Formato: `clientes/{id}_{nome1}_e_{nome2}/`
- Aplicado apenas a NOVOS processos
- Ficheiro: `/app/backend/services/s3_storage.py`

**4. Alerta Automático de Avaliação Bancária**
- Novo tipo: `VALUATION_BELOW_PURCHASE`
- Detecta quando avaliação < valor de compra
- Calcula diferença e percentagem
- Envia notificações para consultores e admins
- Inclui recomendações de acção
- Ficheiro: `/app/backend/services/alerts.py`

---

### ✅ Correcções Anteriores (Sessão 7)

**Bug Fix: Atribuições - Dropdowns Vazios**
- Problema: Dropdowns de Consultor e Mediador apareciam vazios
- Solução: Função `openAssignDialog` convertida para async com await
- Ficheiro: `/app/frontend/src/pages/ProcessDetails.js`

**Integração HCPro**
- Upload de Excel para criar imóveis
- Botão de login HCPro no formulário de novo imóvel
- URL: https://crmhcpro.pt/login

**Sistema de Logs Corrigido**
- Logs de importação Excel agora aparecem na página de Logs do Sistema
- Colecção: `system_error_logs` (centralizada)

---

#### 2. Botão Login HCPro no Formulário de Novo Imóvel
- **Localização**: Topo do formulário "Novo Imóvel"
- **URL**: https://crmhcpro.pt/login
- **Comportamento**: Abre numa nova janela do browser
- **UI**: Secção destacada em azul com ícone de link externo

**Ficheiros Alterados**:
- `/app/frontend/src/pages/PropertiesPage.jsx`:
  - Adicionada constante `HCPRO_URL`
  - Adicionado ícone `ExternalLink` aos imports
  - Adicionada secção "Integração HCPro" no `PropertyForm`

**Teste Realizado**:
- ✅ Importação Excel: 2 imóveis importados com sucesso
- ✅ Botão HCPro: Visível e funcional no formulário
- ✅ Referências automáticas: IMO-004, IMO-005 criados

---

## Última Actualização - 11 Fevereiro 2026 (Sessão 6)

### ✅ Implementações Completas (11 Fevereiro 2026 - Noite)

#### 1. S3 File Manager - Gestão de Documentos AWS S3
- **Componente Frontend**: `/app/frontend/src/components/S3FileManager.js`
- **Serviço Backend**: `/app/backend/services/s3_storage.py`
- **Rotas API**: `/app/backend/routes/documents.py`
- **Funcionalidades**:
  - Upload de ficheiros organizado por categorias (Pessoais, Financeiros, Imóvel, Bancários, Outros)
  - Download com URLs temporários (presigned URLs)
  - Eliminação de ficheiros
  - Criação automática de estrutura de pastas
  - Barra de progresso para uploads
  - Interface com tabs por categoria
- **Configuração AWS** (em `/app/backend/.env`):
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_BUCKET_NAME=powerprecision-docs-storage`
  - `AWS_REGION=eu-north-1`

#### 2. Agente de Melhoria com IA
- **Serviço Backend**: `/app/backend/services/ai_improvement_agent.py`
- **Rotas API**: `/app/backend/routes/ai_agent.py`
- **Página Frontend**: `/app/frontend/src/pages/AIInsightsPage.js`
- **Rota**: `/ai-insights` (apenas admin e CEO)
- **Funcionalidades**:
  - Análise preditiva de todos os processos activos
  - Estatísticas: total analisado, parados, tempo médio
  - Distribuição por estado e consultor
  - Sistema de alertas com prioridades (high, medium, low)
  - Sugestões automáticas baseadas em regras
  - Integração com LLM para insights personalizados
  - Análise de processo individual
- **Endpoints**:
  - `GET /api/ai-agent/analyze` - Análise completa
  - `GET /api/ai-agent/analyze/{process_id}` - Análise de processo
  - `GET /api/ai-agent/suggestions` - Apenas sugestões
  - `GET /api/ai-agent/alerts` - Alertas filtráveis
  - `GET /api/ai-agent/stats` - Estatísticas

### Análise do ficheiro `ideias CreditoIMO.txt`

| Funcionalidade | Estado |
|---------------|--------|
| 1. Página Imóveis + Scraping | ✅ Implementado |
| 2. Deep Scraping (nome agente) | ✅ Implementado |
| 3. Painel Imobiliário (dados comercial) | ✅ Implementado |
| 4. Gestão de Leads/Kanban | ✅ Implementado |
| 5. Checklist Docs (agora S3) | ✅ Implementado |
| 6. Minutas/Templates | ✅ Implementado |
| 7. Entidades Cliente + Imóvel | ✅ Implementado |
| 8. Dashboard/Estatísticas | ✅ Implementado |
| Agente IA - Nível 1 (Descritivo) | ✅ Implementado |
| Agente IA - Nível 2 (Preditivo) | ✅ Implementado |
| Agente IA - Nível 3 (Prescritivo) | ✅ Implementado |
| Integração HCPRO | ❌ Não implementado (requer documentação externa) |

## Última Actualização - 11 Fevereiro 2026 (Sessão 5)

### ✅ Implementação Completa do Ponto 2 (11 Fevereiro 2026 - Noite)

#### Novas Funcionalidades Implementadas:

1. **c) Deep Link Melhorado - Extracção Nome do Agente**
   - Scraper agora extrai o nome do consultor/agente a partir do link adicional
   - Novas funções: `_extract_agent_name()`, `_extract_agency_name()`
   - Procura em selectores CSS típicos e padrões de texto
   - Ficheiro: `/app/backend/services/scraper.py`

2. **d) UI de Gestão de Backups**
   - Nova página `/admin/backups` (apenas admin)
   - Interface para criar backups manualmente
   - Visualização de estatísticas e histórico
   - Verificação de integridade dos backups
   - Ficheiros: `/app/frontend/src/pages/BackupsPage.js`, `/app/backend/routes/backup.py`

3. **e) Mensagens Amigáveis no Scraper**
   - Quando o scraping falha, retorna mensagem user-friendly em português
   - Códigos de erro: `blocked`, `timeout`, `not_found`, `quota_exceeded`, `parse_error`, `ssl_error`
   - Flag `suggest_manual` para indicar quando inserir dados manualmente
   - Flag `can_retry` para indicar se vale a pena tentar novamente
   - Ficheiro: `/app/backend/routes/scraper.py`

4. **f) Suporte a Proxies no Scraper**
   - Configurável via variável de ambiente `SCRAPER_PROXIES`
   - Formato: lista separada por vírgulas (ex: `http://host1:port,http://host2:port`)
   - Rotação round-robin automática entre proxies
   - Fallback quando proxy é bloqueada
   - Ficheiro: `/app/backend/services/scraper.py`

5. **g) Limpeza Automática de Ficheiros Temporários**
   - Nova tarefa `cleanup_temp_files()` nas tarefas agendadas
   - Limpa ficheiros com mais de 24 horas em `/tmp/creditoimo_*`
   - Nova tarefa `cleanup_scraper_cache()` para cache expirado
   - Ficheiro: `/app/backend/services/scheduled_tasks.py`

6. **l) Secção Minutas**
   - Nova página `/minutas` (disponível para todos os staff)
   - CRUD completo para minutas/templates de documentos
   - Categorias: Contratos, Procurações, Declarações, Cartas, Outros
   - Funcionalidades: copiar, descarregar, pesquisar, filtrar por categoria, tags
   - Suporte a placeholders (ex: `[NOME_CLIENTE]`, `[DATA]`)
   - Ficheiros: `/app/frontend/src/pages/MinutasPage.js`, `/app/backend/routes/minutas.py`

#### Menu Lateral Actualizado:
- **Admin**: Vê "Minutas" e "Backups" no menu
- **Staff**: Vê "Minutas" no menu
- **Intermediários/Mediadores**: Não vêem "Imóveis" nem "Todos os Processos"

---

### ✅ Correcções Bug Batch (11 Fevereiro 2026 - Tarde)

1. **Bug h - Dados Pessoais Não Guardados (CORRIGIDO)**
   - Adicionados novos campos ao modelo `PersonalData`: `data_nascimento`, `data_validade_cc`, `sexo`, `altura`, `nome_pai`, `nome_mae`
   - Campos são agora correctamente guardados via PUT /api/processes/{id}
   - Ficheiro: `/app/backend/models/process.py`

2. **Bug i - Consultores Redirecionados para Login (CORRIGIDO)**
   - Função `can_view_process()` actualizada para verificar `created_by` tanto por ID como por email
   - Adicionado suporte para role `INTERMEDIARIO` na verificação de permissões
   - Ficheiro: `/app/backend/routes/processes.py`

3. **Bug j - "Os Meus Clientes" Mostra Clientes Errados (CORRIGIDO)**
   - Endpoint `/api/processes/my-clients` agora suporta `MEDIADOR` e `INTERMEDIARIO`
   - Filtra correctamente por `assigned_consultor_id` ou `assigned_mediador_id` dependendo do papel
   - API `/api/clients` corrigida para filtrar por campos correctos (antes usava `assigned_to` genérico)
   - Ficheiros: `/app/backend/routes/processes.py`, `/app/backend/routes/clients.py`

4. **Bug k - Menu Lateral para Intermediários (CORRIGIDO)**
   - Intermediários e Mediadores agora não vêem "Imóveis" nem "Todos os Processos" no menu
   - Menu "Os Meus Clientes" adicionado para intermediários e mediadores
   - Ficheiro: `/app/frontend/src/layouts/DashboardLayout.js`

### ✅ Correcções e Melhorias Anteriores

1. **UI Kanban - Visibilidade de Nomes de Clientes (P0)**
   - Nomes de clientes agora são **totalmente visíveis** mesmo quando longos
   - Layout reestruturado: Número do processo em cima, nome do cliente em destaque abaixo
   - Texto usa `break-words` e `overflow-wrap: anywhere` para evitar truncamento
   - Fonte aumentada para `text-sm` com `font-semibold` para melhor legibilidade
   - Consultor mostrado em linha separada com ícone de utilizador

2. **Hybrid Scraper com Deep Link (P0)**
   - Implementada lógica "Deep Link" para encontrar contactos de agentes
   - Scraper agora segue links externos para sites de agências (Remax, ERA, Century21, etc.)
   - Extracção de contactos via regex: telefones (+351, 9XX, 2XX) e emails
   - Fallback gracioso quando quota Gemini está excedida
   - Novos campos extraídos: `agente_nome`, `agente_telefone`, `agente_email`, `agencia_nome`
   - Tratamento de erro `quota_exceeded` - scraper continua apenas com BeautifulSoup

3. **Limpeza de Dados de Teste (P2)**
   - Script `cleanup_test_data.py` criado para eliminar dados de teste
   - **33 registos eliminados**: 3 utilizadores de teste + 30 processos de teste
   - Base de dados limpa: apenas dados reais de produção permanecem
   - Script suporta modo dry-run para pré-visualização

4. **Configuração Dinâmica de IA (P1) - NOVO**
   - Admin pode agora escolher qual modelo usar para cada tarefa via `/api/admin/ai-config`
   - Modelos disponíveis: `gemini-2.0-flash`, `gpt-4o-mini`, `gpt-4o`
   - Tarefas configuráveis: scraping, análise de documentos, relatório semanal, análise de erros
   - Scraper e serviços de IA lêem configuração dinamicamente da DB

5. **Sistema de Cache para Scraping - NOVO**
   - Cache local guarda resultados de scraping por 7 dias
   - Evita chamadas repetidas à API Gemini/OpenAI
   - Novos endpoints:
     - `GET /api/scraper/cache/stats` - estatísticas do cache
     - `DELETE /api/scraper/cache/clear` - limpar cache
     - `POST /api/scraper/cache/refresh` - forçar refresh
   - Parâmetro `use_cache` no endpoint `/api/scraper/single`

6. **UI de Configuração de IA - NOVO**
   - Nova página `/configuracoes/ia` com 3 tabs:
     - **Configuração de Tarefas**: Mostra todas as tarefas e permite alterar o modelo de cada uma
     - **Modelos de IA**: CRUD completo para adicionar/editar/remover modelos
     - **Cache & Notificações**: Estatísticas de cache com barra de progresso e configurações de alertas
   - Botões "Nova Tarefa" e "Novo Modelo" para adicionar via UI
   - Modelos e tarefas são agora guardados na DB (não hardcoded)
   - Notificações automáticas quando cache atinge limite configurado

7. **Sistema de Notificações de Cache - NOVO**
   - Configurações: Limite do cache (default: 1000) e % para alertar (default: 80%)
   - Barra de progresso visual mostra utilização do cache
   - Alerta amarelo aparece automaticamente quando limite é atingido
   - Endpoints: `GET/PUT /api/admin/cache-settings`

8. **Log de Uso de IA (Tracking de Custos) - NOVO**
   - Novo serviço `ai_usage_tracker.py` regista cada chamada à IA
   - Métricas: chamadas, tokens (input/output), custo estimado, tempo de resposta, taxa de sucesso
   - Resumos diários guardados na colecção `ai_usage_summary`
   - Endpoints:
     - `GET /api/admin/ai-usage/summary` - Resumo geral
     - `GET /api/admin/ai-usage/by-task` - Agregado por tarefa
     - `GET /api/admin/ai-usage/by-model` - Agregado por modelo
     - `GET /api/admin/ai-usage/trend` - Tendência diária
   - Nova tab "Uso & Custos" na página de configuração de IA
   - Filtro por período: Hoje, Última Semana, Este Mês, Tudo
   - Gráfico de barras para tendência diária

9. **Correcção de Segurança Bandit - CORRIGIDO**
   - Substituído MD5 por SHA-256 no hash de URLs do cache
   - **0 problemas de alta severidade** no Bandit

10. **Correcções Técnicas**
   - Instalado `libmagic1` para validação de ficheiros
   - Instalado `h2` para suporte HTTP/2 no scraper
   - Nova chave Gemini API configurada no `.env`

11. **Sistema de Controlo de Notificações - NOVO**
   - Admin pode configurar preferências de email/notificação por utilizador
   - Tipos de notificação configuráveis:
     - Emails: novo processo, mudança status, documento, tarefa, prazos, urgentes, resumo diário, relatório semanal
     - In-App: novo processo, mudança status, documento, tarefa, comentários
   - **Utilizadores de Teste**: Podem ser marcados para não receber emails
   - Acções em massa: marcar/desmarcar múltiplos utilizadores como teste
   - Nova página: `/configuracoes/notificacoes`
   - Endpoints:
     - `GET /api/admin/notification-preferences` - Lista todos
     - `GET/PUT /api/admin/notification-preferences/{user_id}` - Individual
     - `POST /api/admin/notification-preferences/bulk-update` - Em massa

12. **Correcção de Validação de Datas - NOVO**
   - Datas em formato português ("19 de outubro de 1949") são convertidas para ISO
   - Erros de validação agora são mostrados correctamente (não causam página em branco)

13. **Filtros na Página de Clientes - NOVO**
   - Filtros: Todos | Com Processos | Sem Processos
   - Ordenação: Mais Recentes | Mais Antigos | Nome (A-Z/Z-A) | Processos
   - Cabeçalhos da tabela clicáveis para ordenar

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

### Importação de Comentários do Trello (Fev 2026)
- ✅ Endpoint `POST /api/trello/sync/comments` para importar comentários
- ✅ Botão "Comentários" na página de Integração Trello
- ✅ Comentários aparecem na secção "Atividade" de cada processo
- ✅ Identificados com ícone 📋 e badge "trello"
- ✅ Importação idempotente (não duplica ao re-executar)

### Análise de Documentos com IA (Fev 2026)
- ✅ Botão "✨ Analisar com IA" na página de detalhes do processo
- ✅ Upload de ficheiros (PDF, JPG, PNG, WebP)
- ✅ Análise via URL/link do OneDrive
- ✅ Suporta: CC, Recibo Vencimento, IRS, Contrato Trabalho, Caderneta Predial
- ✅ Preenche automaticamente os campos da ficha do cliente
- ✅ Usa GPT-4o-mini via Emergent LLM Key

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
**11 Fevereiro 2026 - Sessão 3**
- ✅ **P1 Completo - Sistema de Notificações com Preferências**:
  - Novo serviço `services/notification_service.py` que verifica preferências antes de enviar emails
  - Função `send_notification_with_preference_check()` substitui chamadas directas de email
  - Integrado em: `routes/processes.py`, `routes/deadlines.py`, `services/alerts.py`
  - Tipos de notificação suportados: new_process, status_change, document_upload, task_assigned, deadline_reminder
  - Admin pode configurar preferências via `/api/admin/notification-preferences/{user_id}`
  - Utilizadores marcados como `is_test_user` não recebem emails
- ✅ **Melhoria - Mensagens de Erro Claras por Campo**:
  - Novo utilitário `frontend/src/utils/errorFormatter.js` para traduzir erros Pydantic
  - Mapeamento de campos para nomes em português (client_email → "Email do Cliente")
  - Tradução de mensagens comuns (e.g., "Input should be a valid number" → "deve ser um número")
  - Erros mostram lista de campos com problema em vez de mensagem genérica
  - Implementado em `ProcessDetails.js` e `LeadsKanban.js`
- ✅ **Bug Fix - NIF aceita números**:
  - Validators em `PersonalData` e `Titular2Data` convertem int/float para string antes de validar
  - Corrige erro quando frontend envia NIF como número em vez de string

**11 Fevereiro 2026 - Sessão 2**
- ✅ **Bug Fix - Validação Email/Telefone (P0)**: Corrigido erro "Input should be a valid number" ao guardar ficha de cliente:
  - Adicionado `@field_validator` no modelo `ProcessUpdate` para converter `client_email` e `client_phone` para string
  - Frontend converte explicitamente para `String()` antes de enviar
  - Testado e verificado: guardar funciona sem erros de validação
- ✅ **Nova Funcionalidade - Criação de Leads via URL (P0)**:
  - Novo endpoint `POST /api/leads/from-url` que extrai dados e cria lead automaticamente
  - Verifica duplicados antes de criar
  - Regista erros de scraping no sistema de logs
  - Retorna lead criado com dados extraídos
- ✅ **Nova Funcionalidade - Página de Logs do Sistema (P0)**:
  - Nova página `/admin/logs` para visualizar erros do sistema
  - Endpoints implementados:
    - `GET /api/admin/system-logs` - Lista com filtros e paginação
    - `GET /api/admin/system-logs/stats` - Estatísticas (total, não lidos, críticos)
    - `POST /api/admin/system-logs/mark-read` - Marcar como lido
    - `POST /api/admin/system-logs/{id}/resolve` - Resolver erro
    - `DELETE /api/admin/system-logs/cleanup` - Limpar antigos
  - UI com:
    - Cards de estatísticas (Total, Não Lidos, Por Resolver, Críticos)
    - Filtros por severidade, componente, estado, período
    - Tabela paginada com detalhes
    - Dialog para ver detalhes e resolver erros
  - Link adicionado no menu Admin
- ✅ **Serviço de Error Logging**: Novo serviço `system_error_logger.py` centralizado

**10 Fevereiro 2026**
- ✅ **Bug Fix Crítico - Extração NIF de CC**: Corrigido bug onde NIF era extraído incorretamente de documentos CC (começava por 5 em vez do valor real):
  - Alterado `detail` de `'low'` para `'high'` na API de visão para documentos CC/CPCV
  - Aumentado DPI de conversão PDF→imagem de 200 para 300 para documentos CC/CPCV
  - Imagens de CC não são mais redimensionadas para preservar qualidade
  - Prompts melhorados com instruções específicas sobre localização do NIF no verso do cartão
  - Testado com CC da Carolina Silva: NIF 268494622 extraído correctamente
- ✅ **Nova Funcionalidade - Lista de Clientes para Consultores (P0)**:
  - Novo endpoint `GET /api/processes/my-clients` com filtro por consultor
  - Nova página `/meus-clientes` com:
    - Estatísticas: Total de Clientes, Com Tarefas Pendentes, Com Imóvel Associado
    - Pesquisa por nome, email ou nº processo
    - Filtro por fase do workflow
    - Tabela com: Nº, Cliente, Fase, Ações Pendentes, Última Atualização, Ações
  - Link "Os Meus Clientes" adicionado na navegação para consultores
- ✅ **Bug Fix - Dados CPCV não guardados (P2)**:
  - Adicionados campos ao modelo `RealEstateData`: valor_imovel, data_cpcv, data_escritura_prevista, tipologia, etc.
  - Adicionados campos ao modelo `FinancialData`: valor_entrada, valor_pretendido, data_sinal, etc.
  - Adicionados campos ao modelo `ProcessUpdate`: co_buyers, vendedor, mediador
  - Adicionados campos ao modelo `ProcessResponse` para retornar dados do CPCV
  - Endpoint `PUT /processes/{id}` agora guarda todos os campos do CPCV
- ✅ **Instalação libmagic**: Corrigido erro de importação do python-magic para validação de ficheiros

**9 Fevereiro 2026**
- ✅ **Segurança: SlowAPI Rate Limiting**: Implementado nas rotas públicas e de autenticação
  - Login: 5 requests/minuto
  - Register: 3 requests/minuto
  - Client Registration: 3 requests/minuto
- ✅ **Segurança: CORS Estrito**: Refatorado para usar variáveis de ambiente com validação
  - CORS_ORIGINS aceita lista de origens separadas por vírgula
  - Validação de formato de URLs
  - Avisos em modo desenvolvimento
- ✅ **Segurança: CI/CD Security Scan**: Workflow GitHub Actions criado
  - Safety para vulnerabilidades de dependências
  - Bandit para análise estática de código
  - Execução semanal automática + em PRs
- ✅ **Página Leads para Consultores**: Adicionada rota `/leads` e link de navegação
- ✅ **Bug Fix LeadsKanban**: Corrigido bug SelectItem com valor vazio
- ✅ **Verificação Trello**: Confirmado funcional (14 listas, 152 processos)
- ✅ **Impersonation Testado**: admin→consultor→admin funciona
- ✅ **Visibilidade Clientes**: Consultor vê 100 clientes baseado em processos

### Issues Verificados e Resolvidos
| Issue | Estado | Notas |
|-------|--------|-------|
| Trello 401 Error | ✅ RESOLVIDO | API conectada |
| Impersonation Error | ✅ RESOLVIDO | Fluxo completo testado |
| Bulk Upload postMessage | ✅ WORKAROUND | Patch aplicado |
| Consultor não vê clientes | ✅ RESOLVIDO | 100 clientes visíveis |
| Leads para Consultor | ✅ RESOLVIDO | Rota e navegação adicionadas |
| Rate Limiting | ✅ IMPLEMENTADO | SlowAPI em rotas públicas |
| CORS Estrito | ✅ IMPLEMENTADO | Validação via .env |
| Security Scan CI/CD | ✅ IMPLEMENTADO | GitHub Actions workflow |

**10 Fevereiro 2026**
- ✅ **Correção de Testes Unitários**: Resolvido problema de asyncio event loop com Motor driver
  - Actualizado `conftest.py` com `reset_db_connection()` entre testes
  - Criado `DatabaseProxy` em `database.py` para conexões on-demand
  - Corrigidos fixtures de autenticação (admin, consultor, mediador)
  - Todos os 16 testes passam (test_auth.py + test_processes.py)
- ✅ **Melhorias no Módulo de Gestão de Leads**:
  - Novo endpoint `POST /api/leads/{id}/refresh` para verificar se preço mudou
  - Botão "🔄 Verificar Preço" no card de cada lead
  - Filtro por Consultor no Kanban de Leads
  - Filtro por Estado no Kanban de Leads
  - Endpoint `GET /api/leads/consultores` para lista de consultores
  - Data de entrada nos cards ("Há X dias")
  - Destaque visual (borda vermelha) para leads antigas (>7 dias em "Novo")
- ✅ **Nova Página de Estatísticas de Leads**:
  - Tab "Funil de Leads" com gráfico de barras (5 fases)
  - Tab "Ranking Consultores" com top 5 consultores por leads angariados
  - Endpoint `GET /api/stats/leads` retorna estatísticas
  - Endpoint `GET /api/stats/conversion` retorna tempo médio de conversão
  - KPIs: Total de Leads, Tempo Médio de Conversão, Leads Convertidos
- ✅ **Correção de Bug UI**: Toast notifications movidas para bottom-right (não tapam botões)
- ✅ **Correção de Bug de Acesso**: Consultores podem agora aceder a processos que criaram
  - Função `can_view_process()` actualizada para verificar `created_by`
- ✅ **Melhorias no Scraper**: Adicionado fallback SSL, parser ERA melhorado
- ✅ **Tab CPCV na página de detalhes**: Nova secção dedicada ao Contrato Promessa Compra e Venda com:
  - Dados do Imóvel (valor, tipologia, área, morada)
  - Dados do Vendedor (nome, NIF, telefone, email, morada)
  - Compradores (principal + co-compradores do CPCV)
  - Valores e Datas (entrada, sinal, data CPCV, escritura prevista)
  - Mediador (se existir)
- ✅ **Cartões do Kanban compactados**: Tamanho reduzido para melhor visualização
- ✅ **Ficheiros de teste temporários limpos**
- ✅ **Sistema de Logging de Erros de Importação**:
  - Novo endpoint `GET /api/ai/bulk/import-errors` - lista erros de importação
  - Novo endpoint `GET /api/ai/bulk/import-errors/summary` - resumo estatístico
  - Novo endpoint `POST /api/ai/bulk/import-errors/{id}/resolve` - marcar como resolvido
  - Novo endpoint `DELETE /api/ai/bulk/import-errors/clear` - limpar erros antigos
  - Erros guardados na colecção `import_errors` com: cliente, ficheiro, tipo, erro, timestamp
  - Agrupamento por tipo de erro para identificar padrões
- ✅ **Sistema de Matching - UI Clientes Sugeridos**:
  - Botão sparkles (✨) no cartão de lead para ver clientes compatíveis
  - Dialog mostra clientes com score de match e razões do match
  - Corrigido bug em `client_match.py` (NoneType error em financial_data)
- ✅ **Scraper melhorado**:
  - Headers mais realistas (Sec-Fetch, Cache-Control)
  - Delay aleatório entre requests
  - Suporte HTTP/2
  - Handling correcto de erros SSL
- ✅ **Bug login consultor VERIFICADO**: Consultor consegue aceder a processos atribuídos

**11 Fevereiro 2026**
- ✅ **Cartões do Quadro Geral de Processos Ultra-Compactos**:
  - Reduzido padding de p-2 para p-1.5
  - Fonte do nome de text-xs para text-[11px]
  - Número do processo de text-[10px] para text-[9px]
  - Removidos badges de Trello e Consultor para economizar espaço
  - Layout em linha única: nome + número + badge prioridade + botão ver
  - Adicionado data-testid para testes automatizados
- ✅ **Validação de NIF para Clientes Particulares**:
  - Backend: função `validate_nif()` actualizada para rejeitar NIFs começados por 5 (empresas)
  - Frontend: validação em tempo real no campo NIF com mensagem de erro
  - Erro mostrado: "NIF de empresa (começa por 5) não é permitido para clientes particulares"
  - Campo fica com borda vermelha quando inválido
  - Validação também bloqueia guardar o processo se NIF for inválido
- ✅ **Importar Imóveis via Excel**:
  - Novo endpoint `POST /api/properties/bulk/import-excel`
  - Aceita ficheiros .xlsx e .xls
  - Colunas obrigatórias: titulo, preco, distrito, concelho, proprietario_nome
  - 14 colunas opcionais: tipo, quartos, area_util, estado, etc.
  - Retorna estatísticas: total, importados, erros com linha
  - Erros são logados na colecção `error_logs` para análise
  - Novo endpoint `GET /api/properties/bulk/import-template` com instruções
  - Botão "Importar Excel" na página de Imóveis
  - Dialog mostra resultados da importação com erros detalhados
- ✅ **Sistema de Sugestões de Melhoria (Aprender com Erros)**:
  - Novo endpoint `GET /api/ai/bulk/import-errors/suggestions`
  - Analisa padrões nos erros de importação
  - Gera sugestões categorizadas por: validation, format, data_quality, geography, owner_data
  - Cada sugestão tem: título, descrição, acção recomendada, prioridade
  - Identifica erros de: campos em falta, formato errado, NIFs inválidos, localização

**8 Fevereiro 2026** (noite - final)
- ✅ **UI Gestão de Clientes**: Nova página `/clientes` com:
  - Lista de clientes com pesquisa por nome/email/NIF
  - Estatísticas (total clientes, com processos activos)
  - Criar novos clientes
  - Criar processos para clientes existentes
  - Eliminar clientes (se sem processos activos)
- ✅ **Múltiplos Processos por Cliente**: Backend completo e testado
  - `POST /api/clients/{id}/create-process` - processo #153 criado com sucesso
- ❌ **Removida integração Idealista**: A pedido do utilizador, para evitar ban da conta empresarial

**8 Fevereiro 2026** (noite - continuação)
- ✅ **Múltiplos Processos por Cliente**: Nova arquitectura que permite um cliente ter múltiplos processos de compra:
  - Novo modelo `Client` separado do `Process`
  - Rotas CRUD em `/api/clients`
  - Endpoints: `POST /clients/{id}/link-process`, `POST /clients/{id}/create-process`, `GET /clients/{id}/processes`
  - Endpoint `POST /clients/find-or-create` para encontrar ou criar cliente automaticamente
- ✅ **Co-Compradores no Frontend**: Secção visual na ficha de cliente mostrando co-compradores e co-proponentes detectados em documentos (CPCV, IRS conjunto, simulações)
- ✅ **Integração API Idealista**: Serviço `services/idealista_api.py` com OAuth2, pesquisa por localização, filtros de preço/tipologia
  - Endpoints: `POST /api/leads/search/idealista`, `GET /api/leads/search/idealista/status`
  - Requer configuração: `IDEALISTA_API_KEY` e `IDEALISTA_API_SECRET` no .env

**8 Fevereiro 2026** (noite)
- ✅ **Bug Fix Crítico - Análise de Documentos**: Corrigido bug onde dados extraídos de documentos não eram guardados quando `personal_data`, `financial_data` ou `real_estate_data` eram `None` (em vez de `{}`). O problema estava na função `build_update_data_from_extraction` em `services/ai_document.py` que usava `.get("key", {})` que retorna `None` quando a chave existe mas tem valor `None`, causando erro `NoneType.update()`. Corrigido para usar `.get("key") or {}`.
- ✅ **Deteção de Documentos Duplicados (P1)**: Implementada persistência de hashes de documentos na base de dados para evitar re-análise de documentos idênticos, mesmo após reinício do servidor:
  - Novos campos `analyzed_documents` array em cada processo
  - Função `check_duplicate_comprehensive()` verifica cache + DB
  - Função `persist_document_analysis()` guarda hash, tipo, data, campos extraídos
  - Novo endpoint `GET /api/ai/bulk/analyzed-documents/{process_id}` lista documentos analisados
  - Expandido para mais tipos: recibo_vencimento, extrato_bancario, irs, contrato_trabalho, certidao
- ✅ **Múltiplos Compradores/Proponentes (P2)**: Sistema detecta automaticamente múltiplas pessoas em documentos:
  - **CPCV**: Extrai array `compradores` com dados de todos os compradores (casal/parceiros)
  - **Simulação Crédito**: Extrai array `proponentes` e calcula `rendimento_agregado`
  - **IRS Conjunto**: Detecta cônjuge (sujeito passivo B) e guarda em `co_applicants`
  - Prompts da IA actualizados para identificar "Proponente 1", "Proponente 2", "Cônjuge"
  - Novos campos no processo: `co_buyers`, `co_applicants`
  - Endpoint de diagnóstico mostra co-compradores se existirem

**11 Fevereiro 2026** (continuação)
- ✅ **Pipeline CI/CD Corrigida**:
  - Adicionado `seed.py` ao workflow para criar utilizadores de teste
  - Adicionado `libmagic1` como dependência de sistema
  - Adicionado `arq` ao requirements.txt
  - Testes agora passam no GitHub Actions
- ✅ **Redução de Emails para Admin**:
  - Emails de novo cliente enviados apenas para o PRIMEIRO admin/ceo
  - Outros admins recebem notificação via sistema interno (sem spam)
- ✅ **Smart Crawler (Navegação Recursiva)**:
  - Novo método `crawl_recursive(start_url, max_pages, max_depth)` em `scraper.py`
  - Novo endpoint `POST /api/scraper/crawl` para crawling de múltiplas páginas
  - Extrai automaticamente links de imóveis dentro do mesmo domínio
  - Suporta até 50 páginas e profundidade 3
  - Endpoint `GET /api/scraper/supported-sites` lista sites suportados
- ✅ **Motor de Validação de Documentos**:
  - Novo serviço `document_processor.py`
  - Conversão automática de imagens para PDF (img2pdf)
  - Campo `data_emissao` adicionado ao modelo de documento
  - Validação de validade: documentos com mais de 180 dias (6 meses) são alertados
  - Função `validate_document_for_process()` verifica todos os documentos
- ✅ **Calendário Global (Visão CEO)**:
  - Endpoint `GET /api/tasks` aceita `?user_id=all` para admin/ceo
  - Retorna tarefas de toda a equipa para calendário global
  - Filtro `?user_id=<id>` para ver tarefas de utilizador específico
  - Permissões: apenas admin/ceo/diretor podem ver tarefas de outros
- ✅ **Webhooks Trello Bidirecionais**:
  - Endpoint `POST /api/trello/webhook` melhorado
  - Processa `addMemberToCard`: atribui consultor/mediador automaticamente
  - Processa `removeMemberFromCard`: remove atribuição
  - Movimento de cartões actualiza status do processo
  - Usa mapeamento `trello_member_mappings` para identificar utilizadores

**8 Fevereiro 2026**
- ✅ **Upload de Fotos para Imóveis**: Novos endpoints `/api/properties/{id}/upload-photo` e `DELETE /photo`
- ✅ **Notificações Automáticas de Match**: Sistema notifica quando imóvel novo tem clientes compatíveis (score ≥50%)
- ✅ **Filtro de Extracção de Nomes**: Lista de palavras bloqueadas (seguradoras, bancos) para evitar extracção incorrecta
- ✅ **Match Automático Cliente ↔ Imóvel (P1 Completo)**:
  - Novo endpoint `/api/match/client/{id}/all` combina leads + imóveis angariados
  - Novo endpoint `/api/match/property/{id}/clients` encontra clientes para imóvel angariado
  - Score baseado em preço (40pts), localização (35pts), tipologia (25pts)
- ✅ **Módulo Imóveis Angariados (P0 Completo)**:
  - Backend: Modelo `Property` com dados completos
  - API CRUD: `/api/properties` com filtros, estatísticas
  - Frontend: Página `/imoveis` com cards, filtros, formulário
  - Referências automáticas (IMO-001, IMO-002...)
- ✅ **ScraperAPI Integrado**: Para contornar bloqueios de portais imobiliários
- ✅ **Sanitização de Emails**: Função `sanitize_email()` em 3 locais críticos

**6 Fevereiro 2026**
- ✅ Sincronizado ambiente de desenvolvimento com MongoDB Atlas de produção
- ✅ Configurada separação de dados: `powerprecision_dev` (testes) vs `powerprecision` (produção)
- ✅ Código local mantido (inclui otimização de verificação de cliente no upload massivo)
- ✅ Comparadas diferenças com repositório GitHub - código local mais avançado

**5 Fevereiro 2026**
- Corrigido bug de layout dos botões no Kanban (CSS Grid)
- Implementado botão "Abrir no OneDrive" na página de detalhes
- Limpeza de código (removido onedrive_shared.py redundante)
- Testada funcionalidade de atribuição de processos via API
