# CreditoIMO - Product Requirements Document

## Problema Original
Aplicação de gestão de processos de crédito habitação e transações imobiliárias que funciona como "espelho" de um quadro Trello, com sincronização bidirecional.

## Stack Técnica
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, Pydantic, Motor (MongoDB async)
- **Base de Dados**: MongoDB Atlas (Cluster: cluster0.c8livu.mongodb.net)
  - **Desenvolvimento/Testes**: `powerprecision_dev`
  - **Produção**: `powerprecision`
- **Integrações**: Trello API & Webhooks, IMAP/SMTP (emails), OneDrive (via link partilhado), Gemini 2.0 Flash (scraping)

## Última Actualização - 11 Fevereiro 2026

### ✅ Correcções e Melhorias Implementadas

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
