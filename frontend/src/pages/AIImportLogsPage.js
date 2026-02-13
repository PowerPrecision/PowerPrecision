/**
 * AIImportLogsPage - Logs de Importação IA
 * Mostra logs de importação massiva com dados organizados por categorias:
 * - Dados Pessoais
 * - Imóvel
 * - Financiamento
 * - Outros
 */
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { ScrollArea } from "../components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
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
  CheckCircle,
  XCircle,
  Eye,
  RefreshCw,
  Filter,
  ChevronLeft,
  ChevronRight,
  FileText,
  User,
  Home,
  Banknote,
  MoreHorizontal,
  Download,
  Clock,
  TrendingUp,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { pt } from "date-fns/locale";

const API_URL = process.env.REACT_APP_BACKEND_URL || "";

// Mapeamento de tipos de documento para ícones e labels
const documentTypeConfig = {
  cc: { label: "Cartão de Cidadão", icon: "🪪" },
  irs: { label: "Declaração IRS", icon: "📄" },
  recibo_vencimento: { label: "Recibo de Vencimento", icon: "💰" },
  contrato_trabalho: { label: "Contrato de Trabalho", icon: "📝" },
  extrato_bancario: { label: "Extrato Bancário", icon: "🏦" },
  caderneta_predial: { label: "Caderneta Predial", icon: "🏠" },
  outro: { label: "Outro Documento", icon: "📎" },
};

// Componente para exibir dados categorizados em tabs
const CategorizedDataView = ({ categorizedData }) => {
  if (!categorizedData || Object.keys(categorizedData).length === 0) {
    return (
      <div className="text-center py-4 text-muted-foreground">
        Sem dados extraídos
      </div>
    );
  }

  const categoryConfig = {
    dados_pessoais: { label: "Dados Pessoais", icon: User, color: "text-blue-600" },
    imovel: { label: "Imóvel", icon: Home, color: "text-green-600" },
    financiamento: { label: "Financiamento", icon: Banknote, color: "text-purple-600" },
    outros: { label: "Outros", icon: MoreHorizontal, color: "text-gray-600" },
  };

  const availableCategories = Object.keys(categorizedData).filter(
    (key) => Object.keys(categorizedData[key]).length > 0
  );

  if (availableCategories.length === 0) {
    return (
      <div className="text-center py-4 text-muted-foreground">
        Sem dados para mostrar
      </div>
    );
  }

  return (
    <Tabs defaultValue={availableCategories[0]} className="w-full">
      <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${availableCategories.length}, 1fr)` }}>
        {availableCategories.map((category) => {
          const config = categoryConfig[category] || categoryConfig.outros;
          const Icon = config.icon;
          const count = Object.keys(categorizedData[category]).length;
          return (
            <TabsTrigger key={category} value={category} className="gap-2">
              <Icon className={`h-4 w-4 ${config.color}`} />
              <span className="hidden sm:inline">{config.label}</span>
              <Badge variant="secondary" className="ml-1 text-xs">{count}</Badge>
            </TabsTrigger>
          );
        })}
      </TabsList>

      {availableCategories.map((category) => (
        <TabsContent key={category} value={category} className="mt-4">
          <div className="grid gap-3">
            {Object.entries(categorizedData[category]).map(([key, value]) => (
              <div key={key} className="flex justify-between items-start p-3 bg-muted/30 rounded-lg">
                <span className="text-sm font-medium text-muted-foreground capitalize">
                  {key.replace(/_/g, " ")}
                </span>
                <span className="text-sm font-semibold text-right max-w-[60%] break-words">
                  {typeof value === "object" ? JSON.stringify(value) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </TabsContent>
      ))}
    </Tabs>
  );
};

const AIImportLogsPage = () => {
  const { token } = useAuth();
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  // Filtros
  const [statusFilter, setStatusFilter] = useState("");
  const [clientFilter, setClientFilter] = useState("");
  const [docTypeFilter, setDocTypeFilter] = useState("");
  const [daysFilter, setDaysFilter] = useState("7");

  // Dialog de detalhes
  const [selectedLog, setSelectedLog] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("page", page);
      params.append("limit", "25");
      params.append("days", daysFilter);
      if (statusFilter) params.append("status", statusFilter);
      if (clientFilter) params.append("client_name", clientFilter);
      if (docTypeFilter) params.append("document_type", docTypeFilter);

      const response = await fetch(`${API_URL}/api/admin/ai-import-logs-v2?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
        setTotalPages(data.pagination?.total_pages || 1);
        setTotal(data.pagination?.total || 0);
        setStats(data.stats || null);
      } else {
        toast.error("Erro ao carregar logs de importação");
      }
    } catch (error) {
      console.error("Erro:", error);
      toast.error("Erro de ligação");
    } finally {
      setLoading(false);
    }
  }, [token, page, statusFilter, clientFilter, docTypeFilter, daysFilter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleMarkResolved = async (logId) => {
    try {
      const response = await fetch(`${API_URL}/api/admin/ai-import-logs/${logId}/resolve`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        toast.success("Log marcado como resolvido");
        fetchLogs();
        if (selectedLog?.id === logId) {
          setSelectedLog({ ...selectedLog, resolved: true });
        }
      }
    } catch (error) {
      toast.error("Erro ao marcar como resolvido");
    }
  };

  const openDetails = async (log) => {
    setSelectedLog(log);
    setShowDetails(true);
    
    // Buscar detalhes completos se não tiver dados categorizados
    if (!log.categorized_data) {
      setLoadingDetail(true);
      try {
        const response = await fetch(`${API_URL}/api/admin/ai-import-logs-v2/${log.id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const detail = await response.json();
          setSelectedLog(detail);
        }
      } catch (error) {
        console.error("Erro ao carregar detalhes:", error);
      } finally {
        setLoadingDetail(false);
      }
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "—";
    try {
      return format(new Date(dateStr), "dd/MM/yyyy HH:mm", { locale: pt });
    } catch {
      return dateStr;
    }
  };

  const getDocTypeConfig = (type) => {
    return documentTypeConfig[type] || documentTypeConfig.outro;
  };

  if (loading && logs.length === 0) {
    return (
      <DashboardLayout title="Logs de Importação IA">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Logs de Importação IA">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" data-testid="import-logs-title">
              Logs de Importação IA
            </h1>
            <p className="text-muted-foreground">
              Visualize sucessos e erros das importações massivas
            </p>
          </div>
          <Button variant="outline" onClick={fetchLogs} data-testid="refresh-import-logs">
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <FileText className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total</p>
                    <p className="text-2xl font-bold">{stats.total}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Sucesso</p>
                    <p className="text-2xl font-bold text-green-600">{stats.success}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-100 rounded-lg">
                    <XCircle className="h-5 w-5 text-red-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Erros</p>
                    <p className="text-2xl font-bold text-red-600">{stats.error}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <TrendingUp className="h-5 w-5 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Campos Actualizados</p>
                    <p className="text-2xl font-bold text-purple-600">{stats.fields_updated}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filtros */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filtros
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div>
                <Label className="text-xs">Estado</Label>
                <Select value={statusFilter || "all"} onValueChange={(v) => { setStatusFilter(v === "all" ? "" : v); setPage(1); }}>
                  <SelectTrigger data-testid="status-filter">
                    <SelectValue placeholder="Todos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="success">Sucesso</SelectItem>
                    <SelectItem value="error">Erro</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Tipo Documento</Label>
                <Select value={docTypeFilter || "all"} onValueChange={(v) => { setDocTypeFilter(v === "all" ? "" : v); setPage(1); }}>
                  <SelectTrigger data-testid="doctype-filter">
                    <SelectValue placeholder="Todos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="cc">Cartão de Cidadão</SelectItem>
                    <SelectItem value="irs">IRS</SelectItem>
                    <SelectItem value="recibo_vencimento">Recibo Vencimento</SelectItem>
                    <SelectItem value="contrato_trabalho">Contrato Trabalho</SelectItem>
                    <SelectItem value="extrato_bancario">Extrato Bancário</SelectItem>
                    <SelectItem value="caderneta_predial">Caderneta Predial</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Cliente</Label>
                <Input
                  placeholder="Nome do cliente"
                  value={clientFilter}
                  onChange={(e) => setClientFilter(e.target.value)}
                  data-testid="client-filter"
                />
              </div>
              <div>
                <Label className="text-xs">Período</Label>
                <Select value={daysFilter} onValueChange={(v) => { setDaysFilter(v); setPage(1); }}>
                  <SelectTrigger data-testid="days-filter">
                    <SelectValue placeholder="7 dias" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">Últimas 24h</SelectItem>
                    <SelectItem value="7">Últimos 7 dias</SelectItem>
                    <SelectItem value="30">Últimos 30 dias</SelectItem>
                    <SelectItem value="90">Últimos 90 dias</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end">
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => {
                    setStatusFilter("");
                    setClientFilter("");
                    setDocTypeFilter("");
                    setDaysFilter("7");
                    setPage(1);
                  }}
                >
                  Limpar Filtros
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tabela de Logs */}
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-24">Estado</TableHead>
                  <TableHead className="w-32">Tipo Doc.</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Ficheiro</TableHead>
                  <TableHead className="w-24">Campos</TableHead>
                  <TableHead className="w-40">Data</TableHead>
                  <TableHead className="w-20">Acções</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      Nenhum log de importação encontrado
                    </TableCell>
                  </TableRow>
                ) : (
                  logs.map((log) => {
                    const docConfig = getDocTypeConfig(log.document_type);
                    return (
                      <TableRow
                        key={log.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => openDetails(log)}
                        data-testid={`import-log-row-${log.id}`}
                      >
                        <TableCell>
                          {log.status === "success" ? (
                            <Badge variant="outline" className="bg-green-100 text-green-800 gap-1">
                              <CheckCircle className="h-3 w-3" />
                              Sucesso
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-red-100 text-red-800 gap-1">
                              <XCircle className="h-3 w-3" />
                              Erro
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className="text-sm flex items-center gap-1">
                            <span>{docConfig.icon}</span>
                            <span className="hidden md:inline">{docConfig.label}</span>
                          </span>
                        </TableCell>
                        <TableCell className="font-medium">{log.client_name}</TableCell>
                        <TableCell className="max-w-xs truncate text-sm text-muted-foreground">
                          {log.filename}
                        </TableCell>
                        <TableCell>
                          {log.fields_count > 0 ? (
                            <Badge variant="secondary">{log.fields_count}</Badge>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(log.timestamp)}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              openDetails(log);
                            }}
                            data-testid={`view-log-${log.id}`}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Paginação */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              Página {page} de {totalPages} ({total} registos)
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Dialog de Detalhes */}
        <Dialog open={showDetails} onOpenChange={setShowDetails}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {selectedLog?.status === "success" ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600" />
                )}
                Detalhes da Importação
              </DialogTitle>
              <DialogDescription>
                {selectedLog?.filename} - {selectedLog?.client_name}
              </DialogDescription>
            </DialogHeader>

            {loadingDetail ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : selectedLog && (
              <div className="space-y-6">
                {/* Info básica */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <Label className="text-xs text-muted-foreground">Estado</Label>
                    <div className="mt-1">
                      {selectedLog.status === "success" ? (
                        <Badge className="bg-green-100 text-green-800">Sucesso</Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-800">Erro</Badge>
                      )}
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Tipo Documento</Label>
                    <p className="mt-1 text-sm font-medium">
                      {getDocTypeConfig(selectedLog.document_type).label}
                    </p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Data</Label>
                    <p className="mt-1 text-sm">{formatDate(selectedLog.timestamp)}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Campos Actualizados</Label>
                    <p className="mt-1 text-sm font-bold text-purple-600">
                      {selectedLog.fields_count || 0}
                    </p>
                  </div>
                </div>

                {/* Erro (se houver) */}
                {selectedLog.error && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                      <div>
                        <p className="font-medium text-red-800">Erro de Importação</p>
                        <p className="text-sm text-red-700 mt-1">{selectedLog.error}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Campos actualizados */}
                {selectedLog.updated_fields && selectedLog.updated_fields.length > 0 && (
                  <div>
                    <Label className="text-xs text-muted-foreground mb-2 block">
                      Campos Actualizados
                    </Label>
                    <div className="flex flex-wrap gap-2">
                      {selectedLog.updated_fields.map((field, idx) => (
                        <Badge key={idx} variant="outline" className="bg-green-50 text-green-700">
                          {field}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Dados categorizados em tabs */}
                {selectedLog.categorized_data && (
                  <div>
                    <Label className="text-xs text-muted-foreground mb-3 block">
                      Dados Guardados por Categoria
                    </Label>
                    <Card>
                      <CardContent className="pt-4">
                        <CategorizedDataView categorizedData={selectedLog.categorized_data} />
                      </CardContent>
                    </Card>
                  </div>
                )}

                {/* Info adicional */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <Label className="text-xs text-muted-foreground">Pasta</Label>
                    <p className="mt-1 font-mono text-xs bg-muted p-2 rounded">
                      {selectedLog.folder_name || "—"}
                    </p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Utilizador</Label>
                    <p className="mt-1">{selectedLog.user_email || "—"}</p>
                  </div>
                </div>
              </div>
            )}

            <DialogFooter className="gap-2">
              {selectedLog && selectedLog.status === "error" && !selectedLog.resolved && (
                <Button
                  variant="outline"
                  onClick={() => handleMarkResolved(selectedLog.id)}
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Marcar como Resolvido
                </Button>
              )}
              <Button variant="ghost" onClick={() => setShowDetails(false)}>
                Fechar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
};

export default AIImportLogsPage;
