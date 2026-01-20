import { useState, useEffect } from "react";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { 
  getUsers, createUser, updateUser, deleteUser, getStats,
  getWorkflowStatuses, createWorkflowStatus, updateWorkflowStatus, deleteWorkflowStatus,
  getOneDriveStatus
} from "../services/api";
import {
  Users,
  UserPlus,
  Search,
  Edit,
  Trash2,
  Loader2,
  GitBranch,
  Plus,
  ArrowUp,
  ArrowDown,
  Settings,
  FolderOpen,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { format, parseISO } from "date-fns";
import { pt } from "date-fns/locale";

const roleLabels = {
  cliente: "Cliente",
  consultor: "Consultor",
  mediador: "Mediador",
  admin: "Administrador",
};

const roleColors = {
  cliente: "bg-blue-100 text-blue-800 border-blue-200",
  consultor: "bg-emerald-100 text-emerald-800 border-emerald-200",
  mediador: "bg-purple-100 text-purple-800 border-purple-200",
  admin: "bg-red-100 text-red-800 border-red-200",
};

const statusColorOptions = [
  { value: "yellow", label: "Amarelo", class: "bg-yellow-100 text-yellow-800" },
  { value: "blue", label: "Azul", class: "bg-blue-100 text-blue-800" },
  { value: "orange", label: "Laranja", class: "bg-orange-100 text-orange-800" },
  { value: "green", label: "Verde", class: "bg-emerald-100 text-emerald-800" },
  { value: "red", label: "Vermelho", class: "bg-red-100 text-red-800" },
  { value: "purple", label: "Roxo", class: "bg-purple-100 text-purple-800" },
];

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState("users");
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [workflowStatuses, setWorkflowStatuses] = useState([]);
  const [stats, setStats] = useState(null);
  const [oneDriveStatus, setOneDriveStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  
  // User dialogs
  const [isCreateUserDialogOpen, setIsCreateUserDialogOpen] = useState(false);
  const [isEditUserDialogOpen, setIsEditUserDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [formLoading, setFormLoading] = useState(false);
  const [userFormData, setUserFormData] = useState({
    name: "", email: "", password: "", phone: "", role: "cliente", onedrive_folder: ""
  });

  // Workflow dialogs
  const [isCreateStatusDialogOpen, setIsCreateStatusDialogOpen] = useState(false);
  const [isEditStatusDialogOpen, setIsEditStatusDialogOpen] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState(null);
  const [statusFormData, setStatusFormData] = useState({
    name: "", label: "", order: 1, color: "blue", description: ""
  });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    filterUsers();
  }, [users, searchTerm, roleFilter]);

  const fetchData = async () => {
    try {
      const [usersRes, statsRes, statusesRes] = await Promise.all([
        getUsers(),
        getStats(),
        getWorkflowStatuses()
      ]);
      setUsers(usersRes.data);
      setStats(statsRes.data);
      setWorkflowStatuses(statusesRes.data);

      try {
        const oneDriveRes = await getOneDriveStatus();
        setOneDriveStatus(oneDriveRes.data);
      } catch (e) {
        setOneDriveStatus({ configured: false });
      }
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  };

  const filterUsers = () => {
    let filtered = [...users];
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(u => u.name.toLowerCase().includes(term) || u.email.toLowerCase().includes(term));
    }
    if (roleFilter !== "all") {
      filtered = filtered.filter(u => u.role === roleFilter);
    }
    setFilteredUsers(filtered);
  };

  // User CRUD
  const handleCreateUser = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      await createUser(userFormData);
      toast.success("Utilizador criado com sucesso!");
      setIsCreateUserDialogOpen(false);
      setUserFormData({ name: "", email: "", password: "", phone: "", role: "cliente", onedrive_folder: "" });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao criar utilizador");
    } finally {
      setFormLoading(false);
    }
  };

  const handleEditUser = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      await updateUser(selectedUser.id, {
        name: userFormData.name,
        phone: userFormData.phone,
        role: userFormData.role,
        onedrive_folder: userFormData.onedrive_folder,
      });
      toast.success("Utilizador atualizado!");
      setIsEditUserDialogOpen(false);
      setSelectedUser(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao atualizar utilizador");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!confirm("Tem certeza que deseja eliminar este utilizador?")) return;
    try {
      await deleteUser(userId);
      toast.success("Utilizador eliminado!");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao eliminar utilizador");
    }
  };

  const openEditUserDialog = (user) => {
    setSelectedUser(user);
    setUserFormData({
      name: user.name,
      email: user.email,
      password: "",
      phone: user.phone || "",
      role: user.role,
      onedrive_folder: user.onedrive_folder || "",
    });
    setIsEditUserDialogOpen(true);
  };

  // Workflow CRUD
  const handleCreateStatus = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      await createWorkflowStatus(statusFormData);
      toast.success("Estado criado com sucesso!");
      setIsCreateStatusDialogOpen(false);
      setStatusFormData({ name: "", label: "", order: workflowStatuses.length + 1, color: "blue", description: "" });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao criar estado");
    } finally {
      setFormLoading(false);
    }
  };

  const handleEditStatus = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      await updateWorkflowStatus(selectedStatus.id, {
        label: statusFormData.label,
        order: statusFormData.order,
        color: statusFormData.color,
        description: statusFormData.description,
      });
      toast.success("Estado atualizado!");
      setIsEditStatusDialogOpen(false);
      setSelectedStatus(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao atualizar estado");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteStatus = async (statusId) => {
    if (!confirm("Tem certeza? Não pode eliminar estados com processos associados.")) return;
    try {
      await deleteWorkflowStatus(statusId);
      toast.success("Estado eliminado!");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao eliminar estado");
    }
  };

  const openEditStatusDialog = (status) => {
    setSelectedStatus(status);
    setStatusFormData({
      name: status.name,
      label: status.label,
      order: status.order,
      color: status.color,
      description: status.description || "",
    });
    setIsEditStatusDialogOpen(true);
  };

  const getColorClass = (color) => {
    return statusColorOptions.find(c => c.value === color)?.class || "bg-gray-100 text-gray-800";
  };

  if (loading) {
    return (
      <DashboardLayout title="Administração">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Administração">
      <div className="space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-border">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Utilizadores</p>
                  <p className="text-3xl font-bold font-mono mt-1">{stats?.total_users || 0}</p>
                </div>
                <div className="h-12 w-12 bg-primary/10 rounded-md flex items-center justify-center">
                  <Users className="h-6 w-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Clientes</p>
                  <p className="text-3xl font-bold font-mono mt-1">{stats?.clients || 0}</p>
                </div>
                <div className="h-12 w-12 bg-blue-100 rounded-md flex items-center justify-center">
                  <Users className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">OneDrive</p>
                  <p className="text-lg font-semibold mt-1">
                    {oneDriveStatus?.configured ? "Configurado" : "Não configurado"}
                  </p>
                </div>
                <div className={`h-12 w-12 rounded-md flex items-center justify-center ${oneDriveStatus?.configured ? "bg-emerald-100" : "bg-red-100"}`}>
                  {oneDriveStatus?.configured ? (
                    <CheckCircle className="h-6 w-6 text-emerald-600" />
                  ) : (
                    <XCircle className="h-6 w-6 text-red-600" />
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Estados de Fluxo</p>
                  <p className="text-3xl font-bold font-mono mt-1">{workflowStatuses.length}</p>
                </div>
                <div className="h-12 w-12 bg-purple-100 rounded-md flex items-center justify-center">
                  <GitBranch className="h-6 w-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="users" className="gap-2">
              <Users className="h-4 w-4" />
              Utilizadores
            </TabsTrigger>
            <TabsTrigger value="workflow" className="gap-2">
              <GitBranch className="h-4 w-4" />
              Fluxo de Processos
            </TabsTrigger>
            <TabsTrigger value="settings" className="gap-2">
              <Settings className="h-4 w-4" />
              Configurações
            </TabsTrigger>
          </TabsList>

          {/* Users Tab */}
          <TabsContent value="users" className="mt-6">
            <Card className="border-border">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">Gestão de Utilizadores</CardTitle>
                    <CardDescription>Gerir utilizadores do sistema</CardDescription>
                  </div>
                  <Dialog open={isCreateUserDialogOpen} onOpenChange={setIsCreateUserDialogOpen}>
                    <DialogTrigger asChild>
                      <Button data-testid="create-user-btn">
                        <UserPlus className="h-4 w-4 mr-2" />
                        Novo Utilizador
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Criar Novo Utilizador</DialogTitle>
                      </DialogHeader>
                      <form onSubmit={handleCreateUser} className="space-y-4">
                        <div className="space-y-2">
                          <Label>Nome</Label>
                          <Input value={userFormData.name} onChange={(e) => setUserFormData({ ...userFormData, name: e.target.value })} required />
                        </div>
                        <div className="space-y-2">
                          <Label>Email</Label>
                          <Input type="email" value={userFormData.email} onChange={(e) => setUserFormData({ ...userFormData, email: e.target.value })} required />
                        </div>
                        <div className="space-y-2">
                          <Label>Password</Label>
                          <Input type="password" value={userFormData.password} onChange={(e) => setUserFormData({ ...userFormData, password: e.target.value })} required />
                        </div>
                        <div className="space-y-2">
                          <Label>Telefone</Label>
                          <Input value={userFormData.phone} onChange={(e) => setUserFormData({ ...userFormData, phone: e.target.value })} />
                        </div>
                        <div className="space-y-2">
                          <Label>Perfil</Label>
                          <Select value={userFormData.role} onValueChange={(value) => setUserFormData({ ...userFormData, role: value })}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="cliente">Cliente</SelectItem>
                              <SelectItem value="consultor">Consultor</SelectItem>
                              <SelectItem value="mediador">Mediador</SelectItem>
                              <SelectItem value="admin">Administrador</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Pasta OneDrive</Label>
                          <Input 
                            value={userFormData.onedrive_folder} 
                            onChange={(e) => setUserFormData({ ...userFormData, onedrive_folder: e.target.value })} 
                            placeholder="Nome da pasta no OneDrive"
                          />
                        </div>
                        <DialogFooter>
                          <Button type="submit" disabled={formLoading}>
                            {formLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Criar"}
                          </Button>
                        </DialogFooter>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                {/* Filters */}
                <div className="flex flex-col sm:flex-row gap-4 mb-4">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input placeholder="Pesquisar..." className="pl-10" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
                  </div>
                  <Select value={roleFilter} onValueChange={setRoleFilter}>
                    <SelectTrigger className="w-full sm:w-48"><SelectValue placeholder="Filtrar por perfil" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos os perfis</SelectItem>
                      <SelectItem value="cliente">Cliente</SelectItem>
                      <SelectItem value="consultor">Consultor</SelectItem>
                      <SelectItem value="mediador">Mediador</SelectItem>
                      <SelectItem value="admin">Administrador</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Users Table */}
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Nome</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Perfil</TableHead>
                        <TableHead>Pasta OneDrive</TableHead>
                        <TableHead className="text-right">Ações</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredUsers.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                            Nenhum utilizador encontrado
                          </TableCell>
                        </TableRow>
                      ) : (
                        filteredUsers.map((user) => (
                          <TableRow key={user.id}>
                            <TableCell className="font-medium">{user.name}</TableCell>
                            <TableCell>{user.email}</TableCell>
                            <TableCell>
                              <Badge className={`${roleColors[user.role]} border`}>{roleLabels[user.role]}</Badge>
                            </TableCell>
                            <TableCell className="font-mono text-sm">{user.onedrive_folder || "-"}</TableCell>
                            <TableCell className="text-right">
                              <Button variant="ghost" size="icon" onClick={() => openEditUserDialog(user)}>
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="icon" onClick={() => handleDeleteUser(user.id)}>
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Workflow Tab */}
          <TabsContent value="workflow" className="mt-6">
            <Card className="border-border">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">Estados do Fluxo de Processos</CardTitle>
                    <CardDescription>Configurar as fases dos processos</CardDescription>
                  </div>
                  <Dialog open={isCreateStatusDialogOpen} onOpenChange={setIsCreateStatusDialogOpen}>
                    <DialogTrigger asChild>
                      <Button data-testid="create-status-btn">
                        <Plus className="h-4 w-4 mr-2" />
                        Novo Estado
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Criar Novo Estado</DialogTitle>
                      </DialogHeader>
                      <form onSubmit={handleCreateStatus} className="space-y-4">
                        <div className="space-y-2">
                          <Label>Nome (identificador)</Label>
                          <Input 
                            value={statusFormData.name} 
                            onChange={(e) => setStatusFormData({ ...statusFormData, name: e.target.value.toLowerCase().replace(/\s+/g, "_") })} 
                            placeholder="ex: documentos_pendentes"
                            required 
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Label (exibição)</Label>
                          <Input 
                            value={statusFormData.label} 
                            onChange={(e) => setStatusFormData({ ...statusFormData, label: e.target.value })} 
                            placeholder="ex: Documentos Pendentes"
                            required 
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Ordem</Label>
                          <Input 
                            type="number" 
                            value={statusFormData.order} 
                            onChange={(e) => setStatusFormData({ ...statusFormData, order: parseInt(e.target.value) || 1 })} 
                            min={1}
                            required 
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Cor</Label>
                          <Select value={statusFormData.color} onValueChange={(value) => setStatusFormData({ ...statusFormData, color: value })}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                              {statusColorOptions.map((color) => (
                                <SelectItem key={color.value} value={color.value}>
                                  <div className="flex items-center gap-2">
                                    <span className={`w-3 h-3 rounded-full ${color.class.split(" ")[0]}`} />
                                    {color.label}
                                  </div>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Descrição</Label>
                          <Input value={statusFormData.description} onChange={(e) => setStatusFormData({ ...statusFormData, description: e.target.value })} />
                        </div>
                        <DialogFooter>
                          <Button type="submit" disabled={formLoading}>
                            {formLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Criar"}
                          </Button>
                        </DialogFooter>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {workflowStatuses.map((status, index) => (
                    <div key={status.id} className="flex items-center justify-between p-4 bg-muted/30 rounded-md">
                      <div className="flex items-center gap-4">
                        <span className="text-2xl font-bold text-muted-foreground font-mono w-8">{status.order}</span>
                        <div>
                          <div className="flex items-center gap-2">
                            <Badge className={`${getColorClass(status.color)} border`}>{status.label}</Badge>
                            {status.is_default && <Badge variant="outline" className="text-xs">Padrão</Badge>}
                          </div>
                          <p className="text-xs text-muted-foreground font-mono mt-1">{status.name}</p>
                          {status.description && <p className="text-sm text-muted-foreground">{status.description}</p>}
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" onClick={() => openEditStatusDialog(status)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        {!status.is_default && (
                          <Button variant="ghost" size="icon" onClick={() => handleDeleteStatus(status.id)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings" className="mt-6">
            <div className="grid gap-6">
              <Card className="border-border">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FolderOpen className="h-5 w-5" />
                    Integração OneDrive
                  </CardTitle>
                  <CardDescription>Configuração de acesso aos documentos</CardDescription>
                </CardHeader>
                <CardContent>
                  {oneDriveStatus?.configured ? (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 text-emerald-600">
                        <CheckCircle className="h-5 w-5" />
                        <span className="font-medium">OneDrive configurado</span>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Tenant ID</p>
                          <p className="font-mono">{oneDriveStatus.tenant_id}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Client ID</p>
                          <p className="font-mono">{oneDriveStatus.client_id}</p>
                        </div>
                        <div className="col-span-2">
                          <p className="text-muted-foreground">Pasta Base</p>
                          <p className="font-mono">{oneDriveStatus.base_path}</p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 text-red-600">
                        <XCircle className="h-5 w-5" />
                        <span className="font-medium">OneDrive não configurado</span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Para configurar o OneDrive, adicione as seguintes variáveis de ambiente:
                      </p>
                      <div className="bg-muted p-4 rounded-md font-mono text-sm space-y-1">
                        <p>ONEDRIVE_TENANT_ID=seu_tenant_id</p>
                        <p>ONEDRIVE_CLIENT_ID=seu_client_id</p>
                        <p>ONEDRIVE_CLIENT_SECRET=seu_client_secret</p>
                        <p>ONEDRIVE_BASE_PATH=Documentação Clientes</p>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Siga as instruções do Azure Portal para registar uma aplicação e obter as credenciais.
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Edit User Dialog */}
        <Dialog open={isEditUserDialogOpen} onOpenChange={setIsEditUserDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Editar Utilizador</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleEditUser} className="space-y-4">
              <div className="space-y-2">
                <Label>Nome</Label>
                <Input value={userFormData.name} onChange={(e) => setUserFormData({ ...userFormData, name: e.target.value })} required />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input type="email" value={userFormData.email} disabled className="bg-muted" />
              </div>
              <div className="space-y-2">
                <Label>Telefone</Label>
                <Input value={userFormData.phone} onChange={(e) => setUserFormData({ ...userFormData, phone: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Perfil</Label>
                <Select value={userFormData.role} onValueChange={(value) => setUserFormData({ ...userFormData, role: value })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cliente">Cliente</SelectItem>
                    <SelectItem value="consultor">Consultor</SelectItem>
                    <SelectItem value="mediador">Mediador</SelectItem>
                    <SelectItem value="admin">Administrador</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Pasta OneDrive</Label>
                <Input 
                  value={userFormData.onedrive_folder} 
                  onChange={(e) => setUserFormData({ ...userFormData, onedrive_folder: e.target.value })} 
                  placeholder="Nome da pasta no OneDrive"
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={formLoading}>
                  {formLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Guardar"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Edit Status Dialog */}
        <Dialog open={isEditStatusDialogOpen} onOpenChange={setIsEditStatusDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Editar Estado</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleEditStatus} className="space-y-4">
              <div className="space-y-2">
                <Label>Nome (identificador)</Label>
                <Input value={statusFormData.name} disabled className="bg-muted font-mono" />
              </div>
              <div className="space-y-2">
                <Label>Label (exibição)</Label>
                <Input value={statusFormData.label} onChange={(e) => setStatusFormData({ ...statusFormData, label: e.target.value })} required />
              </div>
              <div className="space-y-2">
                <Label>Ordem</Label>
                <Input type="number" value={statusFormData.order} onChange={(e) => setStatusFormData({ ...statusFormData, order: parseInt(e.target.value) || 1 })} min={1} required />
              </div>
              <div className="space-y-2">
                <Label>Cor</Label>
                <Select value={statusFormData.color} onValueChange={(value) => setStatusFormData({ ...statusFormData, color: value })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {statusColorOptions.map((color) => (
                      <SelectItem key={color.value} value={color.value}>
                        <div className="flex items-center gap-2">
                          <span className={`w-3 h-3 rounded-full ${color.class.split(" ")[0]}`} />
                          {color.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Descrição</Label>
                <Input value={statusFormData.description} onChange={(e) => setStatusFormData({ ...statusFormData, description: e.target.value })} />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={formLoading}>
                  {formLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Guardar"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
};

export default AdminDashboard;
