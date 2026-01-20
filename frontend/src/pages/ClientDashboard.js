import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { getProcesses, getDeadlines, getStats } from "../services/api";
import { 
  FileText, 
  PlusCircle, 
  Calendar, 
  Clock, 
  ArrowRight,
  Building2,
  CreditCard,
  AlertCircle
} from "lucide-react";
import { toast } from "sonner";
import { format, parseISO, isAfter, isBefore, addDays } from "date-fns";
import { pt } from "date-fns/locale";

const statusLabels = {
  pedido_inicial: "Pedido Inicial",
  em_analise: "Em Análise",
  autorizacao_bancaria: "Autorização Bancária",
  aprovado: "Aprovado",
  rejeitado: "Rejeitado",
};

const typeLabels = {
  credito: "Crédito",
  imobiliaria: "Imobiliária",
  ambos: "Crédito + Imobiliária",
};

const typeIcons = {
  credito: CreditCard,
  imobiliaria: Building2,
  ambos: FileText,
};

const ClientDashboard = () => {
  const [processes, setProcesses] = useState([]);
  const [deadlines, setDeadlines] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [processesRes, deadlinesRes, statsRes] = await Promise.all([
        getProcesses(),
        getDeadlines(),
        getStats(),
      ]);
      setProcesses(processesRes.data);
      setDeadlines(deadlinesRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  };

  const upcomingDeadlines = deadlines
    .filter((d) => !d.completed && isAfter(parseISO(d.due_date), new Date()))
    .sort((a, b) => parseISO(a.due_date) - parseISO(b.due_date))
    .slice(0, 5);

  const urgentDeadlines = deadlines.filter(
    (d) =>
      !d.completed &&
      isBefore(parseISO(d.due_date), addDays(new Date(), 3)) &&
      isAfter(parseISO(d.due_date), new Date())
  );

  if (loading) {
    return (
      <DashboardLayout title="Dashboard">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Dashboard">
      <div className="space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="border-border card-hover">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total de Processos</p>
                  <p className="text-3xl font-bold font-mono mt-1">
                    {stats?.total_processes || 0}
                  </p>
                </div>
                <div className="h-12 w-12 bg-primary/10 rounded-md flex items-center justify-center">
                  <FileText className="h-6 w-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border card-hover">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Prazos Pendentes</p>
                  <p className="text-3xl font-bold font-mono mt-1">
                    {stats?.pending_deadlines || 0}
                  </p>
                </div>
                <div className="h-12 w-12 bg-orange-100 rounded-md flex items-center justify-center">
                  <Calendar className="h-6 w-6 text-orange-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border card-hover">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Prazos Urgentes</p>
                  <p className="text-3xl font-bold font-mono mt-1">
                    {urgentDeadlines.length}
                  </p>
                </div>
                <div className="h-12 w-12 bg-red-100 rounded-md flex items-center justify-center">
                  <AlertCircle className="h-6 w-6 text-red-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        {processes.length === 0 && (
          <Card className="border-border border-dashed">
            <CardContent className="p-8 text-center">
              <div className="h-16 w-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <PlusCircle className="h-8 w-8 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Comece agora</h3>
              <p className="text-muted-foreground mb-4">
                Ainda não tem processos. Crie o seu primeiro processo de crédito ou imobiliária.
              </p>
              <Button onClick={() => navigate("/cliente/novo-processo")} data-testid="new-process-btn">
                <PlusCircle className="h-4 w-4 mr-2" />
                Novo Processo
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Processes */}
        {processes.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Os Meus Processos</h2>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate("/cliente/novo-processo")}
                data-testid="new-process-btn"
              >
                <PlusCircle className="h-4 w-4 mr-2" />
                Novo Processo
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {processes.map((process) => {
                const TypeIcon = typeIcons[process.process_type] || FileText;
                return (
                  <Card
                    key={process.id}
                    className="border-border card-hover cursor-pointer"
                    onClick={() => navigate(`/processo/${process.id}`)}
                    data-testid={`process-card-${process.id}`}
                  >
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 bg-primary/10 rounded-md flex items-center justify-center">
                            <TypeIcon className="h-5 w-5 text-primary" />
                          </div>
                          <div>
                            <p className="font-semibold">
                              {typeLabels[process.process_type]}
                            </p>
                            <p className="text-xs text-muted-foreground font-mono">
                              {process.id.slice(0, 8)}...
                            </p>
                          </div>
                        </div>
                        <Badge className={`status-${process.status}`}>
                          {statusLabels[process.status]}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground flex items-center gap-1">
                          <Clock className="h-4 w-4" />
                          {format(parseISO(process.created_at), "dd MMM yyyy", {
                            locale: pt,
                          })}
                        </span>
                        <Button variant="ghost" size="sm" className="gap-1">
                          Ver detalhes
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {/* Upcoming Deadlines */}
        {upcomingDeadlines.length > 0 && (
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="text-lg">Próximos Prazos</CardTitle>
              <CardDescription>
                Prazos a cumprir nos próximos dias
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {upcomingDeadlines.map((deadline) => (
                  <div
                    key={deadline.id}
                    className="flex items-center justify-between p-3 bg-muted/50 rounded-md"
                    data-testid={`deadline-${deadline.id}`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          deadline.priority === "high"
                            ? "bg-red-500"
                            : deadline.priority === "medium"
                            ? "bg-yellow-500"
                            : "bg-slate-400"
                        }`}
                      />
                      <div>
                        <p className="font-medium text-sm">{deadline.title}</p>
                        {deadline.description && (
                          <p className="text-xs text-muted-foreground">
                            {deadline.description}
                          </p>
                        )}
                      </div>
                    </div>
                    <span className="text-sm font-mono text-muted-foreground">
                      {format(parseISO(deadline.due_date), "dd/MM/yyyy")}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default ClientDashboard;
