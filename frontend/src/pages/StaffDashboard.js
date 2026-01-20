import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import DashboardLayout from "../layouts/DashboardLayout";
import KanbanBoard from "../components/KanbanBoard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Badge } from "../components/ui/badge";
import { Loader2, LayoutGrid, Calendar, Users, Settings, FileText, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { getStats, getUsers, getUpcomingExpiries, getCalendarDeadlines } from "../services/api";

const roleLabels = {
  admin: "Administrador",
  ceo: "CEO",
  consultor: "Consultor",
  mediador: "Mediador",
  consultor_mediador: "Consultor/Mediador",
  cliente: "Cliente"
};

const StaffDashboard = () => {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({});
  const [users, setUsers] = useState([]);
  const [expiries, setExpiries] = useState([]);
  const [deadlines, setDeadlines] = useState([]);
  const [activeTab, setActiveTab] = useState("kanban");

  const isAdmin = user?.role === "admin";
  const isCeo = user?.role === "ceo";
  const canManageUsers = isAdmin;
  const canManageWorkflow = isAdmin;
  const canSeeAllStats = isAdmin || isCeo;

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsRes, usersRes, expiriesRes, deadlinesRes] = await Promise.all([
        getStats().catch(() => ({ data: {} })),
        canSeeAllStats ? getUsers().catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
        getUpcomingExpiries(60).catch(() => ({ data: [] })),
        getCalendarDeadlines().catch(() => ({ data: [] })),
      ]);
      setStats(statsRes.data);
      setUsers(usersRes.data);
      setExpiries(expiriesRes.data);
      setDeadlines(deadlinesRes.data);
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
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
      <div className="space-y-6" data-testid="staff-dashboard">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Olá, {user?.name?.split(' ')[0]}</h1>
            <p className="text-muted-foreground">
              <Badge variant="outline" className="mr-2">{roleLabels[user?.role] || user?.role}</Badge>
              {canSeeAllStats ? `${stats.total_processes || 0} processos no sistema` : "Os seus processos atribuídos"}
            </p>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-primary">{stats.total_processes || 0}</p>
                <p className="text-sm text-muted-foreground">Processos</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-orange-500">{stats.pending_deadlines || 0}</p>
                <p className="text-sm text-muted-foreground">Prazos Pendentes</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-red-500">{expiries.length}</p>
                <p className="text-sm text-muted-foreground">Docs a Expirar</p>
              </div>
            </CardContent>
          </Card>
          {canSeeAllStats && (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-3xl font-bold text-emerald-500">{users.length}</p>
                  <p className="text-sm text-muted-foreground">Utilizadores</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="flex-wrap">
            <TabsTrigger value="kanban" className="gap-2">
              <LayoutGrid className="h-4 w-4" />
              Quadro Kanban
            </TabsTrigger>
            <TabsTrigger value="calendar" className="gap-2">
              <Calendar className="h-4 w-4" />
              Calendário
            </TabsTrigger>
            <TabsTrigger value="documents" className="gap-2">
              <FileText className="h-4 w-4" />
              Documentos
            </TabsTrigger>
            {canManageUsers && (
              <TabsTrigger value="users" className="gap-2">
                <Users className="h-4 w-4" />
                Utilizadores
              </TabsTrigger>
            )}
            {canManageWorkflow && (
              <TabsTrigger value="settings" className="gap-2">
                <Settings className="h-4 w-4" />
                Configurações
              </TabsTrigger>
            )}
          </TabsList>

          {/* Kanban Tab */}
          <TabsContent value="kanban" className="mt-6">
            <KanbanBoard token={token} />
          </TabsContent>

          {/* Calendar Tab */}
          <TabsContent value="calendar" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Próximos Prazos</CardTitle>
                <CardDescription>Prazos e eventos agendados</CardDescription>
              </CardHeader>
              <CardContent>
                {deadlines.length === 0 ? (
                  <p className="text-muted-foreground text-center py-8">Nenhum prazo agendado</p>
                ) : (
                  <div className="space-y-3">
                    {deadlines.slice(0, 10).map((deadline) => (
                      <div key={deadline.id} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                        <div>
                          <p className="font-medium">{deadline.title}</p>
                          <p className="text-sm text-muted-foreground">{deadline.client_name}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-medium">{new Date(deadline.due_date).toLocaleDateString('pt-PT')}</p>
                          <Badge variant={deadline.priority === "high" ? "destructive" : "outline"}>
                            {deadline.priority === "high" ? "Alta" : deadline.priority === "medium" ? "Média" : "Baixa"}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Documents Tab */}
          <TabsContent value="documents" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Documentos a Expirar</CardTitle>
                <CardDescription>Documentos próximos da data de validade (60 dias)</CardDescription>
              </CardHeader>
              <CardContent>
                {expiries.length === 0 ? (
                  <p className="text-muted-foreground text-center py-8">Nenhum documento a expirar</p>
                ) : (
                  <div className="space-y-3">
                    {expiries.map((doc) => (
                      <div key={doc.id} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                        <div>
                          <p className="font-medium">{doc.document_name}</p>
                          <p className="text-sm text-muted-foreground">{doc.client_name} • {doc.document_type}</p>
                        </div>
                        <Badge variant="destructive">
                          {new Date(doc.expiry_date).toLocaleDateString('pt-PT')}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Users Tab (Admin only) */}
          {canManageUsers && (
            <TabsContent value="users" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Gestão de Utilizadores</CardTitle>
                  <CardDescription>Para gestão completa, aceda ao painel de administração</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {users.map((u) => (
                      <div key={u.id} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                        <div>
                          <p className="font-medium">{u.name}</p>
                          <p className="text-sm text-muted-foreground">{u.email}</p>
                        </div>
                        <Badge>{roleLabels[u.role] || u.role}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          )}

          {/* Settings Tab (Admin only) */}
          {canManageWorkflow && (
            <TabsContent value="settings" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Configurações do Sistema</CardTitle>
                  <CardDescription>Para gestão completa, aceda ao painel de administração</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">
                    Use o menu lateral para aceder à gestão completa de utilizadores e workflow.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          )}
        </Tabs>
      </div>
    </DashboardLayout>
  );
};

export default StaffDashboard;
