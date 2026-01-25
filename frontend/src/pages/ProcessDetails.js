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
} from "lucide-react";
import { toast } from "sonner";
import { format, parseISO, isAfter } from "date-fns";
import { pt } from "date-fns/locale";

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

const ProcessDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
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
      toast.error("Erro ao carregar dados do processo");
      navigate(-1);
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
              <p className="text-sm text-muted-foreground font-mono">
                {process.id.slice(0, 8)}... • {typeLabels[process.process_type]}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge className={`${statusColors[currentStatusInfo.color]} border`}>
              {currentStatusInfo.label}
            </Badge>
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
                    <TabsTrigger value="credit" className="gap-2">
                      <CreditCard className="h-4 w-4" />
                      <span className="hidden sm:inline">Crédito</span>
                    </TabsTrigger>
                  </TabsList>

                  {/* Personal Data Tab */}
                  <TabsContent value="personal" className="space-y-4 mt-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>NIF</Label>
                        <Input
                          value={personalData.nif || ""}
                          onChange={(e) => setPersonalData({ ...personalData, nif: e.target.value })}
                          disabled={!canEditPersonal}
                          data-testid="personal-nif"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Data de Nascimento</Label>
                        <Input
                          type="date"
                          value={personalData.birth_date || ""}
                          onChange={(e) => setPersonalData({ ...personalData, birth_date: e.target.value })}
                          disabled={!canEditPersonal}
                        />
                      </div>
                      <div className="space-y-2 md:col-span-2">
                        <Label>Morada Fiscal</Label>
                        <Input
                          value={personalData.morada_fiscal || personalData.address || ""}
                          onChange={(e) => setPersonalData({ ...personalData, morada_fiscal: e.target.value })}
                          disabled={!canEditPersonal}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Estado Civil</Label>
                        <Select
                          value={personalData.estado_civil || personalData.marital_status || ""}
                          onValueChange={(value) => setPersonalData({ ...personalData, estado_civil: value })}
                          disabled={!canEditPersonal}
                        >
                          <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="solteiro">Solteiro(a)</SelectItem>
                            <SelectItem value="casado">Casado(a)</SelectItem>
                            <SelectItem value="divorciado">Divorciado(a)</SelectItem>
                            <SelectItem value="viuvo">Viúvo(a)</SelectItem>
                            <SelectItem value="uniao_facto">União de Facto</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Nacionalidade</Label>
                        <Input
                          value={personalData.nacionalidade || personalData.nationality || ""}
                          onChange={(e) => setPersonalData({ ...personalData, nacionalidade: e.target.value })}
                          disabled={!canEditPersonal}
                        />
                      </div>
                    </div>
                  </TabsContent>

                  {/* Financial Data Tab */}
                  <TabsContent value="financial" className="space-y-4 mt-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Rendimento Mensal (€)</Label>
                        <Input
                          type="number"
                          value={financialData.monthly_income || ""}
                          onChange={(e) => setFinancialData({ ...financialData, monthly_income: parseFloat(e.target.value) || null })}
                          disabled={!canEditFinancial}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Outros Rendimentos (€)</Label>
                        <Input
                          type="number"
                          value={financialData.other_income || ""}
                          onChange={(e) => setFinancialData({ ...financialData, other_income: parseFloat(e.target.value) || null })}
                          disabled={!canEditFinancial}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Despesas Mensais (€)</Label>
                        <Input
                          type="number"
                          value={financialData.monthly_expenses || ""}
                          onChange={(e) => setFinancialData({ ...financialData, monthly_expenses: parseFloat(e.target.value) || null })}
                          disabled={!canEditFinancial}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Tipo de Emprego</Label>
                        <Select
                          value={financialData.employment_type || ""}
                          onValueChange={(value) => setFinancialData({ ...financialData, employment_type: value })}
                          disabled={!canEditFinancial}
                        >
                          <SelectTrigger><SelectValue placeholder="Selecione" /></SelectTrigger>
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
                      <div className="space-y-2">
                        <Label>Entidade Empregadora</Label>
                        <Input
                          value={financialData.employer_name || ""}
                          onChange={(e) => setFinancialData({ ...financialData, employer_name: e.target.value })}
                          disabled={!canEditFinancial}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Tempo de Emprego</Label>
                        <Input
                          value={financialData.employment_duration || ""}
                          onChange={(e) => setFinancialData({ ...financialData, employment_duration: e.target.value })}
                          disabled={!canEditFinancial}
                        />
                      </div>
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
                      </div>
                    )}
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

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Activity Section - Moved to top of sidebar */}
            <Card className="border-border">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Atividade
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-3">
                  {/* New Comment Input */}
                  <div className="flex gap-2">
                    <Textarea
                      placeholder="Adicionar comentário..."
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      className="flex-1 min-h-[60px] text-sm"
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

                  {/* Comments List */}
                  <ScrollArea className="h-[200px]">
                    <div className="space-y-2">
                      {activities.length === 0 ? (
                        <p className="text-center text-muted-foreground py-4 text-sm">Sem comentários</p>
                      ) : (
                        activities.map((activity) => (
                          <div key={activity.id} className="p-2 bg-muted/50 rounded-md text-sm" data-testid={`activity-${activity.id}`}>
                            <div className="flex items-start justify-between">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1 flex-wrap">
                                  <span className="font-medium text-xs">{activity.user_name}</span>
                                  <Badge variant="outline" className="text-[10px] px-1 py-0">{activity.user_role}</Badge>
                                </div>
                                <p className="text-xs mt-1">{activity.comment}</p>
                                <p className="text-[10px] text-muted-foreground mt-1">
                                  {format(parseISO(activity.created_at), "dd/MM HH:mm", { locale: pt })}
                                </p>
                              </div>
                              {(activity.user_id === user.id || user.role === "admin") && (
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6 shrink-0"
                                  onClick={() => handleDeleteComment(activity.id)}
                                >
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

            {/* Tasks Panel */}
            <TasksPanel 
              processId={id} 
              processName={process.client_name}
              compact={true}
              maxHeight="250px"
            />

            {/* Side Tabs */}
            <Card className="border-border">
              <CardContent className="p-0">
                <Tabs value={sideTab} onValueChange={setSideTab}>
                  <TabsList className="w-full grid grid-cols-3 rounded-none rounded-t-md">
                    <TabsTrigger value="deadlines" className="gap-1">
                      <Clock className="h-4 w-4" />
                      <span className="hidden sm:inline">Prazos</span>
                    </TabsTrigger>
                    <TabsTrigger value="history" className="gap-1">
                      <History className="h-4 w-4" />
                      <span className="hidden sm:inline">Histórico</span>
                    </TabsTrigger>
                    <TabsTrigger value="files" className="gap-1">
                      <FolderOpen className="h-4 w-4" />
                      <span className="hidden sm:inline">Ficheiros</span>
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
    </DashboardLayout>
  );
};

export default ProcessDetails;
