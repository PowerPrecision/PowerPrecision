import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Calendar } from "../components/ui/calendar";
import { Textarea } from "../components/ui/textarea";
import { Checkbox } from "../components/ui/checkbox";
import { useAuth } from "../contexts/AuthContext";
import { 
  Users, Settings, Plus, Edit, Trash2, Search, UserPlus, GitBranch, FolderOpen, 
  Loader2, CheckCircle, XCircle, FileText, Calendar as CalendarIcon, Filter, Eye, Sparkles,
  UserX, UserCheck, LayoutGrid
} from "lucide-react";
import { toast } from "sonner";
import { 
  getStats, getUsers, createUser, updateUser, deleteUser,
  getWorkflowStatuses, createWorkflowStatus, updateWorkflowStatus, deleteWorkflowStatus,
  getOneDriveStatus, getProcesses, getCalendarDeadlines, createDeadline, deleteDeadline,
  getUpcomingExpiries, analyzeDocument
} from "../services/api";
import KanbanBoard from "../components/KanbanBoard";

const roleLabels = { admin: "Administrador", ceo: "CEO", consultor: "Consultor", mediador: "Intermediário de Crédito", intermediario: "Intermediário de Crédito", consultor_mediador: "Consultor/Intermediário", consultor_intermediario: "Consultor/Intermediário", cliente: "Cliente" };
const roleColors = {
  admin: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  consultor: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  mediador: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400",
  cliente: "bg-gray-100 text-gray-800 dark:bg-gray-800/30 dark:text-gray-400",
};

const statusColorOptions = [
  { value: "yellow", label: "Amarelo", class: "bg-yellow-100 text-yellow-800" },
  { value: "blue", label: "Azul", class: "bg-blue-100 text-blue-800" },
  { value: "orange", label: "Laranja", class: "bg-orange-100 text-orange-800" },
  { value: "green", label: "Verde", class: "bg-green-100 text-green-800" },
  { value: "red", label: "Vermelho", class: "bg-red-100 text-red-800" },
  { value: "purple", label: "Roxo", class: "bg-purple-100 text-purple-800" },
];

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({});
  const [users, setUsers] = useState([]);
  const [processes, setProcesses] = useState([]);
  const [workflowStatuses, setWorkflowStatuses] = useState([]);
  const [oneDriveStatus, setOneDriveStatus] = useState(null);
  const [calendarDeadlines, setCalendarDeadlines] = useState([]);
  const [upcomingExpiries, setUpcomingExpiries] = useState([]);
  
  const [activeTab, setActiveTab] = useState("overview");
  const [searchTerm, setSearchTerm] = useState("");
  const [userSearchTerm, setUserSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [consultorFilter, setConsultorFilter] = useState("all");
  const [mediadorFilter, setMediadorFilter] = useState("all");
  const [selectedDate, setSelectedDate] = useState(new Date());
  
  // Dialogs
  const [isCreateUserDialogOpen, setIsCreateUserDialogOpen] = useState(false);
  const [isEditUserDialogOpen, setIsEditUserDialogOpen] = useState(false);
  const [isCreateStatusDialogOpen, setIsCreateStatusDialogOpen] = useState(false);
  const [isEditStatusDialogOpen, setIsEditStatusDialogOpen] = useState(false);
  const [isCreateEventDialogOpen, setIsCreateEventDialogOpen] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  
  // Form data
  const [userFormData, setUserFormData] = useState({ name: "", email: "", password: "", phone: "", role: "cliente", onedrive_folder: "" });
  const [statusFormData, setStatusFormData] = useState({ name: "", label: "", order: 1, color: "blue", description: "" });
  const [eventFormData, setEventFormData] = useState({ 
    title: "", 
    description: "", 
    due_date: "", 
    priority: "medium",
    process_id: "",
    assigned_user_ids: []  // Lista de utilizadores atribuídos
  });
  const [editingUserId, setEditingUserId] = useState(null);
  const [editingStatusId, setEditingStatusId] = useState(null);

  // Get all staff users for assignment
  const staffUsers = useMemo(() => users.filter(u => u.role !== "cliente"), [users]);
  // Get consultors and intermediários for filters
  const consultors = useMemo(() => users.filter(u => u.role === "consultor" || u.role === "consultor_mediador" || u.role === "consultor_intermediario" || u.role === "ceo"), [users]);
  const intermediarios = useMemo(() => users.filter(u => u.role === "mediador" || u.role === "intermediario" || u.role === "consultor_mediador" || u.role === "consultor_intermediario"), [users]);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    fetchCalendarData();
  }, [consultorFilter, mediadorFilter]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsRes, usersRes, processesRes, statusesRes, oneDriveRes, expiriesRes] = await Promise.all([
        getStats(),
        getUsers(),
        getProcesses(),
        getWorkflowStatuses(),
        getOneDriveStatus().catch(() => ({ data: { configured: false } })),
        getUpcomingExpiries(60).catch(() => ({ data: [] })),
      ]);
      setStats(statsRes.data);
      setUsers(usersRes.data);
      setProcesses(processesRes.data);
      setWorkflowStatuses(statusesRes.data);
      setOneDriveStatus(oneDriveRes.data);
      setUpcomingExpiries(expiriesRes.data);
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  };

  const fetchCalendarData = async () => {
    try {
      const res = await getCalendarDeadlines(
        consultorFilter !== "all" ? consultorFilter : null,
        mediadorFilter !== "all" ? mediadorFilter : null
      );
      setCalendarDeadlines(res.data);
    } catch (error) {
      console.error("Error fetching calendar data:", error);
    }
  };

  const filteredUsers = useMemo(() => {
    return users.filter(user => {
      const matchesSearch = user.name.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
                           user.email.toLowerCase().includes(userSearchTerm.toLowerCase());
      const matchesRole = roleFilter === "all" || user.role === roleFilter;
      return matchesSearch && matchesRole;
    });
  }, [users, userSearchTerm, roleFilter]);

  const filteredProcesses = useMemo(() => {
    return processes.filter(process => {
      const matchesConsultor = consultorFilter === "all" || process.assigned_consultor_id === consultorFilter;
      const matchesMediador = mediadorFilter === "all" || process.assigned_mediador_id === mediadorFilter;
      return matchesConsultor && matchesMediador;
    });
  }, [processes, consultorFilter, mediadorFilter]);

  // Get deadlines for selected date
  const deadlinesForDate = useMemo(() => {
    const dateStr = selectedDate.toISOString().split('T')[0];
    return calendarDeadlines.filter(d => d.due_date === dateStr);
  }, [calendarDeadlines, selectedDate]);

  // Get dates with deadlines for calendar highlighting
  const datesWithDeadlines = useMemo(() => {
    return calendarDeadlines.map(d => new Date(d.due_date));
  }, [calendarDeadlines]);

  const getColorClass = (color) => {
    const colorOption = statusColorOptions.find(c => c.value === color);
    return colorOption ? colorOption.class : "bg-gray-100 text-gray-800";
  };

  // User handlers
  const handleCreateUser = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      await createUser(userFormData);
      toast.success("Utilizador criado com sucesso");
      setIsCreateUserDialogOpen(false);
      setUserFormData({ name: "", email: "", password: "", phone: "", role: "cliente", onedrive_folder: "" });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao criar utilizador");
    } finally {
      setFormLoading(false);
    }
  };

  const openEditUserDialog = (user) => {
    setEditingUserId(user.id);
    setUserFormData({ name: user.name, email: user.email, phone: user.phone || "", role: user.role, onedrive_folder: user.onedrive_folder || "" });
    setIsEditUserDialogOpen(true);
  };

  const handleEditUser = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      await updateUser(editingUserId, { name: userFormData.name, phone: userFormData.phone, role: userFormData.role, onedrive_folder: userFormData.onedrive_folder });
      toast.success("Utilizador atualizado");
      setIsEditUserDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao atualizar utilizador");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm("Tem a certeza que deseja eliminar este utilizador?")) return;
    try {
      await deleteUser(userId);
      toast.success("Utilizador eliminado");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao eliminar utilizador");
    }
  };

  const handleToggleUserStatus = async (userId, currentStatus) => {
    try {
      await updateUser(userId, { is_active: !currentStatus });
      toast.success(`Utilizador ${!currentStatus ? 'ativado' : 'desativado'} com sucesso`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao atualizar utilizador");
    }
  };


  // Status handlers
  const handleCreateStatus = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      await createWorkflowStatus(statusFormData);
      toast.success("Estado criado com sucesso");
      setIsCreateStatusDialogOpen(false);
      setStatusFormData({ name: "", label: "", order: 1, color: "blue", description: "" });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao criar estado");
    } finally {
      setFormLoading(false);
    }
  };

  const openEditStatusDialog = (status) => {
    setEditingStatusId(status.id);
    setStatusFormData({ name: status.name, label: status.label, order: status.order, color: status.color, description: status.description || "" });
    setIsEditStatusDialogOpen(true);
  };

  const handleEditStatus = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      await updateWorkflowStatus(editingStatusId, { label: statusFormData.label, order: statusFormData.order, color: statusFormData.color, description: statusFormData.description });
      toast.success("Estado atualizado");
      setIsEditStatusDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao atualizar estado");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteStatus = async (statusId) => {
    if (!window.confirm("Tem a certeza que deseja eliminar este estado?")) return;
    try {
      await deleteWorkflowStatus(statusId);
      toast.success("Estado eliminado");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao eliminar estado");
    }
  };

  // Event/Deadline handlers
  const openCreateEventDialog = (date) => {
    setEventFormData({
      title: "",
      description: "",
      due_date: date ? date.toISOString().split('T')[0] : selectedDate.toISOString().split('T')[0],
      priority: "medium",
      process_id: "",
      assigned_consultor_id: "",
      assigned_mediador_id: ""
    });
    setIsCreateEventDialogOpen(true);
  };

  const handleCreateEvent = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      const data = {
        title: eventFormData.title,
        description: eventFormData.description || null,
        due_date: eventFormData.due_date,
        priority: eventFormData.priority,
        process_id: eventFormData.process_id || null,
        assigned_user_ids: eventFormData.assigned_user_ids.length > 0 ? eventFormData.assigned_user_ids : [user.id]
      };
      await createDeadline(data);
      toast.success("Evento criado com sucesso");
      setIsCreateEventDialogOpen(false);
      setEventFormData({ title: "", description: "", due_date: "", priority: "medium", process_id: "", assigned_user_ids: [] });
      fetchCalendarData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao criar evento");
    } finally {
      setFormLoading(false);
    }
  };

  const toggleUserAssignment = (userId) => {
    setEventFormData(prev => {
      const current = prev.assigned_user_ids || [];
      if (current.includes(userId)) {
        return { ...prev, assigned_user_ids: current.filter(id => id !== userId) };
      } else {
        return { ...prev, assigned_user_ids: [...current, userId] };
      }
    });
  };

  const handleDeleteEvent = async (eventId) => {
    if (!window.confirm("Tem a certeza que deseja eliminar este evento?")) return;
    try {
      await deleteDeadline(eventId);
      toast.success("Evento eliminado");
      fetchCalendarData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao eliminar evento");
    }
  };

  const getUserName = (userId) => {
    const user = users.find(u => u.id === userId);
    return user ? user.name : "-";
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="admin-dashboard">
        <div>
          <h1 className="text-2xl font-bold">Painel de Administração</h1>
          <p className="text-muted-foreground">Gestão completa do sistema</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <FileText className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.total_processes || 0}</p>
                  <p className="text-sm text-muted-foreground">Total Processos</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
                  <Users className="h-6 w-6 text-emerald-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.total_users || 0}</p>
                  <p className="text-sm text-muted-foreground">Utilizadores</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                  <CalendarIcon className="h-6 w-6 text-orange-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.pending_deadlines || 0}</p>
                  <p className="text-sm text-muted-foreground">Prazos Pendentes</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                  <GitBranch className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{workflowStatuses.length}</p>
                  <p className="text-sm text-muted-foreground">Estados</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="flex-wrap">
            <TabsTrigger value="overview" className="gap-2">
              <Eye className="h-4 w-4" />
              Visão Geral
            </TabsTrigger>
            <TabsTrigger value="calendar" className="gap-2">
              <CalendarIcon className="h-4 w-4" />
              Calendário
            </TabsTrigger>
            <TabsTrigger value="documents" className="gap-2">
              <FileText className="h-4 w-4" />
              Documentos
            </TabsTrigger>
            <TabsTrigger value="ai" className="gap-2">
              <Sparkles className="h-4 w-4" />
              Análise IA
            </TabsTrigger>
            <TabsTrigger value="clients" className="gap-2">
              <Search className="h-4 w-4" />
              Pesquisar Cliente
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="mt-6 space-y-6">
            <Card className="border-border">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <LayoutGrid className="h-5 w-5" />
                  Quadro Geral de Processos
                </CardTitle>
                <CardDescription>
                  {filteredProcesses.length} processos • Filtre por consultor ou intermediário
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  <div className="space-y-2">
                    <Label>Filtrar por Consultor</Label>
                    <Select value={consultorFilter} onValueChange={setConsultorFilter}>
                      <SelectTrigger><SelectValue placeholder="Todos os consultores" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos os consultores</SelectItem>
                        {consultors.map((c) => (<SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Filtrar por Intermediário</Label>
                    <Select value={mediadorFilter} onValueChange={setMediadorFilter}>
                      <SelectTrigger><SelectValue placeholder="Todos os intermediários" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos os intermediários</SelectItem>
                        {intermediarios.map((m) => (<SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Kanban Board */}
                <KanbanBoard token={localStorage.getItem('token')} />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Calendar Tab */}
          <TabsContent value="calendar" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="border-border lg:col-span-1">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Filtros & Calendário</CardTitle>
                    <Button size="sm" onClick={() => openCreateEventDialog()}>
                      <Plus className="h-4 w-4 mr-1" />Evento
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Consultor</Label>
                    <Select value={consultorFilter} onValueChange={setConsultorFilter}>
                      <SelectTrigger><SelectValue placeholder="Todos" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos</SelectItem>
                        {consultors.map((c) => (<SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Intermediário</Label>
                    <Select value={mediadorFilter} onValueChange={setMediadorFilter}>
                      <SelectTrigger><SelectValue placeholder="Todos" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos</SelectItem>
                        {intermediarios.map((m) => (<SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="pt-4 border-t">
                    <Calendar
                      mode="single"
                      selected={selectedDate}
                      onSelect={(date) => date && setSelectedDate(date)}
                      className="rounded-md border"
                      modifiers={{ hasDeadline: datesWithDeadlines }}
                      modifiersStyles={{ hasDeadline: { backgroundColor: "rgb(254 202 202)", fontWeight: "bold" } }}
                    />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border lg:col-span-2">
                <CardHeader>
                  <CardTitle className="text-lg">
                    Prazos - {selectedDate.toLocaleDateString('pt-PT', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                  </CardTitle>
                  <CardDescription>{deadlinesForDate.length} prazo(s) nesta data</CardDescription>
                </CardHeader>
                <CardContent>
                  {deadlinesForDate.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>Nenhum prazo para esta data</p>
                      <Button variant="outline" className="mt-4" onClick={() => openCreateEventDialog(selectedDate)}>
                        <Plus className="h-4 w-4 mr-2" />Criar Evento
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {deadlinesForDate.map((deadline) => (
                        <div key={deadline.id} className="flex items-center justify-between p-4 bg-muted/30 rounded-lg">
                          <div className="space-y-1">
                            <p className="font-medium">{deadline.title}</p>
                            <p className="text-sm text-muted-foreground">
                              {deadline.client_name !== "Evento Geral" ? `Cliente: ${deadline.client_name}` : "Evento Geral"}
                            </p>
                            <div className="flex gap-2 mt-2 flex-wrap">
                              {deadline.assigned_consultor_id && (
                                <Badge variant="outline" className="text-xs bg-blue-50">Consultor: {getUserName(deadline.assigned_consultor_id)}</Badge>
                              )}
                              {deadline.assigned_mediador_id && (
                                <Badge variant="outline" className="text-xs bg-emerald-50">Mediador: {getUserName(deadline.assigned_mediador_id)}</Badge>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge className={deadline.priority === "high" ? "bg-red-100 text-red-800" : deadline.priority === "medium" ? "bg-yellow-100 text-yellow-800" : "bg-green-100 text-green-800"}>
                              {deadline.priority === "high" ? "Alta" : deadline.priority === "medium" ? "Média" : "Baixa"}
                            </Badge>
                            {deadline.process_id && (
                              <Button variant="ghost" size="icon" onClick={() => navigate(`/process/${deadline.process_id}`)}>
                                <Eye className="h-4 w-4" />
                              </Button>
                            )}
                            <Button variant="ghost" size="icon" onClick={() => handleDeleteEvent(deadline.id)}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Documents Tab - Admin can see all document expiries GROUPED BY CLIENT */}
          <TabsContent value="documents" className="mt-6">
            <Card className="border-border">
              <CardHeader>
                <CardTitle className="text-lg">Documentos a Expirar (Próximos 60 dias)</CardTitle>
                <CardDescription>Documentos de todos os clientes próximos da data de validade, agrupados por cliente</CardDescription>
              </CardHeader>
              <CardContent>
                {upcomingExpiries.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Nenhum documento a expirar</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Agrupar por cliente */}
                    {Object.entries(
                      upcomingExpiries.reduce((acc, doc) => {
                        const clientKey = doc.client_name || 'Sem Cliente';
                        if (!acc[clientKey]) {
                          acc[clientKey] = {
                            client_name: doc.client_name,
                            process_id: doc.process_id,
                            documents: []
                          };
                        }
                        acc[clientKey].documents.push(doc);
                        return acc;
                      }, {})
                    ).map(([clientName, clientData]) => (
                      <Card key={clientName} className="border-l-4 border-l-amber-500">
                        <CardHeader className="py-3 px-4 bg-muted/30">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Users className="h-4 w-4 text-blue-900" />
                              <CardTitle className="text-base font-semibold">{clientName}</CardTitle>
                              <Badge variant="outline" className="ml-2">
                                {clientData.documents.length} documento(s)
                              </Badge>
                            </div>
                            {clientData.process_id && (
                              <Button variant="ghost" size="sm" onClick={() => navigate(`/process/${clientData.process_id}`)}>
                                <Eye className="h-4 w-4 mr-1" /> Ver Processo
                              </Button>
                            )}
                          </div>
                        </CardHeader>
                        <CardContent className="pt-2 pb-3">
                          <div className="space-y-2">
                            {clientData.documents.map((doc) => {
                              const daysUntil = Math.ceil((new Date(doc.expiry_date) - new Date()) / (1000 * 60 * 60 * 24));
                              const urgencyClass = daysUntil <= 7 ? 'bg-red-50 border-red-200 text-red-800' : 
                                                   daysUntil <= 30 ? 'bg-amber-50 border-amber-200 text-amber-800' : 
                                                   'bg-blue-50 border-blue-200 text-blue-800';
                              return (
                                <div key={doc.id} className={`flex items-center justify-between p-2 rounded border ${urgencyClass}`}>
                                  <div className="flex items-center gap-3">
                                    <FileText className="h-4 w-4" />
                                    <span className="font-medium">{doc.document_name}</span>
                                    <Badge variant="outline" className="text-xs">{doc.document_type}</Badge>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm">
                                      {new Date(doc.expiry_date).toLocaleDateString('pt-PT')}
                                    </span>
                                    <Badge className={daysUntil <= 7 ? 'bg-red-500' : daysUntil <= 30 ? 'bg-amber-500' : 'bg-blue-500'}>
                                      {daysUntil} dias
                                    </Badge>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* AI Tab - Admin can use AI analysis */}
          <TabsContent value="ai" className="mt-6">
            <Card className="border-border">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-purple-500" />
                  Análise de Documentos com IA
                </CardTitle>
                <CardDescription>
                  Use a IA para extrair dados de documentos automaticamente
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  A funcionalidade de análise IA está disponível nos dashboards de Consultor e Mediador.
                  Como admin, pode aceder a todas as funcionalidades através da visualização de processos individuais.
                </p>
                <Button className="mt-4" onClick={() => setActiveTab("overview")}>
                  Ver Processos
                </Button>
              </CardContent>
            </Card>
          </TabsContent>


          {/* Clients Search Tab */}
          <TabsContent value="clients" className="mt-6">
            <Card className="border-border">
              <CardHeader>
                <CardTitle className="text-lg">Pesquisar Cliente</CardTitle>
                <CardDescription>Encontre e visualize informações de clientes</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input 
                      placeholder="Pesquisar por nome, email ou telefone..." 
                      className="pl-10" 
                      value={searchTerm} 
                      onChange={(e) => setSearchTerm(e.target.value)} 
                    />
                  </div>

                  {searchTerm.length >= 2 ? (
                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Nome</TableHead>
                            <TableHead>Email</TableHead>
                            <TableHead>Telefone</TableHead>
                            <TableHead>Fase</TableHead>
                            <TableHead>Valor</TableHead>
                            <TableHead className="text-right">Ações</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {processes.filter(p => 
                            p.client_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                            p.client_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                            p.client_phone?.includes(searchTerm)
                          ).map((process) => {
                            const status = workflowStatuses.find(s => s.name === process.status);
                            return (
                              <TableRow key={process.id} className="cursor-pointer hover:bg-muted/50" onClick={() => navigate(`/process/${process.id}`)}>
                                <TableCell className="font-medium">{process.client_name}</TableCell>
                                <TableCell>{process.client_email}</TableCell>
                                <TableCell>{process.client_phone || "-"}</TableCell>
                                <TableCell>
                                  <Badge className={`bg-${status?.color || 'gray'}-100 text-${status?.color || 'gray'}-800 border`}>
                                    {status?.label || process.status}
                                  </Badge>
                                </TableCell>
                                <TableCell>{process.property_value ? `€${process.property_value.toLocaleString('pt-PT')}` : "-"}</TableCell>
                                <TableCell className="text-right">
                                  <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); navigate(`/process/${process.id}`); }}>
                                    <Eye className="h-4 w-4" />
                                  </Button>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                          {processes.filter(p => 
                            p.client_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                            p.client_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                            p.client_phone?.includes(searchTerm)
                          ).length === 0 && (
                            <TableRow>
                              <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                Nenhum cliente encontrado com "{searchTerm}"
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Digite pelo menos 2 caracteres para pesquisar</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Users Tab */}

        </Tabs>
      </div>

      {/* Dialog para Criar Evento */}
      <Dialog open={isCreateEventDialogOpen} onOpenChange={setIsCreateEventDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Criar Novo Evento</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateEvent} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="event-title">Título *</Label>
              <Input
                id="event-title"
                value={eventFormData.title}
                onChange={(e) => setEventFormData({ ...eventFormData, title: e.target.value })}
                placeholder="Ex: Reunião com cliente"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="event-description">Descrição</Label>
              <Textarea
                id="event-description"
                value={eventFormData.description}
                onChange={(e) => setEventFormData({ ...eventFormData, description: e.target.value })}
                placeholder="Detalhes do evento..."
                rows={3}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="event-date">Data *</Label>
                <Input
                  id="event-date"
                  type="date"
                  value={eventFormData.due_date}
                  onChange={(e) => setEventFormData({ ...eventFormData, due_date: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="event-priority">Prioridade</Label>
                <Select
                  value={eventFormData.priority}
                  onValueChange={(value) => setEventFormData({ ...eventFormData, priority: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Baixa</SelectItem>
                    <SelectItem value="medium">Média</SelectItem>
                    <SelectItem value="high">Alta</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="event-process">Processo (opcional)</Label>
              <Select
                value={eventFormData.process_id || "none"}
                onValueChange={(value) => setEventFormData({ ...eventFormData, process_id: value === "none" ? "" : value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecionar processo..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Nenhum (Evento Geral)</SelectItem>
                  {processes.slice(0, 50).map((process) => (
                    <SelectItem key={process.id} value={process.id}>
                      {process.client_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Atribuir a (selecione um ou mais)</Label>
              <p className="text-xs text-muted-foreground mb-2">
                O evento será sempre adicionado ao seu calendário. Selecione outros colaboradores para partilhar.
              </p>
              <div className="border rounded-md p-3 max-h-40 overflow-y-auto space-y-2">
                {staffUsers.map((staffUser) => (
                  <div key={staffUser.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`user-${staffUser.id}`}
                      checked={eventFormData.assigned_user_ids?.includes(staffUser.id) || staffUser.id === user?.id}
                      disabled={staffUser.id === user?.id}
                      onCheckedChange={() => toggleUserAssignment(staffUser.id)}
                    />
                    <label
                      htmlFor={`user-${staffUser.id}`}
                      className={`text-sm cursor-pointer flex items-center gap-2 ${staffUser.id === user?.id ? 'font-medium' : ''}`}
                    >
                      {staffUser.name}
                      {staffUser.id === user?.id && <Badge variant="outline" className="text-xs">Você</Badge>}
                      <span className="text-xs text-muted-foreground">({staffUser.role})</span>
                    </label>
                  </div>
                ))}
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsCreateEventDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={formLoading} className="bg-blue-900 hover:bg-blue-800">
                {formLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Criar Evento"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
};

export default AdminDashboard;
