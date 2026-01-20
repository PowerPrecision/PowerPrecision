import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { getProcesses, getStats } from "../services/api";
import {
  FileText,
  Search,
  Clock,
  ArrowRight,
  CreditCard,
  Users,
  CheckCircle,
  XCircle,
  AlertCircle,
  Banknote,
} from "lucide-react";
import { toast } from "sonner";
import { format, parseISO } from "date-fns";
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

const MediadorDashboard = () => {
  const [processes, setProcesses] = useState([]);
  const [filteredProcesses, setFilteredProcesses] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    filterProcesses();
  }, [processes, searchTerm, statusFilter]);

  const fetchData = async () => {
    try {
      const [processesRes, statsRes] = await Promise.all([
        getProcesses(),
        getStats(),
      ]);
      setProcesses(processesRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  };

  const filterProcesses = () => {
    let filtered = [...processes];

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (p) =>
          p.client_name.toLowerCase().includes(term) ||
          p.client_email.toLowerCase().includes(term) ||
          p.id.toLowerCase().includes(term)
      );
    }

    if (statusFilter !== "all") {
      filtered = filtered.filter((p) => p.status === statusFilter);
    }

    setFilteredProcesses(filtered);
  };

  if (loading) {
    return (
      <DashboardLayout title="Dashboard Mediador">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Dashboard Mediador">
      <div className="space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-border card-hover">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Processos</p>
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
                  <p className="text-sm text-muted-foreground">Aguardam Autorização</p>
                  <p className="text-3xl font-bold font-mono mt-1">
                    {stats?.bank_authorization || 0}
                  </p>
                </div>
                <div className="h-12 w-12 bg-orange-100 rounded-md flex items-center justify-center">
                  <Banknote className="h-6 w-6 text-orange-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border card-hover">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Aprovados</p>
                  <p className="text-3xl font-bold font-mono mt-1">
                    {stats?.approved || 0}
                  </p>
                </div>
                <div className="h-12 w-12 bg-emerald-100 rounded-md flex items-center justify-center">
                  <CheckCircle className="h-6 w-6 text-emerald-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="border-border card-hover">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Rejeitados</p>
                  <p className="text-3xl font-bold font-mono mt-1">
                    {stats?.rejected || 0}
                  </p>
                </div>
                <div className="h-12 w-12 bg-red-100 rounded-md flex items-center justify-center">
                  <XCircle className="h-6 w-6 text-red-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="border-border">
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Pesquisar por nome, email ou ID..."
                  className="pl-10"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  data-testid="search-input"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-48" data-testid="status-filter">
                  <SelectValue placeholder="Filtrar por estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos os estados</SelectItem>
                  <SelectItem value="pedido_inicial">Pedido Inicial</SelectItem>
                  <SelectItem value="em_analise">Em Análise</SelectItem>
                  <SelectItem value="autorizacao_bancaria">Autorização Bancária</SelectItem>
                  <SelectItem value="aprovado">Aprovado</SelectItem>
                  <SelectItem value="rejeitado">Rejeitado</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Process List */}
        <Card className="border-border">
          <CardHeader>
            <CardTitle className="text-lg">Processos de Crédito</CardTitle>
            <CardDescription>
              Processos de crédito para gerir e aprovar
            </CardDescription>
          </CardHeader>
          <CardContent>
            {filteredProcesses.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <CreditCard className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Nenhum processo encontrado</p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredProcesses.map((process) => (
                  <div
                    key={process.id}
                    className="flex items-center justify-between p-4 bg-muted/30 rounded-md hover:bg-muted/50 transition-colors cursor-pointer"
                    onClick={() => navigate(`/processo/${process.id}`)}
                    data-testid={`process-row-${process.id}`}
                  >
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 bg-primary/10 rounded-md flex items-center justify-center">
                        <Users className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">{process.client_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {process.client_email}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right hidden sm:block">
                        <p className="text-sm font-medium">
                          {typeLabels[process.process_type]}
                        </p>
                        <p className="text-xs text-muted-foreground flex items-center gap-1 justify-end">
                          <Clock className="h-3 w-3" />
                          {format(parseISO(process.created_at), "dd/MM/yyyy", {
                            locale: pt,
                          })}
                        </p>
                      </div>
                      <Badge className={`status-${process.status}`}>
                        {statusLabels[process.status]}
                      </Badge>
                      <Button variant="ghost" size="icon">
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default MediadorDashboard;
