import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { Textarea } from "../components/ui/textarea";
import { toast } from "sonner";
import {
  Users,
  Plus,
  Search,
  MoreHorizontal,
  FileText,
  Phone,
  Mail,
  Hash,
  Building2,
  UserPlus,
  Eye,
  Trash2,
  Link2,
  RefreshCw,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function ClientsPage() {
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showProcessDialog, setShowProcessDialog] = useState(false);
  const [selectedClient, setSelectedClient] = useState(null);
  const [newClient, setNewClient] = useState({
    nome: "",
    email: "",
    telefone: "",
    nif: "",
    notas: "",
  });
  const [newProcessType, setNewProcessType] = useState("credito_habitacao");

  const fetchClients = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      const params = new URLSearchParams();
      if (searchTerm) params.append("search", searchTerm);

      const response = await fetch(`${API_URL}/api/clients?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setClients(data.clients || []);
      }
    } catch (error) {
      console.error("Erro ao carregar clientes:", error);
      toast.error("Erro ao carregar clientes");
    } finally {
      setLoading(false);
    }
  }, [searchTerm]);

  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  const handleCreateClient = async () => {
    if (!newClient.nome.trim()) {
      toast.error("Nome é obrigatório");
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_URL}/api/clients`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newClient),
      });

      if (response.ok) {
        toast.success("Cliente criado com sucesso");
        setShowCreateDialog(false);
        setNewClient({ nome: "", email: "", telefone: "", nif: "", notas: "" });
        fetchClients();
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao criar cliente");
      }
    } catch (error) {
      console.error("Erro ao criar cliente:", error);
      toast.error("Erro ao criar cliente");
    }
  };

  const handleCreateProcess = async () => {
    if (!selectedClient) return;

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `${API_URL}/api/clients/${selectedClient.id}/create-process?process_type=${newProcessType}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        toast.success(`Processo #${data.process_number} criado`);
        setShowProcessDialog(false);
        setSelectedClient(null);
        fetchClients();
        // Navegar para o novo processo
        navigate(`/processes/${data.process_id}`);
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao criar processo");
      }
    } catch (error) {
      console.error("Erro ao criar processo:", error);
      toast.error("Erro ao criar processo");
    }
  };

  const handleDeleteClient = async (clientId) => {
    if (!window.confirm("Tem a certeza que deseja eliminar este cliente?")) {
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_URL}/api/clients/${clientId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        toast.success("Cliente eliminado");
        fetchClients();
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao eliminar cliente");
      }
    } catch (error) {
      console.error("Erro ao eliminar cliente:", error);
      toast.error("Erro ao eliminar cliente");
    }
  };

  const openCreateProcessDialog = (client) => {
    setSelectedClient(client);
    setShowProcessDialog(true);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="clients-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Users className="h-6 w-6 text-primary" />
              Gestão de Clientes
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Gerir clientes e os seus processos de compra
            </p>
          </div>
          <Button
            onClick={() => setShowCreateDialog(true)}
            className="gap-2"
            data-testid="create-client-btn"
          >
            <Plus className="h-4 w-4" />
            Novo Cliente
          </Button>
        </div>

        {/* Search & Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="md:col-span-2">
            <CardContent className="pt-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Pesquisar por nome, email ou NIF..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                  data-testid="search-clients-input"
                />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Users className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{clients.length}</p>
                  <p className="text-xs text-muted-foreground">Total Clientes</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                  <FileText className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {clients.filter((c) => c.active_processes_count > 0).length}
                  </p>
                  <p className="text-xs text-muted-foreground">Com Processos Activos</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Clients Table */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Lista de Clientes</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchClients}
                className="gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Actualizar
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-8">
                <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : clients.length === 0 ? (
              <div className="text-center py-12">
                <Users className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">Nenhum cliente encontrado</p>
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={() => setShowCreateDialog(true)}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Criar primeiro cliente
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Contacto</TableHead>
                    <TableHead>NIF</TableHead>
                    <TableHead className="text-center">Processos</TableHead>
                    <TableHead className="text-right">Acções</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clients.map((client) => (
                    <TableRow key={client.id} data-testid={`client-row-${client.id}`}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center">
                            <span className="text-sm font-medium text-primary">
                              {client.nome?.charAt(0)?.toUpperCase() || "?"}
                            </span>
                          </div>
                          <div>
                            <p className="font-medium">{client.nome}</p>
                            {client.fonte && (
                              <Badge variant="outline" className="text-xs mt-1">
                                {client.fonte}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          {client.contacto?.email && (
                            <div className="flex items-center gap-1 text-sm text-muted-foreground">
                              <Mail className="h-3 w-3" />
                              {client.contacto.email}
                            </div>
                          )}
                          {client.contacto?.telefone && (
                            <div className="flex items-center gap-1 text-sm text-muted-foreground">
                              <Phone className="h-3 w-3" />
                              {client.contacto.telefone}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {client.dados_pessoais?.nif ? (
                          <div className="flex items-center gap-1">
                            <Hash className="h-3 w-3 text-muted-foreground" />
                            <span className="font-mono text-sm">
                              {client.dados_pessoais.nif}
                            </span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground text-sm">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center justify-center gap-2">
                          <Badge
                            variant={
                              client.active_processes_count > 0
                                ? "default"
                                : "secondary"
                            }
                          >
                            {client.active_processes_count || 0} activo(s)
                          </Badge>
                          {(client.process_ids?.length || 0) > client.active_processes_count && (
                            <Badge variant="outline">
                              {client.process_ids?.length || 0} total
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              data-testid={`client-actions-${client.id}`}
                            >
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => openCreateProcessDialog(client)}
                            >
                              <UserPlus className="h-4 w-4 mr-2" />
                              Novo Processo
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() =>
                                client.process_ids?.[0] &&
                                navigate(`/processes/${client.process_ids[0]}`)
                              }
                              disabled={!client.process_ids?.length}
                            >
                              <Eye className="h-4 w-4 mr-2" />
                              Ver Processos
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => handleDeleteClient(client.id)}
                              className="text-red-600"
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Eliminar
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Create Client Dialog */}
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <UserPlus className="h-5 w-5" />
                Novo Cliente
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="nome">Nome *</Label>
                <Input
                  id="nome"
                  value={newClient.nome}
                  onChange={(e) =>
                    setNewClient({ ...newClient, nome: e.target.value })
                  }
                  placeholder="Nome completo do cliente"
                  data-testid="new-client-name"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={newClient.email}
                    onChange={(e) =>
                      setNewClient({ ...newClient, email: e.target.value })
                    }
                    placeholder="email@exemplo.pt"
                    data-testid="new-client-email"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="telefone">Telefone</Label>
                  <Input
                    id="telefone"
                    value={newClient.telefone}
                    onChange={(e) =>
                      setNewClient({ ...newClient, telefone: e.target.value })
                    }
                    placeholder="912 345 678"
                    data-testid="new-client-phone"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="nif">NIF</Label>
                <Input
                  id="nif"
                  value={newClient.nif}
                  onChange={(e) =>
                    setNewClient({ ...newClient, nif: e.target.value })
                  }
                  placeholder="123456789"
                  maxLength={9}
                  data-testid="new-client-nif"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="notas">Notas</Label>
                <Textarea
                  id="notas"
                  value={newClient.notas}
                  onChange={(e) =>
                    setNewClient({ ...newClient, notas: e.target.value })
                  }
                  placeholder="Observações sobre o cliente..."
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowCreateDialog(false)}
              >
                Cancelar
              </Button>
              <Button onClick={handleCreateClient} data-testid="submit-new-client">
                Criar Cliente
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Create Process Dialog */}
        <Dialog open={showProcessDialog} onOpenChange={setShowProcessDialog}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Novo Processo para {selectedClient?.nome}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <p className="text-sm text-muted-foreground">
                Criar um novo processo de compra/financiamento para este cliente.
                Os dados pessoais e financeiros serão copiados automaticamente.
              </p>
              <div className="space-y-2">
                <Label>Tipo de Processo</Label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { value: "credito_habitacao", label: "Crédito Habitação" },
                    { value: "compra_direta", label: "Compra Directa" },
                    { value: "arrendamento", label: "Arrendamento" },
                    { value: "consultoria", label: "Consultoria" },
                  ].map((type) => (
                    <Button
                      key={type.value}
                      variant={
                        newProcessType === type.value ? "default" : "outline"
                      }
                      className="justify-start"
                      onClick={() => setNewProcessType(type.value)}
                    >
                      <Building2 className="h-4 w-4 mr-2" />
                      {type.label}
                    </Button>
                  ))}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowProcessDialog(false)}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleCreateProcess}
                data-testid="submit-new-process"
              >
                <Plus className="h-4 w-4 mr-2" />
                Criar Processo
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
}
