# 📘 GUIÃO DO SISTEMA CREDITOIMO

## Sistema de Gestão de Processos Imobiliários e Crédito

**Power Real Estate & Precision Crédito**

---

## 📋 Índice

1. [Introdução](#1-introdução)
2. [Acesso ao Sistema](#2-acesso-ao-sistema)
3. [Papéis e Permissões](#3-papéis-e-permissões)
4. [Dashboard Principal](#4-dashboard-principal)
5. [Quadro Kanban](#5-quadro-kanban)
6. [Gestão de Processos](#6-gestão-de-processos)
7. [Calendário e Prazos](#7-calendário-e-prazos)
8. [Documentos e Validades](#8-documentos-e-validades)
9. [Estatísticas](#9-estatísticas)
10. [Formulário Público](#10-formulário-público)
11. [Referência Técnica](#11-referência-técnica)

---

## 1. Introdução

O **CreditoIMO** é um sistema integrado de gestão de processos para empresas do sector imobiliário e de intermediação de crédito. Foi desenvolvido especificamente para:

- **Power Real Estate** - Consultoria imobiliária
- **Precision Crédito** - Intermediação de crédito habitação

### Funcionalidades Principais

✅ Gestão visual de processos com quadro Kanban  
✅ Controlo de 14 fases de workflow  
✅ Calendário com prazos e alertas  
✅ Rastreamento de validade de documentos (60 dias)  
✅ Estatísticas e relatórios  
✅ Formulário público de registo de clientes  
✅ Controlo de acesso por papel  

---

## 2. Acesso ao Sistema

### Credenciais de Acesso

| Utilizador | Email | Password | Papel |
|------------|-------|----------|-------|
| Admin | admin@sistema.pt | admin2026 | Administrador |
| Pedro Borges | pedro@powerealestate.pt | power2026 | CEO |
| Tiago Borges | tiago@powerealestate.pt | power2026 | Consultor |
| Flávio da Silva | flavio@powerealestate.pt | power2026 | Consultor |
| Estácio Miranda | estacio@precisioncredito.pt | power2026 | Intermediário |
| Fernando Andrade | fernando@precisioncredito.pt | power2026 | Intermediário |
| Carina Amuedo | carina@powerealestate.pt | power2026 | Consultor/Intermediário |
| Marisa Rodrigues | marisa@powerealestate.pt | power2026 | Consultor/Intermediário |

### Processo de Login

1. Aceda ao sistema através do URL fornecido
2. Introduza o email e password
3. Clique em "Entrar"
4. Será redirecionado para o dashboard apropriado ao seu papel

```
📌 EXEMPLO DE CÓDIGO - Autenticação

// Frontend: Chamada à API de login
const login = async (email, password) => {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const data = await response.json();
  // Token JWT guardado para autenticação subsequente
  localStorage.setItem('token', data.access_token);
};
```

---

## 3. Papéis e Permissões

### Hierarquia de Acesso

```
ADMINISTRADOR (admin)
    └── Acesso total ao sistema
    └── Gestão de utilizadores
    └── Configurações do sistema

CEO (ceo)
    └── Visão global de todos os processos
    └── Estatísticas gerais
    └── Relatórios executivos

CONSULTOR (consultor)
    └── Processos imobiliários atribuídos
    └── Agendamento de visitas
    └── Acompanhamento de clientes

INTERMEDIÁRIO (intermediario)
    └── Processos de crédito atribuídos
    └── Contacto com bancos
    └── Gestão documental

CONSULTOR/INTERMEDIÁRIO (consultor_intermediario)
    └── Ambas as funções
    └── Processos mistos

CLIENTE (cliente)
    └── Visualização do próprio processo
    └── Upload de documentos
```

### Código de Verificação de Permissões

```python
# Backend: Decorador de verificação de papel
from services.auth import require_roles
from models.auth import UserRole

@router.get("/processos")
async def listar_processos(
    user: dict = Depends(require_roles([
        UserRole.ADMIN, 
        UserRole.CEO,
        UserRole.CONSULTOR
    ]))
):
    # Apenas utilizadores com estes papéis podem aceder
    return await obter_processos(user)
```

---

## 4. Dashboard Principal

O dashboard é a página inicial após login, adaptada ao papel do utilizador.

### Dashboard do Administrador

**Funcionalidades:**
- Quadro Kanban com todos os processos
- Filtros por consultor e intermediário
- Abas: Visão Geral, Calendário, Documentos, Análise IA, Pesquisar

**Interface:**
```
┌─────────────────────────────────────────────────────────────┐
│  🏠 POWER REAL ESTATE & PRECISION                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 155 Processos  │  👥 8 Utilizadores  │  📋 14 Estados   │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Espera   │ │ Docum.   │ │ Bancária │ │ Aprovado │  ...  │
│  │   15     │ │   20     │ │   18     │ │   12     │       │
│  │ ▪▪▪▪▪    │ │ ▪▪▪▪▪    │ │ ▪▪▪▪▪    │ │ ▪▪▪▪▪    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Código do Dashboard

```javascript
// Frontend: Componente de estatísticas do dashboard
const DashboardStats = () => {
  const [stats, setStats] = useState(null);
  
  useEffect(() => {
    // Buscar estatísticas da API
    const fetchStats = async () => {
      const response = await api.get('/api/stats');
      setStats(response.data);
    };
    fetchStats();
  }, []);
  
  return (
    <div className="grid grid-cols-4 gap-4">
      <StatCard 
        titulo="Total Processos" 
        valor={stats?.total_processes} 
        icone={<FileText />}
      />
      <StatCard 
        titulo="Ativos" 
        valor={stats?.active_processes}
        icone={<Activity />}
      />
      {/* ... mais cards */}
    </div>
  );
};
```

---

## 5. Quadro Kanban

O quadro Kanban permite visualizar e gerir processos através de 14 fases.

### Fases do Workflow

| # | Fase | Cor | Descrição |
|---|------|-----|-----------|
| 1 | Clientes em Espera | 🟡 Amarelo | Novos clientes aguardando triagem |
| 2 | Fase Documental | 🔵 Azul | Recolha de documentos inicial |
| 3 | Fase Documental II | 🔵 Azul | Documentação complementar |
| 4 | Enviado ao Bruno | 🟣 Roxo | Análise por parceiro |
| 5 | Enviado ao Luís | 🟣 Roxo | Análise por parceiro |
| 6 | Enviado BCP Rui | 🟣 Roxo | Contacto bancário |
| 7 | Entradas Precision | 🟠 Laranja | Recepção pela Precision |
| 8 | Fase Bancária | 🟠 Laranja | Pré-aprovação bancária |
| 9 | Fase de Visitas | 🔵 Azul | Visitas a imóveis |
| 10 | CH Aprovado | 🟢 Verde | Crédito aprovado, avaliação |
| 11 | Fase de Escritura | 🟢 Verde | Preparação de escritura |
| 12 | Escritura Agendada | 🟢 Verde | Data de escritura marcada |
| 13 | Concluídos | 🟢 Verde | Processo finalizado |
| 14 | Desistências | 🔴 Vermelho | Processo cancelado |

### Mover Processos (Drag & Drop)

```javascript
// Frontend: Handler de drag & drop do Kanban
const handleDragEnd = async (result) => {
  const { draggableId, destination, source } = result;
  
  // Verificar se houve movimento válido
  if (!destination) return;
  if (destination.droppableId === source.droppableId) return;
  
  // Atualizar estado local imediatamente (otimista)
  const novoEstado = destination.droppableId;
  atualizarEstadoLocal(draggableId, novoEstado);
  
  // Enviar atualização à API
  try {
    await api.put(`/api/processes/${draggableId}`, {
      status: novoEstado
    });
  } catch (error) {
    // Reverter em caso de erro
    reverterEstado(draggableId, source.droppableId);
    toast.error('Erro ao mover processo');
  }
};
```

### Cartão de Processo

Cada cartão mostra:
- Nome do cliente
- Telefone
- Tipo de processo (Crédito/Imobiliária/Ambos)
- Valor financiado
- Etiquetas (Urgente, VIP, etc.)

```
┌────────────────────────┐
│ 👤 Maria Silva         │
│ 📞 +351 912 345 678    │
│ 💰 €250.000            │
│ ┌──────┐ ┌─────────┐   │
│ │VIP   │ │1ª Casa  │   │
│ └──────┘ └─────────┘   │
└────────────────────────┘
```

---

## 6. Gestão de Processos

### Criar Novo Processo

Os processos são criados através:
1. Formulário público (clientes)
2. Back-office (colaboradores)

```python
# Backend: Modelo de dados do processo
class ProcessResponse(BaseModel):
    id: str                           # UUID único
    client_id: str                    # ID do cliente
    client_name: str                  # Nome completo
    client_email: str                 # Email
    client_phone: str                 # Telefone
    process_type: str                 # credito/imobiliaria/ambos
    status: str                       # Fase atual
    personal_data: dict               # Dados pessoais
    financial_data: dict              # Dados financeiros
    real_estate_data: dict            # Dados do imóvel
    credit_data: dict                 # Dados do crédito
    assigned_consultor_id: str        # Consultor atribuído
    assigned_mediador_id: str         # Intermediário atribuído
    created_at: str                   # Data de criação
    updated_at: str                   # Última atualização
```

### Detalhes do Processo

Ao clicar num processo, abre-se um modal com:

- **Dados Pessoais:** NIF, morada, estado civil, profissão
- **Dados Financeiros:** Rendimento, despesas, tipo de emprego
- **Dados do Imóvel:** Tipo, localização, características
- **Dados do Crédito:** Valor, prazo, taxa, banco

### Filtros Disponíveis

```javascript
// Frontend: Componente de filtros
const ProcessFilters = () => {
  return (
    <div className="flex gap-4">
      <Select 
        placeholder="Consultor"
        options={consultores}
        onChange={filtrarPorConsultor}
      />
      <Select 
        placeholder="Intermediário"
        options={intermediarios}
        onChange={filtrarPorIntermediario}
      />
      <Select 
        placeholder="Estado"
        options={workflowStatuses}
        onChange={filtrarPorEstado}
      />
      <Input 
        placeholder="Pesquisar cliente..."
        onChange={pesquisarCliente}
      />
    </div>
  );
};
```

---

## 7. Calendário e Prazos

### Funcionalidades

- Visualização mensal de eventos
- Prazos de tarefas
- **Alertas de documentos a expirar (60 dias)**
- Agendamentos de visitas e escrituras

### Tipos de Eventos

| Tipo | Ícone | Cor |
|------|-------|-----|
| Reunião com cliente | 👥 | Azul |
| Visita a imóvel | 🏠 | Verde |
| Entrega de documentos | 📄 | Laranja |
| Escritura | ✍️ | Roxo |
| **Documento a expirar** | ⚠️ | Vermelho/Âmbar |

### Documentos no Calendário

Os documentos a expirar nos próximos **60 dias** aparecem automaticamente no calendário:

```python
# Backend: Obter eventos de expiração para calendário
@router.get("/documents/expiry/calendar")
async def get_expiry_calendar_events(user: dict = Depends(get_current_user)):
    """
    Documentos a expirar nos próximos 60 dias formatados
    como eventos de calendário.
    """
    EXPIRY_WARNING_DAYS = 60
    
    today = datetime.now().date()
    future = today + timedelta(days=EXPIRY_WARNING_DAYS)
    
    docs = await db.documents.find({
        "expiry_date": {"$gte": str(today), "$lte": str(future)}
    }).to_list(1000)
    
    events = []
    for doc in docs:
        days_until = (parse_date(doc["expiry_date"]) - today).days
        
        # Definir urgência e cor
        if days_until <= 7:
            urgency, color = "critical", "#EF4444"  # Vermelho
        elif days_until <= 30:
            urgency, color = "warning", "#F59E0B"   # Âmbar
        else:
            urgency, color = "normal", "#3B82F6"    # Azul
        
        events.append({
            "id": f"doc-{doc['id']}",
            "title": f"📄 {doc['document_name']}",
            "date": doc["expiry_date"],
            "color": color,
            "urgency": urgency
        })
    
    return events
```

---

## 8. Documentos e Validades

### Tipos de Documentos

| Tipo | Validade Típica |
|------|-----------------|
| Cartão de Cidadão | 5 anos |
| Passaporte | 5 anos |
| Carta de Condução | 15 anos |
| Contrato de Trabalho | Variável |
| Recibos de Vencimento | 3 meses |
| Declaração IRS | 1 ano |
| Certidão Predial | 6 meses |
| Caderneta Predial | 1 ano |

### Sistema de Alertas (60 dias)

O sistema alerta automaticamente sobre documentos a expirar:

```
⚠️ ALERTAS DE VALIDADE

┌─────────────────────────────────────────────────────────┐
│ 🔴 CRÍTICO (< 7 dias)                                   │
│    • CC de Maria Silva - expira em 3 dias               │
│    • Passaporte de João Costa - expira em 5 dias        │
├─────────────────────────────────────────────────────────┤
│ 🟡 ATENÇÃO (7-30 dias)                                  │
│    • Recibos de Ana Ferreira - expiram em 15 dias       │
│    • Certidão de Pedro Santos - expira em 22 dias       │
├─────────────────────────────────────────────────────────┤
│ 🔵 NORMAL (30-60 dias)                                  │
│    • IRS de Rui Martins - expira em 45 dias             │
└─────────────────────────────────────────────────────────┘
```

### Código de Verificação de Validade

```javascript
// Frontend: Componente de documentos a expirar
const DocumentosExpirar = () => {
  const [documentos, setDocumentos] = useState([]);
  
  useEffect(() => {
    // Buscar documentos a expirar em 60 dias
    const fetchDocs = async () => {
      const response = await api.get('/api/documents/expiry/upcoming?days=60');
      setDocumentos(response.data);
    };
    fetchDocs();
  }, []);
  
  const getUrgencyClass = (diasRestantes) => {
    if (diasRestantes <= 7) return 'doc-expiring-soon';    // Vermelho
    if (diasRestantes <= 30) return 'doc-expiring-warning'; // Âmbar
    return 'doc-valid';                                     // Verde
  };
  
  return (
    <div className="space-y-2">
      {documentos.map(doc => (
        <div 
          key={doc.id} 
          className={`p-3 rounded ${getUrgencyClass(doc.days_until_expiry)}`}
        >
          <span className="font-medium">{doc.document_name}</span>
          <span className="text-sm ml-2">
            {doc.client_name} - {doc.days_until_expiry} dias
          </span>
        </div>
      ))}
    </div>
  );
};
```

---

## 9. Estatísticas

### Métricas Disponíveis

- **Total de Processos:** Contagem geral
- **Processos Ativos:** Em andamento
- **Taxa de Sucesso:** % de aprovações
- **Valor Total:** Soma dos valores financiados
- **Por Fase:** Distribuição no workflow
- **Por Consultor:** Performance individual

### Gráficos

O sistema utiliza **Recharts** para visualização:

```javascript
// Frontend: Gráfico de distribuição por fase
import { BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

const GraficoFases = ({ dados }) => {
  return (
    <BarChart width={600} height={300} data={dados}>
      <XAxis dataKey="fase" />
      <YAxis />
      <Tooltip />
      <Bar 
        dataKey="quantidade" 
        fill="hsl(var(--primary))"  // Azul Power
      />
    </BarChart>
  );
};
```

### Filtros de Estatísticas

- Por período (últimos 7/30/90 dias, personalizado)
- Por utilizador
- Por tipo de processo

---

## 10. Formulário Público

### Wizard de 6 Passos

Clientes podem registar-se através de um formulário público:

```
PASSO 1: Dados Pessoais
    └── Nome, Email, Telefone, NIF

PASSO 2: Informação Adicional
    └── Data nascimento, Estado civil, Morada

PASSO 3: Segundo Titular (opcional)
    └── Dados do cônjuge/titular adicional

PASSO 4: Preferências Imóvel
    └── Tipo, Localização, Características

PASSO 5: Situação Financeira
    └── Rendimento, Despesas, Emprego

PASSO 6: Confirmação
    └── Resumo e submissão
```

### Código do Formulário

```javascript
// Frontend: Wizard de registo público
const PublicClientForm = () => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({});
  
  const steps = [
    { title: 'Dados Pessoais', component: <DadosPessoais /> },
    { title: 'Informação Adicional', component: <InfoAdicional /> },
    { title: 'Segundo Titular', component: <SegundoTitular /> },
    { title: 'Preferências', component: <Preferencias /> },
    { title: 'Financeiro', component: <DadosFinanceiros /> },
    { title: 'Confirmação', component: <Confirmacao /> },
  ];
  
  const handleSubmit = async () => {
    const response = await api.post('/api/public/register', formData);
    if (response.ok) {
      toast.success('Registo submetido com sucesso!');
    }
  };
  
  return (
    <div className="max-w-2xl mx-auto">
      <StepIndicator current={step} total={6} />
      {steps[step - 1].component}
      <div className="flex justify-between mt-6">
        <Button onClick={() => setStep(s => s - 1)} disabled={step === 1}>
          Anterior
        </Button>
        {step < 6 ? (
          <Button onClick={() => setStep(s => s + 1)}>
            Seguinte
          </Button>
        ) : (
          <Button onClick={handleSubmit}>
            Submeter
          </Button>
        )}
      </div>
    </div>
  );
};
```

---

## 11. Referência Técnica

### Arquitetura do Sistema

```
┌──────────────────────────────────────────────────────────┐
│                      FRONTEND                            │
│  React 18 + Tailwind CSS + shadcn/ui + Recharts         │
│                         │                                │
│              REACT_APP_BACKEND_URL                       │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│                      BACKEND                             │
│         FastAPI + Python 3.11 + Motor (async)           │
│                         │                                │
│                     MONGO_URL                            │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│                     MONGODB                              │
│         Collections: users, processes, deadlines,       │
│         documents, workflow_statuses, activities        │
└──────────────────────────────────────────────────────────┘
```

### Estrutura de Pastas

```
/app
├── backend/
│   ├── models/          # Modelos Pydantic
│   ├── routes/          # Endpoints da API
│   ├── services/        # Lógica de negócio
│   ├── database.py      # Conexão MongoDB
│   └── server.py        # Aplicação FastAPI
│
├── frontend/
│   ├── src/
│   │   ├── components/  # Componentes React
│   │   ├── contexts/    # Context API (Auth)
│   │   ├── pages/       # Páginas da aplicação
│   │   ├── services/    # Chamadas à API
│   │   └── App.js       # Router principal
│   └── public/
│
├── scripts/
│   └── seed_database.py # Script de dados demo
│
└── docs/
    ├── GUIA_UTILIZADOR.md
    └── APRESENTACAO.md
```

### APIs Principais

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/auth/login` | POST | Autenticação |
| `/api/processes` | GET | Listar processos |
| `/api/processes/{id}` | GET | Detalhes do processo |
| `/api/processes/{id}` | PUT | Atualizar processo |
| `/api/processes/kanban` | GET | Dados para Kanban |
| `/api/stats` | GET | Estatísticas |
| `/api/deadlines` | GET | Eventos/Prazos |
| `/api/documents/expiry/upcoming` | GET | Docs a expirar |
| `/api/users` | GET | Listar utilizadores |
| `/api/public/register` | POST | Registo público |

### Variáveis de Ambiente

```bash
# Backend (.env)
MONGO_URL=mongodb://localhost:27017

# Frontend (.env)
REACT_APP_BACKEND_URL=https://example.com
```

---

## 📞 Suporte

Para questões técnicas ou dúvidas sobre o sistema:

- **Email:** suporte@powerealestate.pt
- **Documentação:** /docs/GUIA_UTILIZADOR.md

---

*Documento gerado automaticamente - CreditoIMO v2.0*
*Janeiro 2026*
