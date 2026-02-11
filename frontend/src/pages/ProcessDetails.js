import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Calendar } from "../components/ui/calendar";
import { ScrollArea } from "../components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Separator } from "../components/ui/separator";
import { Popover, PopoverContent, PopoverTrigger } from "../components/ui/popover";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../components/ui/accordion";
import {
  getProcess,
  updateProcess,
  getDeadlines,
  createDeadline,
  updateDeadline,
  deleteDeadline,
  getActivities,
  createActivity,
  deleteActivity,
  getHistory,
  getWorkflowStatuses,
  getClientOneDriveFiles,
  getOneDriveDownloadUrl,
} from "../services/api";
import OneDriveLinks from "../components/OneDriveLinks";
import ProcessAlerts from "../components/ProcessAlerts";
import TasksPanel from "../components/TasksPanel";
import ProcessSummaryCard from "../components/ProcessSummaryCard";
import EmailHistoryPanel from "../components/EmailHistoryPanel";
import AIDocumentAnalyzer from "../components/AIDocumentAnalyzer";
import DocumentChecklist from "../components/DocumentChecklist";
import ProcessTimeline from "../components/ProcessTimeline";
import ClientPropertyMatch from "../components/ClientPropertyMatch";
import {
  ArrowLeft,
  User,
  Briefcase,
  Building2,
  CreditCard,
  Calendar as CalendarIcon,
  Clock,
  Plus,
  Check,
  Trash2,
  Loader2,
  AlertCircle,
  MessageSquare,
  History,
  Send,
  FolderOpen,
  File,
  Download,
  ChevronRight,
  ExternalLink,
  Users,
  Sparkles,
  Phone,
  MapPin,
  FileSignature,
} from "lucide-react";
import { toast } from "sonner";
import { format, parseISO, isAfter } from "date-fns";
import { pt } from "date-fns/locale";

// eslint-disable-next-line no-undef
const API_URL = process.env.REACT_APP_BACKEND_URL || "";

const statusColors = {
  yellow: "bg-yellow-100 text-yellow-800 border-yellow-200",
  blue: "bg-blue-100 text-blue-800 border-blue-200",
  orange: "bg-orange-100 text-orange-800 border-orange-200",
  green: "bg-emerald-100 text-emerald-800 border-emerald-200",
  red: "bg-red-100 text-red-800 border-red-200",
  purple: "bg-purple-100 text-purple-800 border-purple-200",
};

const typeLabels = {
  credito: "Crédito",
  imobiliaria: "Imobiliária",
  ambos: "Crédito + Imobiliária",
};

// Função para validar NIF português
const validateNIF = (nif) => {
  if (!nif) return { valid: true, error: null };
  
  // Remover espaços e caracteres especiais
  const nifClean = nif.replace(/[^\d]/g, '');
  
  if (nifClean.length !== 9) {
    return { valid: false, error: `NIF deve ter 9 dígitos (tem ${nifClean.length})` };
  }
  
  if (!/^\d+$/.test(nifClean)) {
    return { valid: false, error: "NIF deve conter apenas dígitos" };
  }
  
  // NIFs que começam com 5 são de empresas
  if (nifClean.startsWith('5')) {
    return { valid: false, error: "NIF de empresa (começa por 5) não é permitido para clientes particulares" };
  }
  
  return { valid: true, error: null };
};

const ProcessDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [process, setProcess] = useState(null);
  const [deadlines, setDeadlines] = useState([]);
  const [activities, setActivities] = useState([]);
  const [history, setHistory] = useState([]);
  const [workflowStatuses, setWorkflowStatuses] = useState([]);
  const [oneDriveFiles, setOneDriveFiles] = useState([]);
  const [currentFolder, setCurrentFolder] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("personal");
  const [sideTab, setSideTab] = useState("deadlines");

  const [accessDenied, setAccessDenied] = useState(false);
  
  // Estado de erro de validação do NIF
  const [nifError, setNifError] = useState(null);

  // Form states
  const [personalData, setPersonalData] = useState({});
  const [financialData, setFinancialData] = useState({});
  const [realEstateData, setRealEstateData] = useState({});
  const [creditData, setCreditData] = useState({});
  const [status, setStatus] = useState("");

  // Activity state
  const [newComment, setNewComment] = useState("");
  const [sendingComment, setSendingComment] = useState(false);

  // Deadline dialog
  const [isDeadlineDialogOpen, setIsDeadlineDialogOpen] = useState(false);
  const [deadlineForm, setDeadlineForm] = useState({
    title: "",
    description: "",
    due_date: "",
    priority: "medium",
  });
  const [selectedDate, setSelectedDate] = useState(null);
  
  // Estado para atribuição de utilizadores
  const [showAssignDialog, setShowAssignDialog] = useState(false);
  const [appUsers, setAppUsers] = useState([]);
  const [selectedConsultor, setSelectedConsultor] = useState("");
  const [selectedMediador, setSelectedMediador] = useState("");
  const [savingAssignment, setSavingAssignment] = useState(false);

  // Buscar utilizadores
  const fetchUsers = async () => {
    try {
      const response = await fetch(`${API_URL}/api/admin/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const users = await response.json();
        setAppUsers(users.filter(u => u.is_active !== false));
      }
    } catch (error) {
      console.error("Erro ao buscar utilizadores:", error);
    }
  };

  // Abrir dialog de atribuição
  const openAssignDialog = () => {
    if (process) {
      setSelectedConsultor(process.assigned_consultor_id || "");
      setSelectedMediador(process.assigned_mediador_id || "");
      setShowAssignDialog(true);
      if (appUsers.length === 0) {
        fetchUsers();
      }
    }
  };

  // Guardar atribuições
  const handleSaveAssignment = async () => {
    setSavingAssignment(true);
    try {
      const params = new URLSearchParams();
      params.append("consultor_id", selectedConsultor || "");
      params.append("mediador_id", selectedMediador || "");
      
      const response = await fetch(`${API_URL}/api/processes/${id}/assign?${params.toString()}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success("Atribuições actualizadas com sucesso");
        setShowAssignDialog(false);
        fetchData();
      } else {
        const data = await response.json();
        toast.error(data.detail || "Erro ao actualizar atribuições");
      }
    } catch (error) {
      console.error("Erro ao guardar atribuições:", error);
      toast.error("Erro ao guardar atribuições");
    } finally {
      setSavingAssignment(false);
    }
  };

  // Handler para dados extraídos pela IA
  const handleAIDataExtracted = async ({ extractedData, mappedData, documentType }) => {
    console.log("Dados extraídos pela IA:", { extractedData, mappedData, documentType });
    
    let newPersonalData = { ...personalData };
    let newFinancialData = { ...financialData };
    let newRealEstateData = { ...realEstateData };
    let additionalData = {}; // Para campos extras como co_buyers, vendedor, etc.
    
    // Preencher campos com base no tipo de documento
    if (documentType === "cc") {
      // Dados pessoais do CC
      newPersonalData = {
        ...newPersonalData,
        nif: extractedData.nif || newPersonalData.nif,
        documento_id: extractedData.numero_documento || newPersonalData.documento_id,
        data_nascimento: extractedData.data_nascimento || newPersonalData.data_nascimento,
        data_validade_cc: extractedData.data_validade || newPersonalData.data_validade_cc,
        naturalidade: extractedData.naturalidade || newPersonalData.naturalidade,
        nacionalidade: extractedData.nacionalidade || newPersonalData.nacionalidade,
        sexo: extractedData.sexo || newPersonalData.sexo,
        nome_pai: extractedData.pai || newPersonalData.nome_pai,
        nome_mae: extractedData.mae || newPersonalData.nome_mae,
        altura: extractedData.altura || newPersonalData.altura,
      };
      setPersonalData(newPersonalData);
      
      // Actualizar nome do cliente se extraído
      if (extractedData.nome_completo && !process.client_name) {
        setProcess(prev => ({ ...prev, client_name: extractedData.nome_completo }));
      }
      
      setActiveTab("personal");
      
    } else if (documentType === "recibo_vencimento" || documentType === "irs") {
      // Dados financeiros
      newFinancialData = {
        ...newFinancialData,
        rendimento_mensal: extractedData.salario_liquido || extractedData.rendimento_liquido_mensal || newFinancialData.rendimento_mensal,
        rendimento_bruto: extractedData.salario_bruto || newFinancialData.rendimento_bruto,
        empresa: extractedData.empresa || newFinancialData.empresa,
        tipo_contrato: extractedData.tipo_contrato || newFinancialData.tipo_contrato,
        categoria_profissional: extractedData.categoria_profissional || newFinancialData.categoria_profissional,
      };
      setFinancialData(newFinancialData);
      setActiveTab("financial");
      
    } else if (documentType === "cpcv") {
      // CPCV - Contrato Promessa Compra e Venda
      // Dados do comprador principal
      const compradores = extractedData.compradores || mappedData?.compradores || [];
      if (compradores.length > 0) {
        const comprador1 = compradores[0];
        newPersonalData = {
          ...newPersonalData,
          nif: comprador1.nif || newPersonalData.nif,
          documento_id: comprador1.cc || newPersonalData.documento_id,
          estado_civil: comprador1.estado_civil || newPersonalData.estado_civil,
          profissao: comprador1.profissao || newPersonalData.profissao,
          morada: comprador1.morada || newPersonalData.morada,
          codigo_postal: comprador1.codigo_postal || newPersonalData.codigo_postal,
        };
        setPersonalData(newPersonalData);
        
        // Email e telefone do comprador
        if (comprador1.email) {
          additionalData.client_email = comprador1.email;
        }
        if (comprador1.telefone) {
          additionalData.client_phone = comprador1.telefone;
        }
        
        // Co-compradores (se houver mais que 1)
        if (compradores.length > 0) {
          additionalData.co_buyers = compradores;
        }
      }
      
      // Dados do vendedor
      const vendedor = extractedData.vendedor || mappedData?.vendedor || {};
      if (vendedor.nome || vendedor.nif) {
        additionalData.vendedor = vendedor;
      }
      
      // Dados do imóvel
      const imovel = extractedData.imovel || mappedData?.imovel || {};
      newRealEstateData = {
        ...newRealEstateData,
        localizacao: imovel.morada_completa || imovel.morada || newRealEstateData.localizacao,
        codigo_postal: imovel.codigo_postal || newRealEstateData.codigo_postal,
        localidade: imovel.localidade || newRealEstateData.localidade,
        freguesia: imovel.freguesia || newRealEstateData.freguesia,
        concelho: imovel.concelho || newRealEstateData.concelho,
        tipologia: imovel.tipologia || newRealEstateData.tipologia,
        area_bruta: imovel.area_bruta || newRealEstateData.area_bruta,
        area_util: imovel.area_util || newRealEstateData.area_util,
        fracao: imovel.fracao || newRealEstateData.fracao,
        artigo_matricial: imovel.artigo_matricial || newRealEstateData.artigo_matricial,
        conservatoria: imovel.conservatoria || newRealEstateData.conservatoria,
        numero_predial: imovel.numero_predial || newRealEstateData.numero_predial,
        certificado_energetico: imovel.certificado_energetico || newRealEstateData.certificado_energetico,
        estacionamento: imovel.estacionamento || newRealEstateData.estacionamento,
        arrecadacao: imovel.arrecadacao || newRealEstateData.arrecadacao,
        descricao_imovel: imovel.descricao || newRealEstateData.descricao_imovel,
      };
      setRealEstateData(newRealEstateData);
      
      // Valores do negócio
      const valores = extractedData.valores || mappedData?.valores || {};
      newFinancialData = {
        ...newFinancialData,
        valor_pretendido: valores.valor_financiamento || newFinancialData.valor_pretendido,
        valor_entrada: valores.sinal || newFinancialData.valor_entrada,
        data_sinal: valores.data_sinal || newFinancialData.data_sinal,
        reforco_sinal: valores.reforco_sinal || newFinancialData.reforco_sinal,
        comissao_mediacao: valores.comissao_mediacao || newFinancialData.comissao_mediacao,
      };
      newRealEstateData = {
        ...newRealEstateData,
        valor_imovel: valores.preco_total || newRealEstateData.valor_imovel,
      };
      setFinancialData(newFinancialData);
      setRealEstateData(newRealEstateData);
      
      // Datas do CPCV
      const datas = extractedData.datas || mappedData?.datas || {};
      newRealEstateData = {
        ...newRealEstateData,
        data_cpcv: datas.data_cpcv || newRealEstateData.data_cpcv,
        data_escritura_prevista: datas.data_escritura_prevista || newRealEstateData.data_escritura_prevista,
        prazo_escritura_dias: datas.prazo_escritura_dias || newRealEstateData.prazo_escritura_dias,
        data_entrega_chaves: datas.data_entrega_chaves || newRealEstateData.data_entrega_chaves,
      };
      setRealEstateData(newRealEstateData);
      
      // Mediador
      const mediador = extractedData.mediador || mappedData?.mediador || {};
      if (mediador.nome_empresa || mediador.licenca_ami) {
        additionalData.mediador = mediador;
      }
      
      // Condições
      const condicoes = extractedData.condicoes || mappedData?.condicoes || {};
      if (condicoes.condicao_suspensiva) {
        newRealEstateData.condicao_suspensiva = condicoes.condicao_suspensiva;
        setRealEstateData(newRealEstateData);
      }
      
      setActiveTab("real_estate");
      toast.info("Dados do CPCV extraídos!");
      
    } else if (documentType === "caderneta_predial") {
      // Dados do imóvel
      newRealEstateData = {
        ...newRealEstateData,
        artigo_matricial: extractedData.artigo_matricial || newRealEstateData.artigo_matricial,
        valor_patrimonial: extractedData.valor_patrimonial_tributario || newRealEstateData.valor_patrimonial,
        area: extractedData.area_bruta || newRealEstateData.area,
        localizacao: extractedData.localizacao || newRealEstateData.localizacao,
        tipologia: extractedData.tipologia || newRealEstateData.tipologia,
      };
      setRealEstateData(newRealEstateData);
      setActiveTab("real_estate");
      
    } else {
      // Documento genérico - tentar preencher o que conseguir
      if (extractedData.nif) {
        newPersonalData = { ...newPersonalData, nif: extractedData.nif };
        setPersonalData(newPersonalData);
      }
      if (extractedData.nome_completo) {
        newPersonalData = { ...newPersonalData, nome: extractedData.nome_completo };
        setPersonalData(newPersonalData);
      }
    }
    
    // GUARDAR AUTOMATICAMENTE no backend
    try {
      const updateData = {
        personal_data: newPersonalData,
        financial_data: newFinancialData,
        real_estate_data: newRealEstateData,
        ...additionalData, // Inclui co_buyers, vendedor, mediador, etc.
      };
      
      await updateProcess(id, updateData);
      toast.success("Dados extraídos e guardados automaticamente!");
      fetchData(); // Recarregar dados
    } catch (error) {
      console.error("Erro ao guardar dados extraídos:", error);
      toast.error("Dados extraídos mas falhou a guardar. Clique em Guardar manualmente.");
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      const [processRes, deadlinesRes, activitiesRes, historyRes, statusesRes] = await Promise.all([
        getProcess(id),
        getDeadlines(id),
        getActivities(id),
        getHistory(id),
        getWorkflowStatuses(),
      ]);
      const processData = processRes.data;
      setProcess(processData);
      setDeadlines(deadlinesRes.data);
      setActivities(activitiesRes.data);
      setHistory(historyRes.data);
      setWorkflowStatuses(statusesRes.data);
      setStatus(processData.status);
      setPersonalData(processData.personal_data || {});
      setFinancialData(processData.financial_data || {});
      setRealEstateData(processData.real_estate_data || {});
      setCreditData(processData.credit_data || {});

      // Try to load OneDrive files
      if (processData.client_name) {
        try {
          const filesRes = await getClientOneDriveFiles(processData.client_name, currentFolder);
          setOneDriveFiles(filesRes.data);
        } catch (e) {
          // OneDrive not configured or folder doesn't exist
          setOneDriveFiles([]);
        }
      }
    } catch (error) {
      console.error("Error fetching data:", error);
      if (error.response?.status === 403) {
        setAccessDenied(true);
        toast.error("Não tem permissão para aceder a este processo");
      } else {
        toast.error("Erro ao carregar dados do processo");
        navigate(-1);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadOneDriveFolder = async (subfolder = "") => {
    try {
      const filesRes = await getClientOneDriveFiles(process.client_name, subfolder);
      setOneDriveFiles(filesRes.data);
      setCurrentFolder(subfolder);
    } catch (e) {
      toast.error("Erro ao carregar pasta");
    }
  };

  const handleDownloadFile = async (fileId) => {
    try {
      const res = await getOneDriveDownloadUrl(fileId);
      window.open(res.data.download_url, "_blank");
    } catch (e) {
      toast.error("Erro ao obter link de download");
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updateData = {};

      // Sempre incluir email e telefone do cliente se foram alterados
      if (process?.client_email !== undefined) {
        updateData.client_email = process.client_email;
      }
      if (process?.client_phone !== undefined) {
        updateData.client_phone = process.client_phone;
      }

      if (user.role === "cliente" || user.role === "admin") {
        updateData.personal_data = personalData;
        updateData.financial_data = financialData;
      }

      if (user.role === "consultor" || user.role === "admin") {
        updateData.personal_data = personalData;
        updateData.financial_data = financialData;
        updateData.real_estate_data = realEstateData;
      }

      if (user.role === "mediador" || user.role === "admin") {
        updateData.personal_data = personalData;
        updateData.financial_data = financialData;
        const allowedStatuses = workflowStatuses.filter(s => s.order >= 3).map(s => s.name);
        if (allowedStatuses.includes(process.status) || process.status === "autorizacao_bancaria" || process.status === "aprovado") {
          updateData.credit_data = creditData;
        }
      }

      if (user.role !== "cliente" && status !== process.status) {
        updateData.status = status;
      }

      await updateProcess(id, updateData);
      toast.success("Processo atualizado com sucesso!");
      fetchData();
    } catch (error) {
      console.error("Error saving process:", error);
      toast.error(error.response?.data?.detail || "Erro ao guardar processo");
    } finally {
      setSaving(false);
    }
  };

  const handleSendComment = async () => {
    if (!newComment.trim()) return;

    setSendingComment(true);
    try {
      await createActivity({ process_id: id, comment: newComment });
      setNewComment("");
      const activitiesRes = await getActivities(id);
      setActivities(activitiesRes.data);
      toast.success("Comentário adicionado");
    } catch (error) {
      toast.error("Erro ao adicionar comentário");
    } finally {
      setSendingComment(false);
    }
  };

  const handleDeleteComment = async (activityId) => {
    try {
      await deleteActivity(activityId);
      const activitiesRes = await getActivities(id);
      setActivities(activitiesRes.data);
      toast.success("Comentário eliminado");
    } catch (error) {
      toast.error("Erro ao eliminar comentário");
    }
  };

  const handleCreateDeadline = async () => {
    if (!deadlineForm.title || !selectedDate) {
      toast.error("Preencha o título e a data");
      return;
    }

    try {
      await createDeadline({
        process_id: id,
        title: deadlineForm.title,
        description: deadlineForm.description,
        due_date: format(selectedDate, "yyyy-MM-dd"),
        priority: deadlineForm.priority,
      });
      toast.success("Prazo criado com sucesso!");
      setIsDeadlineDialogOpen(false);
      setDeadlineForm({ title: "", description: "", due_date: "", priority: "medium" });
      setSelectedDate(null);
      fetchData();
    } catch (error) {
      toast.error("Erro ao criar prazo");
    }
  };

  const handleToggleDeadline = async (deadline) => {
    try {
      await updateDeadline(deadline.id, { completed: !deadline.completed });
      fetchData();
    } catch (error) {
      toast.error("Erro ao atualizar prazo");
    }
  };

  const handleDeleteDeadline = async (deadlineId) => {
    if (!confirm("Tem certeza que deseja eliminar este prazo?")) return;

    try {
      await deleteDeadline(deadlineId);
      toast.success("Prazo eliminado!");
      fetchData();
    } catch (error) {
      toast.error("Erro ao eliminar prazo");
    }
  };

  const getStatusInfo = (statusName) => {
    const statusInfo = workflowStatuses.find(s => s.name === statusName);
    return statusInfo || { label: statusName, color: "blue" };
  };

  const canEditPersonal = ["cliente", "consultor", "mediador", "admin"].includes(user?.role);
  const canEditFinancial = ["cliente", "consultor", "mediador", "admin"].includes(user?.role);
  const canEditRealEstate = ["consultor", "admin"].includes(user?.role);
  const canEditCredit = ["mediador", "admin"].includes(user?.role) && 
    (workflowStatuses.filter(s => s.order >= 3).map(s => s.name).includes(process?.status) || 
     process?.status === "autorizacao_bancaria" || process?.status === "aprovado");
  const canChangeStatus = ["consultor", "mediador", "admin"].includes(user?.role);
  const canManageDeadlines = ["consultor", "mediador", "admin"].includes(user?.role);

  if (loading) {
    return (
      <DashboardLayout title="Detalhes do Processo">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }

  if (accessDenied) {
    return (
      <DashboardLayout title="Acesso Negado">
        <Card className="border-border">
          <CardContent className="p-8 text-center">
            <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
            <h2 className="text-xl font-semibold mb-2">Acesso Negado</h2>
            <p className="text-muted-foreground mb-4">
              Não tem permissão para aceder a este processo.
            </p>
            <p className="text-sm text-muted-foreground mb-6">
              Este processo não lhe está atribuído. Se acha que deveria ter acesso, contacte o administrador.
            </p>
            <Button onClick={() => navigate(-1)}>Voltar</Button>
          </CardContent>
        </Card>
      </DashboardLayout>
    );
  }

  if (!process) {
    return (
      <DashboardLayout title="Processo não encontrado">
        <Card className="border-border">
          <CardContent className="p-8 text-center">
            <AlertCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">Processo não encontrado</p>
            <Button className="mt-4" onClick={() => navigate(-1)}>Voltar</Button>
          </CardContent>
        </Card>
      </DashboardLayout>
    );
  }

  const deadlineDates = deadlines.map((d) => parseISO(d.due_date));
  const currentStatusInfo = getStatusInfo(process.status);

  return (
    <DashboardLayout title="Detalhes do Processo">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h2 className="text-xl font-semibold">{process.client_name}</h2>
              <p className="text-sm text-muted-foreground">
                #{process.process_number || '—'} • {typeLabels[process.process_type]}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge className={`${statusColors[currentStatusInfo.color]} border`}>
              {currentStatusInfo.label}
            </Badge>
            
            {/* Botão para Análise com IA */}
            <AIDocumentAnalyzer
              processId={id}
              clientName={process.client_name}
              onDataExtracted={handleAIDataExtracted}
            />
            
            {/* Botão para Gerir Atribuições */}
            <Button
              variant="outline"
              size="sm"
              className="text-purple-600 border-purple-200 hover:bg-purple-50"
              onClick={openAssignDialog}
              data-testid="assign-users-btn"
            >
              <Users className="h-4 w-4 mr-2" />
              Atribuições
            </Button>
            
            {canChangeStatus && (
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger className="w-48" data-testid="status-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {workflowStatuses.map((s) => (
                    <SelectItem key={s.id} value={s.name}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>

        {/* Alertas do Processo */}
        <ProcessAlerts processId={id} className="mb-2" />

        {/* Resumo do Processo */}
        <ProcessSummaryCard 
          process={process}
          statusInfo={currentStatusInfo}
          consultorName={process.assigned_consultor_name}
          mediadorName={process.assigned_mediador_name}
        />

        {/* Timeline do Processo */}
        <ProcessTimeline 
          processId={id}
          currentStatus={process.status}
          history={process.status_history || activities.filter(a => a.type === 'status_change')}
        />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="border-border">
              <CardHeader>
                <CardTitle className="text-lg">Dados do Processo</CardTitle>
              </CardHeader>
              <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="personal" className="gap-2">
                      <User className="h-4 w-4" />
                      <span className="hidden sm:inline">Pessoais</span>
                    </TabsTrigger>
                    <TabsTrigger value="financial" className="gap-2">
                      <Briefcase className="h-4 w-4" />
                      <span className="hidden sm:inline">Financeiros</span>
                    </TabsTrigger>
                    <TabsTrigger value="realestate" className="gap-2">
                      <Building2 className="h-4 w-4" />
                      <span className="hidden sm:inline">Imobiliário</span>
                    </TabsTrigger>
                    <TabsTrigger value="cpcv" className="gap-2">
                      <FileSignature className="h-4 w-4" />
                      <span className="hidden sm:inline">CPCV</span>
                    </TabsTrigger>
                    <TabsTrigger value="credit" className="gap-2">
                      <CreditCard className="h-4 w-4" />
                      <span className="hidden sm:inline">Crédito</span>
                    </TabsTrigger>
                  </TabsList>

                  {/* Personal Data Tab */}
                  <TabsContent value="personal" className="mt-4">
                    <div className="space-y-4">
                      {/* Contactos */}
                      <Card className="border-l-4 border-l-blue-500">
                        <CardContent className="pt-4">
                          <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                            <Phone className="h-4 w-4 text-blue-500" />
                            Contactos
                          </h4>
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Email</Label>
                              <Input
                                type="email"
                                value={process?.client_email || ""}
                                onChange={(e) => setProcess({ ...process, client_email: e.target.value })}
                                disabled={!canEditPersonal}
                                placeholder="email@exemplo.com"
                                className="h-9"
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Telefone</Label>
                              <Input
                                value={process?.client_phone || ""}
                                onChange={(e) => setProcess({ ...process, client_phone: e.target.value })}
                                disabled={!canEditPersonal}
                                placeholder="+351 000 000 000"
                                className="h-9"
                              />
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                      
                      {/* Identificação */}
                      <Card className="border-l-4 border-l-amber-500">
                        <CardContent className="pt-4">
                          <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                            <CreditCard className="h-4 w-4 text-amber-500" />
                            Identificação
                          </h4>
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">NIF</Label>
                              <Input
                                value={personalData.nif || ""}
                                onChange={(e) => setPersonalData({ ...personalData, nif: e.target.value })}
                                disabled={!canEditPersonal}
                                data-testid="personal-nif"
                                className="h-9"
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Nº Documento (CC)</Label>
                              <Input
                                value={personalData.documento_id || ""}
                                onChange={(e) => setPersonalData({ ...personalData, documento_id: e.target.value })}
                                disabled={!canEditPersonal}
                                className="h-9"
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Data de Nascimento</Label>
                              <Input
                                type="date"
                                value={personalData.data_nascimento || personalData.birth_date || ""}
                                onChange={(e) => setPersonalData({ ...personalData, data_nascimento: e.target.value })}
                                disabled={!canEditPersonal}
                                className="h-9"
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Validade CC</Label>
                              <Input
                                type="date"
                                value={personalData.data_validade_cc || ""}
                                onChange={(e) => setPersonalData({ ...personalData, data_validade_cc: e.target.value })}
                                disabled={!canEditPersonal}
                                className="h-9"
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Sexo</Label>
                              <Select
                                value={personalData.sexo || ""}
                                onValueChange={(value) => setPersonalData({ ...personalData, sexo: value })}
                                disabled={!canEditPersonal}
                              >
                                <SelectTrigger className="h-9"><SelectValue placeholder="Selecione" /></SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="M">Masculino</SelectItem>
                                  <SelectItem value="F">Feminino</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Naturalidade</Label>
                              <Input
                                value={personalData.naturalidade || ""}
                                onChange={(e) => setPersonalData({ ...personalData, naturalidade: e.target.value })}
                                disabled={!canEditPersonal}
                                className="h-9"
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Nacionalidade</Label>
                              <Input
                                value={personalData.nacionalidade || personalData.nationality || ""}
                                onChange={(e) => setPersonalData({ ...personalData, nacionalidade: e.target.value })}
                                disabled={!canEditPersonal}
                                className="h-9"
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Estado Civil</Label>
                              <Select
                                value={personalData.estado_civil || personalData.marital_status || ""}
                                onValueChange={(value) => setPersonalData({ ...personalData, estado_civil: value })}
                                disabled={!canEditPersonal}
                              >
                                <SelectTrigger className="h-9"><SelectValue placeholder="Selecione" /></SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="solteiro">Solteiro(a)</SelectItem>
                                  <SelectItem value="casado">Casado(a)</SelectItem>
                                  <SelectItem value="divorciado">Divorciado(a)</SelectItem>
                                  <SelectItem value="viuvo">Viúvo(a)</SelectItem>
                                  <SelectItem value="uniao_facto">União de Facto</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Altura (m)</Label>
                              <Input
                                value={personalData.altura || ""}
                                onChange={(e) => setPersonalData({ ...personalData, altura: e.target.value })}
                                disabled={!canEditPersonal}
                                className="h-9"
                              />
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                      
                      {/* Filiação */}
                      <Card className="border-l-4 border-l-orange-500">
                        <CardContent className="pt-4">
                          <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                            <Users className="h-4 w-4 text-orange-500" />
                            Filiação
                          </h4>
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Nome do Pai</Label>
                              <Input
                                value={personalData.nome_pai || ""}
                                onChange={(e) => setPersonalData({ ...personalData, nome_pai: e.target.value })}
                                disabled={!canEditPersonal}
                                className="h-9"
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Nome da Mãe</Label>
                              <Input
                                value={personalData.nome_mae || ""}
                                onChange={(e) => setPersonalData({ ...personalData, nome_mae: e.target.value })}
                                disabled={!canEditPersonal}
                                className="h-9"
                              />
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                      
                      {/* Morada */}
                      <Card className="border-l-4 border-l-teal-500">
                        <CardContent className="pt-4">
                          <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                            <MapPin className="h-4 w-4 text-teal-500" />
                            Morada
                          </h4>
                          <div className="space-y-1">
                            <Label className="text-xs text-muted-foreground">Morada Fiscal</Label>
                            <Input
                              value={personalData.morada_fiscal || personalData.address || ""}
                              onChange={(e) => setPersonalData({ ...personalData, morada_fiscal: e.target.value })}
                              disabled={!canEditPersonal}
                              className="h-9"
                            />
                          </div>
                        </CardContent>
                      </Card>
                      
                      {/* Co-Compradores / Co-Proponentes */}
                      {(process?.co_buyers?.length > 0 || process?.co_applicants?.length > 0) && (
                        <Card className="border-l-4 border-l-indigo-500">
                          <CardContent className="pt-4">
                            <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                              <Users className="h-4 w-4 text-indigo-500" />
                              Co-Compradores / Co-Proponentes
                              <Badge variant="secondary" className="ml-2">
                                {(process?.co_buyers?.length || 0) + (process?.co_applicants?.length || 0)} pessoa(s)
                              </Badge>
                            </h4>
                            <div className="space-y-3">
                              {/* Co-Buyers (do CPCV) */}
                              {process?.co_buyers?.map((buyer, index) => (
                                <div key={`buyer-${index}`} className="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
                                  <div className="flex items-center gap-2 mb-2">
                                    <Badge variant="outline" className="text-xs">
                                      Comprador {index + 1}
                                    </Badge>
                                    {buyer.estado_civil && (
                                      <Badge variant="secondary" className="text-xs">
                                        {buyer.estado_civil}
                                      </Badge>
                                    )}
                                  </div>
                                  <div className="grid grid-cols-2 gap-2 text-sm">
                                    {buyer.nome && (
                                      <div>
                                        <span className="text-muted-foreground text-xs">Nome:</span>
                                        <p className="font-medium">{buyer.nome}</p>
                                      </div>
                                    )}
                                    {buyer.nif && (
                                      <div>
                                        <span className="text-muted-foreground text-xs">NIF:</span>
                                        <p className="font-medium">{buyer.nif}</p>
                                      </div>
                                    )}
                                    {buyer.email && (
                                      <div>
                                        <span className="text-muted-foreground text-xs">Email:</span>
                                        <p className="font-medium">{buyer.email}</p>
                                      </div>
                                    )}
                                    {buyer.telefone && (
                                      <div>
                                        <span className="text-muted-foreground text-xs">Telefone:</span>
                                        <p className="font-medium">{buyer.telefone}</p>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ))}
                              
                              {/* Co-Applicants (do IRS/Simulação) */}
                              {process?.co_applicants?.map((applicant, index) => (
                                <div key={`applicant-${index}`} className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                                  <div className="flex items-center gap-2 mb-2">
                                    <Badge variant="outline" className="text-xs">
                                      {index === 0 ? "Titular" : "Cônjuge/Proponente " + (index + 1)}
                                    </Badge>
                                    {applicant.rendimento_mensal && (
                                      <Badge variant="secondary" className="text-xs">
                                        {applicant.rendimento_mensal}€/mês
                                      </Badge>
                                    )}
                                  </div>
                                  <div className="grid grid-cols-2 gap-2 text-sm">
                                    {applicant.nome && (
                                      <div>
                                        <span className="text-muted-foreground text-xs">Nome:</span>
                                        <p className="font-medium">{applicant.nome}</p>
                                      </div>
                                    )}
                                    {applicant.nif && (
                                      <div>
                                        <span className="text-muted-foreground text-xs">NIF:</span>
                                        <p className="font-medium">{applicant.nif}</p>
                                      </div>
                                    )}
                                    {applicant.data_nascimento && (
                                      <div>
                                        <span className="text-muted-foreground text-xs">Data Nascimento:</span>
                                        <p className="font-medium">{applicant.data_nascimento}</p>
                                      </div>
                                    )}
                                    {applicant.entidade_patronal && (
                                      <div>
                                        <span className="text-muted-foreground text-xs">Empresa:</span>
                                        <p className="font-medium">{applicant.entidade_patronal}</p>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ))}
                              
                              {/* Rendimento Agregado */}
                              {financialData?.rendimento_agregado && (
                                <div className="mt-3 p-2 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800">
                                  <p className="text-sm font-medium text-green-700 dark:text-green-400">
                                    Rendimento Agregado: {financialData.rendimento_agregado.toLocaleString('pt-PT')}€/mês
                                  </p>
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  </TabsContent>

                  {/* Financial Data Tab */}
                  <TabsContent value="financial" className="mt-4">
                    <div className="space-y-4">
                      {/* Rendimentos */}
                      <Card className="border-l-4 border-l-green-500">
                        <CardContent className="pt-4">
                          <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                            <Briefcase className="h-4 w-4 text-green-500" />
                            Rendimentos
                          </h4>
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Rendimento Mensal (€)</Label>
                              <Input
                                type="number"
                                value={financialData.monthly_income || ""}
                                onChange={(e) => setFinancialData({ ...financialData, monthly_income: parseFloat(e.target.value) || null })}
                                disabled={!canEditFinancial}
                                className="h-9"
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Outros Rendimentos (€)</Label>
                              <Input
                                type="number"
                                value={financialData.other_income || ""}
                                onChange={(e) => setFinancialData({ ...financialData, other_income: parseFloat(e.target.value) || null })}
                                disabled={!canEditFinancial}
                                className="h-9"
                              />
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                      
                      {/* Despesas */}
                      <Card className="border-l-4 border-l-red-500">
                        <CardContent className="pt-4">
                          <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                            <CreditCard className="h-4 w-4 text-red-500" />
                            Despesas
                          </h4>
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Despesas Mensais (€)</Label>
                              <Input
                                type="number"
                                value={financialData.monthly_expenses || ""}
                                onChange={(e) => setFinancialData({ ...financialData, monthly_expenses: parseFloat(e.target.value) || null })}
                                disabled={!canEditFinancial}
                                className="h-9"
                              />
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                      
                      {/* Emprego */}
                      <Card className="border-l-4 border-l-purple-500">
                        <CardContent className="pt-4">
                          <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                            <User className="h-4 w-4 text-purple-500" />
                            Situação Profissional
                          </h4>
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Tipo de Emprego</Label>
                              <Select
                                value={financialData.employment_type || ""}
                                onValueChange={(value) => setFinancialData({ ...financialData, employment_type: value })}
                                disabled={!canEditFinancial}
                              >
                                <SelectTrigger className="h-9"><SelectValue placeholder="Selecione" /></SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="efetivo">Contrato Efetivo</SelectItem>
                                  <SelectItem value="termo">Contrato a Termo</SelectItem>
                                  <SelectItem value="independente">Trabalhador Independente</SelectItem>
                                  <SelectItem value="empresario">Empresário</SelectItem>
                                  <SelectItem value="reformado">Reformado</SelectItem>
                                  <SelectItem value="desempregado">Desempregado</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">Tempo de Emprego</Label>
                              <Input
                                value={financialData.employment_duration || ""}
                                onChange={(e) => setFinancialData({ ...financialData, employment_duration: e.target.value })}
                                disabled={!canEditFinancial}
                                className="h-9"
                              />
                            </div>
                            <div className="space-y-1 col-span-2">
                              <Label className="text-xs text-muted-foreground">Entidade Empregadora</Label>
                              <Input
                                value={financialData.employer_name || ""}
                                onChange={(e) => setFinancialData({ ...financialData, employer_name: e.target.value })}
                                disabled={!canEditFinancial}
                                className="h-9"
                              />
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </TabsContent>

                  {/* Real Estate Tab */}
                  <TabsContent value="realestate" className="space-y-4 mt-4">
                    {!canEditRealEstate && !realEstateData?.tipo_imovel && !realEstateData?.property_type ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <Building2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>Dados imobiliários serão preenchidos pelo consultor</p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Tipo de Imóvel</Label>
                          <Select
                            value={realEstateData.tipo_imovel || realEstateData.property_type || ""}
                            onValueChange={(value) => setRealEstateData({ ...realEstateData, tipo_imovel: value })}
                            disabled={!canEditRealEstate}
                          >
                            <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="apartamento">Apartamento</SelectItem>
                              <SelectItem value="moradia">Moradia</SelectItem>
                              <SelectItem value="terreno">Terreno</SelectItem>
                              <SelectItem value="comercial">Espaço Comercial</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Localização Pretendida</Label>
                          <Input
                            value={realEstateData.localizacao || realEstateData.property_zone || ""}
                            onChange={(e) => setRealEstateData({ ...realEstateData, localizacao: e.target.value })}
                            disabled={!canEditRealEstate}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Área Pretendida (m²)</Label>
                          <Input
                            type="number"
                            value={realEstateData.desired_area || ""}
                            onChange={(e) => setRealEstateData({ ...realEstateData, desired_area: parseFloat(e.target.value) || null })}
                            disabled={!canEditRealEstate}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Orçamento Máximo (€)</Label>
                          <Input
                            type="number"
                            value={realEstateData.max_budget || ""}
                            onChange={(e) => setRealEstateData({ ...realEstateData, max_budget: parseFloat(e.target.value) || null })}
                            disabled={!canEditRealEstate}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Finalidade</Label>
                          <Select
                            value={realEstateData.property_purpose || ""}
                            onValueChange={(value) => setRealEstateData({ ...realEstateData, property_purpose: value })}
                            disabled={!canEditRealEstate}
                          >
                            <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="habitacao_propria">Habitação Própria</SelectItem>
                              <SelectItem value="investimento">Investimento</SelectItem>
                              <SelectItem value="arrendamento">Arrendamento</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2 md:col-span-2">
                          <Label>Notas</Label>
                          <Textarea
                            value={realEstateData.notes || ""}
                            onChange={(e) => setRealEstateData({ ...realEstateData, notes: e.target.value })}
                            disabled={!canEditRealEstate}
                          />
                        </div>
                        
                        {/* Dados do Proprietário */}
                        <div className="md:col-span-2 pt-4 border-t">
                          <h4 className="font-medium text-sm text-muted-foreground mb-4">Dados do Proprietário</h4>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="space-y-2">
                              <Label>Nome do Proprietário</Label>
                              <Input
                                value={realEstateData.owner_name || ""}
                                onChange={(e) => setRealEstateData({ ...realEstateData, owner_name: e.target.value })}
                                disabled={!canEditRealEstate}
                                placeholder="Nome completo"
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Email do Proprietário</Label>
                              <Input
                                type="email"
                                value={realEstateData.owner_email || ""}
                                onChange={(e) => setRealEstateData({ ...realEstateData, owner_email: e.target.value })}
                                disabled={!canEditRealEstate}
                                placeholder="email@exemplo.com"
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Telefone do Proprietário</Label>
                              <Input
                                value={realEstateData.owner_phone || ""}
                                onChange={(e) => setRealEstateData({ ...realEstateData, owner_phone: e.target.value })}
                                disabled={!canEditRealEstate}
                                placeholder="+351 000 000 000"
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </TabsContent>

                  {/* CPCV Tab */}
                  <TabsContent value="cpcv" className="space-y-4 mt-4">
                    <div className="space-y-6">
                      {/* Header CPCV */}
                      <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                          <FileSignature className="h-5 w-5 text-indigo-600" />
                          Contrato Promessa Compra e Venda
                        </h3>
                        {realEstateData?.data_cpcv && (
                          <Badge variant="secondary">
                            Data: {realEstateData.data_cpcv}
                          </Badge>
                        )}
                      </div>

                      {/* Dados do Imóvel do CPCV */}
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Building2 className="h-4 w-4" />
                            Dados do Imóvel
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">Valor do Imóvel</span>
                            <p className="font-semibold text-green-600">
                              {realEstateData?.valor_imovel ? `€${Number(realEstateData.valor_imovel).toLocaleString('pt-PT')}` : '-'}
                            </p>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Tipologia</span>
                            <p className="font-medium">{realEstateData?.tipologia || '-'}</p>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Área</span>
                            <p className="font-medium">{realEstateData?.area ? `${realEstateData.area} m²` : '-'}</p>
                          </div>
                          <div className="col-span-2 md:col-span-3">
                            <span className="text-muted-foreground">Morada</span>
                            <p className="font-medium">{realEstateData?.morada_imovel || realEstateData?.localizacao || '-'}</p>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Vendedor */}
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm flex items-center gap-2">
                            <User className="h-4 w-4" />
                            Vendedor
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">Nome</span>
                            <p className="font-medium">{process?.vendedor?.nome || '-'}</p>
                          </div>
                          <div>
                            <span className="text-muted-foreground">NIF</span>
                            <p className="font-medium">{process?.vendedor?.nif || '-'}</p>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Telefone</span>
                            <p className="font-medium">{process?.vendedor?.telefone || '-'}</p>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Email</span>
                            <p className="font-medium">{process?.vendedor?.email || '-'}</p>
                          </div>
                          <div className="col-span-2">
                            <span className="text-muted-foreground">Morada</span>
                            <p className="font-medium">{process?.vendedor?.morada || '-'}</p>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Compradores */}
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Users className="h-4 w-4" />
                            Compradores
                            <Badge variant="secondary" className="ml-2">
                              {(process?.co_buyers?.length || 0) + 1}
                            </Badge>
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          {/* Comprador Principal */}
                          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge>Comprador Principal</Badge>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-sm">
                              <div>
                                <span className="text-muted-foreground text-xs">Nome:</span>
                                <p className="font-medium">{process?.client_name || '-'}</p>
                              </div>
                              <div>
                                <span className="text-muted-foreground text-xs">NIF:</span>
                                <p className="font-medium">{personalData?.nif || '-'}</p>
                              </div>
                            </div>
                          </div>
                          
                          {/* Co-Compradores */}
                          {process?.co_buyers?.map((buyer, index) => (
                            <div key={index} className="p-3 bg-indigo-50 rounded-lg border border-indigo-200">
                              <div className="flex items-center gap-2 mb-2">
                                <Badge variant="outline">Comprador {index + 2}</Badge>
                                {buyer.estado_civil && (
                                  <Badge variant="secondary" className="text-xs">{buyer.estado_civil}</Badge>
                                )}
                              </div>
                              <div className="grid grid-cols-2 gap-2 text-sm">
                                <div>
                                  <span className="text-muted-foreground text-xs">Nome:</span>
                                  <p className="font-medium">{buyer.nome || '-'}</p>
                                </div>
                                <div>
                                  <span className="text-muted-foreground text-xs">NIF:</span>
                                  <p className="font-medium">{buyer.nif || '-'}</p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </CardContent>
                      </Card>

                      {/* Valores Financeiros do CPCV */}
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm flex items-center gap-2">
                            <CreditCard className="h-4 w-4" />
                            Valores e Datas
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">Valor da Entrada</span>
                            <p className="font-semibold text-amber-600">
                              {financialData?.valor_entrada ? `€${Number(financialData.valor_entrada).toLocaleString('pt-PT')}` : '-'}
                            </p>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Data do Sinal</span>
                            <p className="font-medium">{financialData?.data_sinal || '-'}</p>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Data CPCV</span>
                            <p className="font-medium">{realEstateData?.data_cpcv || '-'}</p>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Data Escritura Prevista</span>
                            <p className="font-medium">{realEstateData?.data_escritura_prevista || '-'}</p>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Valor Financiamento</span>
                            <p className="font-semibold text-blue-600">
                              {financialData?.valor_pretendido ? `€${Number(financialData.valor_pretendido).toLocaleString('pt-PT')}` : '-'}
                            </p>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Mediador */}
                      {process?.mediador && (
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm flex items-center gap-2">
                              <Briefcase className="h-4 w-4" />
                              Mediador
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-muted-foreground">Nome/Empresa</span>
                              <p className="font-medium">{process.mediador.nome || '-'}</p>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Licença AMI</span>
                              <p className="font-medium">{process.mediador.licenca_ami || '-'}</p>
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  </TabsContent>

                  {/* Credit Tab */}
                  <TabsContent value="credit" className="space-y-4 mt-4">
                    {!canEditCredit && !creditData?.requested_amount ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <CreditCard className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>Dados de crédito só podem ser preenchidos após autorização bancária</p>
                        <Badge className="mt-2">{currentStatusInfo.label}</Badge>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Valor do Empréstimo (€)</Label>
                          <Input
                            type="number"
                            value={creditData.requested_amount || ""}
                            onChange={(e) => setCreditData({ ...creditData, requested_amount: parseFloat(e.target.value) || null })}
                            disabled={!canEditCredit}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Prazo (anos)</Label>
                          <Input
                            type="number"
                            value={creditData.loan_term_years || ""}
                            onChange={(e) => setCreditData({ ...creditData, loan_term_years: parseInt(e.target.value) || null })}
                            disabled={!canEditCredit}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Taxa de Juro (%)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={creditData.interest_rate || ""}
                            onChange={(e) => setCreditData({ ...creditData, interest_rate: parseFloat(e.target.value) || null })}
                            disabled={!canEditCredit}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Prestação Mensal (€)</Label>
                          <Input
                            type="number"
                            value={creditData.monthly_payment || ""}
                            onChange={(e) => setCreditData({ ...creditData, monthly_payment: parseFloat(e.target.value) || null })}
                            disabled={!canEditCredit}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Banco</Label>
                          <Input
                            value={creditData.bank_name || ""}
                            onChange={(e) => setCreditData({ ...creditData, bank_name: e.target.value })}
                            disabled={!canEditCredit}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Data de Aprovação</Label>
                          <Input
                            type="date"
                            value={creditData.bank_approval_date || ""}
                            onChange={(e) => setCreditData({ ...creditData, bank_approval_date: e.target.value })}
                            disabled={!canEditCredit}
                          />
                        </div>
                        <div className="space-y-2 md:col-span-2">
                          <Label>Notas da Aprovação</Label>
                          <Textarea
                            value={creditData.bank_approval_notes || ""}
                            onChange={(e) => setCreditData({ ...creditData, bank_approval_notes: e.target.value })}
                            disabled={!canEditCredit}
                          />
                        </div>
                      </div>
                    )}
                  </TabsContent>
                </Tabs>

                {/* Notas extraídas por IA */}
                {process.ai_extracted_notes && (
                  <Card className="mt-6 border-purple-200 bg-purple-50/50">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2 text-purple-700">
                        <Sparkles className="h-4 w-4" />
                        Dados Extraídos por IA
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs whitespace-pre-wrap text-gray-700 bg-white p-3 rounded border max-h-[200px] overflow-y-auto">
                        {process.ai_extracted_notes}
                      </pre>
                    </CardContent>
                  </Card>
                )}

                <Separator className="my-6" />

                <div className="flex justify-end">
                  <Button onClick={handleSave} disabled={saving} data-testid="save-process-btn">
                    {saving ? (
                      <><Loader2 className="h-4 w-4 mr-2 animate-spin" />A guardar...</>
                    ) : (
                      "Guardar Alterações"
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar - Organizada com Accordions */}
          <div className="space-y-3">
            {/* Activity Section */}
            <Card className="border-border">
              <CardHeader className="pb-2 py-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Atividade
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0 pb-3">
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <Textarea
                      placeholder="Adicionar comentário..."
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      className="flex-1 min-h-[50px] text-sm resize-none"
                      data-testid="new-comment-input"
                    />
                    <Button
                      onClick={handleSendComment}
                      disabled={sendingComment || !newComment.trim()}
                      size="sm"
                      data-testid="send-comment-btn"
                    >
                      {sendingComment ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    </Button>
                  </div>
                  <ScrollArea className="h-[120px]">
                    <div className="space-y-1.5 pr-2">
                      {activities.length === 0 ? (
                        <p className="text-center text-muted-foreground py-2 text-xs">Sem comentários</p>
                      ) : (
                        activities.slice(0, 5).map((activity) => (
                          <div key={activity.id} className="p-1.5 bg-muted/50 rounded text-xs" data-testid={`activity-${activity.id}`}>
                            <div className="flex items-start justify-between gap-1">
                              <div className="flex-1 min-w-0">
                                <span className="font-medium">{activity.user_name}</span>
                                {activity.source === 'trello' && <Badge variant="outline" className="ml-1 text-[9px] px-1 py-0">trello</Badge>}
                                <p className="text-[11px] mt-0.5 text-muted-foreground line-clamp-2">{activity.comment}</p>
                                <p className="text-[10px] text-muted-foreground">{format(parseISO(activity.created_at), "dd/MM HH:mm", { locale: pt })}</p>
                              </div>
                              {(activity.user_id === user.id || user.role === "admin") && (
                                <Button variant="ghost" size="icon" className="h-5 w-5 shrink-0" onClick={() => handleDeleteComment(activity.id)}>
                                  <Trash2 className="h-3 w-3 text-destructive" />
                                </Button>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </ScrollArea>
                </div>
              </CardContent>
            </Card>

            {/* Accordion para agrupar painéis secundários */}
            <Accordion type="multiple" defaultValue={["tasks"]} className="space-y-2">
              {/* Tarefas */}
              <AccordionItem value="tasks" className="border rounded-lg">
                <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                  <span className="flex items-center gap-2">
                    <Check className="h-4 w-4" />
                    Tarefas
                  </span>
                </AccordionTrigger>
                <AccordionContent className="px-3 pb-3">
                  <TasksPanel 
                    processId={id} 
                    processName={process.client_name}
                    compact={true}
                    maxHeight="150px"
                  />
                </AccordionContent>
              </AccordionItem>

              {/* Match Imóveis */}
              <AccordionItem value="match" className="border rounded-lg">
                <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                  <span className="flex items-center gap-2">
                    <Building2 className="h-4 w-4" />
                    Imóveis Compatíveis
                  </span>
                </AccordionTrigger>
                <AccordionContent className="px-3 pb-3">
                  <ClientPropertyMatch 
                    processId={id}
                    clientName={process?.client_name}
                  />
                </AccordionContent>
              </AccordionItem>

              {/* Documentos OneDrive */}
              <AccordionItem value="docs" className="border rounded-lg">
                <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                  <span className="flex items-center gap-2">
                    <FolderOpen className="h-4 w-4" />
                    Checklist Documentos
                  </span>
                </AccordionTrigger>
                <AccordionContent className="px-3 pb-3">
                  <DocumentChecklist 
                    processId={id}
                    clientName={process?.client_name}
                  />
                </AccordionContent>
              </AccordionItem>

              {/* Emails */}
              <AccordionItem value="emails" className="border rounded-lg">
                <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                  <span className="flex items-center gap-2">
                    <Send className="h-4 w-4" />
                    Histórico de Emails
                  </span>
                </AccordionTrigger>
                <AccordionContent className="px-3 pb-3">
                  <EmailHistoryPanel 
                    processId={id}
                    clientEmail={process?.client_email}
                    clientName={process?.client_name}
                    compact={true}
                    maxHeight="200px"
                  />
                </AccordionContent>
              </AccordionItem>
            </Accordion>

            {/* Side Tabs - Prazos, Histórico, Ficheiros */}
            <Card className="border-border">
              <CardContent className="p-0">
                <Tabs value={sideTab} onValueChange={setSideTab}>
                  <TabsList className="w-full grid grid-cols-3 rounded-none rounded-t-md h-9">
                    <TabsTrigger value="deadlines" className="gap-1 text-xs">
                      <Clock className="h-3 w-3" />
                      Prazos
                    </TabsTrigger>
                    <TabsTrigger value="history" className="gap-1 text-xs">
                      <History className="h-3 w-3" />
                      Histórico
                    </TabsTrigger>
                    <TabsTrigger value="files" className="gap-1 text-xs">
                      <FolderOpen className="h-3 w-3" />
                      Ficheiros
                    </TabsTrigger>
                  </TabsList>

                  {/* Deadlines Tab */}
                  <TabsContent value="deadlines" className="p-4 pt-2">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-medium">Prazos</h3>
                      {canManageDeadlines && (
                        <Dialog open={isDeadlineDialogOpen} onOpenChange={setIsDeadlineDialogOpen}>
                          <DialogTrigger asChild>
                            <Button size="sm" variant="outline" data-testid="add-deadline-btn">
                              <Plus className="h-4 w-4" />
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Novo Prazo</DialogTitle>
                            </DialogHeader>
                            <div className="space-y-4">
                              <div className="space-y-2">
                                <Label>Título</Label>
                                <Input
                                  value={deadlineForm.title}
                                  onChange={(e) => setDeadlineForm({ ...deadlineForm, title: e.target.value })}
                                  placeholder="Ex: Entregar documentos"
                                />
                              </div>
                              <div className="space-y-2">
                                <Label>Descrição</Label>
                                <Textarea
                                  value={deadlineForm.description}
                                  onChange={(e) => setDeadlineForm({ ...deadlineForm, description: e.target.value })}
                                />
                              </div>
                              <div className="space-y-2">
                                <Label>Data Limite</Label>
                                <Popover>
                                  <PopoverTrigger asChild>
                                    <Button variant="outline" className="w-full justify-start text-left font-normal">
                                      <CalendarIcon className="mr-2 h-4 w-4" />
                                      {selectedDate ? format(selectedDate, "PPP", { locale: pt }) : "Selecione"}
                                    </Button>
                                  </PopoverTrigger>
                                  <PopoverContent className="w-auto p-0">
                                    <Calendar mode="single" selected={selectedDate} onSelect={setSelectedDate} locale={pt} />
                                  </PopoverContent>
                                </Popover>
                              </div>
                              <div className="space-y-2">
                                <Label>Prioridade</Label>
                                <Select
                                  value={deadlineForm.priority}
                                  onValueChange={(value) => setDeadlineForm({ ...deadlineForm, priority: value })}
                                >
                                  <SelectTrigger><SelectValue /></SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="low">Baixa</SelectItem>
                                    <SelectItem value="medium">Média</SelectItem>
                                    <SelectItem value="high">Alta</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>
                            <DialogFooter>
                              <Button onClick={handleCreateDeadline}>Criar Prazo</Button>
                            </DialogFooter>
                          </DialogContent>
                        </Dialog>
                      )}
                    </div>

                    <Calendar
                      mode="single"
                      selected={selectedDate}
                      locale={pt}
                      modifiers={{ deadline: deadlineDates }}
                      modifiersStyles={{
                        deadline: { backgroundColor: "hsl(var(--primary))", color: "white", borderRadius: "4px" },
                      }}
                      className="rounded-md border mb-4"
                    />

                    <ScrollArea className="h-[200px]">
                      {deadlines.length === 0 ? (
                        <p className="text-center text-muted-foreground text-sm py-4">Sem prazos</p>
                      ) : (
                        <div className="space-y-2">
                          {deadlines.map((deadline) => (
                            <div
                              key={deadline.id}
                              className={`flex items-center justify-between p-2 rounded-md ${deadline.completed ? "bg-muted/30" : "bg-muted/50"}`}
                            >
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => handleToggleDeadline(deadline)}
                                  className={`h-4 w-4 rounded border flex items-center justify-center ${
                                    deadline.completed ? "bg-emerald-500 border-emerald-500 text-white" : "border-slate-300"
                                  }`}
                                  disabled={!canManageDeadlines}
                                >
                                  {deadline.completed && <Check className="h-3 w-3" />}
                                </button>
                                <div>
                                  <p className={`text-sm ${deadline.completed ? "line-through text-muted-foreground" : ""}`}>
                                    {deadline.title}
                                  </p>
                                  <p className="text-xs text-muted-foreground font-mono">
                                    {format(parseISO(deadline.due_date), "dd/MM/yyyy")}
                                  </p>
                                </div>
                              </div>
                              {canManageDeadlines && (
                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handleDeleteDeadline(deadline.id)}>
                                  <Trash2 className="h-3 w-3 text-destructive" />
                                </Button>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </ScrollArea>
                  </TabsContent>

                  {/* History Tab */}
                  <TabsContent value="history" className="p-4 pt-2">
                    <h3 className="font-medium mb-4">Histórico de Alterações</h3>
                    <ScrollArea className="h-[400px]">
                      {history.length === 0 ? (
                        <p className="text-center text-muted-foreground text-sm py-4">Sem histórico</p>
                      ) : (
                        <div className="space-y-3">
                          {history.map((entry) => (
                            <div key={entry.id} className="border-l-2 border-primary/30 pl-3 py-1">
                              <p className="text-sm font-medium">{entry.action}</p>
                              {entry.field && (
                                <p className="text-xs text-muted-foreground">
                                  {entry.field}: {entry.old_value || "vazio"} → {entry.new_value}
                                </p>
                              )}
                              <p className="text-xs text-muted-foreground">
                                {entry.user_name} • {format(parseISO(entry.created_at), "dd/MM HH:mm", { locale: pt })}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </ScrollArea>
                  </TabsContent>

                  {/* Files Tab (OneDrive Links) */}
                  <TabsContent value="files" className="p-4 pt-2">
                    <OneDriveLinks processId={id} clientName={process?.client_name} />
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
      
      {/* Dialog para atribuir utilizadores */}
      <Dialog open={showAssignDialog} onOpenChange={setShowAssignDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-purple-600" />
              Gerir Atribuições
            </DialogTitle>
            <DialogDescription>
              Seleccione os utilizadores a atribuir a este processo.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="font-medium">{process?.client_name}</p>
              <p className="text-sm text-muted-foreground">
                #{process?.process_number || '—'}
              </p>
            </div>
            
            <div className="space-y-3">
              <div>
                <Label className="text-sm font-medium">Consultor</Label>
                <Select value={selectedConsultor || "none"} onValueChange={(v) => setSelectedConsultor(v === "none" ? "" : v)}>
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="Seleccionar consultor..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Nenhum</SelectItem>
                    {appUsers
                      .filter(u => ["consultor", "diretor", "admin", "ceo"].includes(u.role))
                      .map(u => (
                        <SelectItem key={u.id} value={u.id}>
                          {u.name} ({u.role})
                        </SelectItem>
                      ))
                    }
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label className="text-sm font-medium">Intermediário / Mediador</Label>
                <Select value={selectedMediador || "none"} onValueChange={(v) => setSelectedMediador(v === "none" ? "" : v)}>
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="Seleccionar intermediário..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Nenhum</SelectItem>
                    {appUsers
                      .filter(u => ["mediador", "intermediario", "intermediario_credito", "diretor"].includes(u.role))
                      .map(u => (
                        <SelectItem key={u.id} value={u.id}>
                          {u.name} ({u.role})
                        </SelectItem>
                      ))
                    }
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setShowAssignDialog(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSaveAssignment}
              disabled={savingAssignment}
              className="bg-purple-600 hover:bg-purple-700"
            >
              {savingAssignment ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  A guardar...
                </>
              ) : (
                "Guardar"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
};

export default ProcessDetails;
