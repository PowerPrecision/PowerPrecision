import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
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
  AlertCircle,
  AlertTriangle,
  Info,
  XCircle,
  Check,
  Eye,
  Trash2,
  RefreshCw,
  Filter,
  ChevronLeft,
  ChevronRight,
  Clock,
  Server,
  Activity,
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { pt } from "date-fns/locale";

const API_URL = process.env.REACT_APP_BACKEND_URL || "";

const severityConfig = {
  info: { icon: Info, color: "bg-blue-100 text-blue-800 border-blue-200", label: "Info" },
  warning: { icon: AlertTriangle, color: "bg-yellow-100 text-yellow-800 border-yellow-200", label: "Aviso" },
  error: { icon: AlertCircle, color: "bg-red-100 text-red-800 border-red-200", label: "Erro" },
  critical: { icon: XCircle, color: "bg-red-200 text-red-900 border-red-300", label: "Crítico" },
};

const SystemLogsPage = () => {
  const { token } = useAuth();
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  
  // Filtros
  const [severityFilter, setSeverityFilter] = useState("");
  const [componentFilter, setComponentFilter] = useState("");
  const [resolvedFilter, setResolvedFilter] = useState("");
  const [daysFilter, setDaysFilter] = useState("7");
  
  // Dialog de detalhes
  const [selectedLog, setSelectedLog] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [resolveNotes, setResolveNotes] = useState("");
  const [resolving, setResolving] = useState(false);
  
  // Acções em lote
  const [selectedIds, setSelectedIds] = useState([]);

  const fetchLogs = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      params.append("page", page);
      params.append("limit", "25");
      params.append("days", daysFilter);
      if (severityFilter) params.append("severity", severityFilter);
      if (componentFilter) params.append("component", componentFilter);
      if (resolvedFilter !== "") params.append("resolved", resolvedFilter === "true");
      
      const response = await fetch(`${API_URL}/api/admin/system-logs?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setLogs(data.errors || []);
        setTotalPages(data.pages || 1);
        setTotal(data.total || 0);
      } else {
        toast.error("Erro ao carregar logs");
      }
    } catch (error) {
      console.error("Erro:", error);
      toast.error("Erro de ligação");
    } finally {
      setLoading(false);
    }
  }, [token, page, severityFilter, componentFilter, resolvedFilter, daysFilter]);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/admin/system-logs/stats?days=${daysFilter}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error("Erro ao carregar estatísticas:", error);
    }
  };

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [fetchLogs]);

  const handleMarkAsRead = async (ids) => {
    try {
      const response = await fetch(`${API_URL}/api/admin/system-logs/mark-read`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ error_ids: ids }),
      });
      
      if (response.ok) {
        toast.success("Marcados como lidos");
        fetchLogs();
        setSelectedIds([]);
      }
    } catch (error) {
      toast.error("Erro ao marcar como lidos");
    }
  };

  const handleResolve = async () => {
    if (!selectedLog) return;
    
    setResolving(true);
    try {
      const response = await fetch(`${API_URL}/api/admin/system-logs/${selectedLog.id}/resolve`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ notes: resolveNotes }),
      });
      
      if (response.ok) {
        toast.success("Erro marcado como resolvido");
        setShowDetails(false);
        setResolveNotes("");
        fetchLogs();
        fetchStats();
      }
    } catch (error) {
      toast.error("Erro ao resolver");
    } finally {
      setResolving(false);
    }
  };

  const handleCleanup = async () => {
    if (!confirm("Tem certeza que deseja eliminar logs com mais de 90 dias?")) return;
    
    try {
      const response = await fetch(`${API_URL}/api/admin/system-logs/cleanup?days=90`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        toast.success(`${data.deleted_count} logs eliminados`);
        fetchLogs();
        fetchStats();
      }
    } catch (error) {
      toast.error("Erro ao limpar logs");
    }
  };

  const openDetails = (log) => {
    setSelectedLog(log);
    setResolveNotes("");
    setShowDetails(true);
  };

  const toggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (selectedIds.length === logs.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(logs.map((l) => l.id));
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

  const SeverityBadge = ({ severity }) => {
    const config = severityConfig[severity] || severityConfig.info;
    const Icon = config.icon;
    return (
      <Badge variant="outline" className={`${config.color} gap-1`}>
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  if (loading) {
    return (
      <DashboardLayout title="Logs do Sistema">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Logs do Sistema">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold" data-testid="system-logs-title">Logs de Erro do Sistema</h1>
            <p className="text-muted-foreground">
              Monitorize e resolva erros da aplicação
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => { fetchLogs(); fetchStats(); }} data-testid="refresh-logs-btn">
              <RefreshCw className="h-4 w-4 mr-2" />
              Actualizar
            </Button>
            <Button variant="destructive" size="sm" onClick={handleCleanup} data-testid="cleanup-logs-btn">
              <Trash2 className="h-4 w-4 mr-2" />
              Limpar Antigos
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Activity className="h-5 w-5 text-blue-500" />
                  <div>
                    <p className="text-sm text-muted-foreground">Total</p>
                    <p className="text-2xl font-bold">{stats.total}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-yellow-500" />
                  <div>
                    <p className="text-sm text-muted-foreground">Não Lidos</p>
                    <p className="text-2xl font-bold">{stats.unread}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-orange-500" />
                  <div>
                    <p className="text-sm text-muted-foreground">Por Resolver</p>
                    <p className="text-2xl font-bold">{stats.unresolved}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className={stats.critical > 0 ? "border-red-500" : ""}>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <XCircle className={`h-5 w-5 ${stats.critical > 0 ? "text-red-500" : "text-gray-400"}`} />
                  <div>
                    <p className="text-sm text-muted-foreground">Críticos</p>
                    <p className={`text-2xl font-bold ${stats.critical > 0 ? "text-red-600" : ""}`}>
                      {stats.critical}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Server className="h-5 w-5 text-purple-500" />
                  <div>
                    <p className="text-sm text-muted-foreground">Componentes</p>
                    <p className="text-2xl font-bold">{Object.keys(stats.by_component || {}).length}</p>
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
                <Label className="text-xs">Severidade</Label>
                <Select value={severityFilter || "all"} onValueChange={(v) => setSeverityFilter(v === "all" ? "" : v)}>
                  <SelectTrigger data-testid="severity-filter">
                    <SelectValue placeholder="Todas" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="warning">Aviso</SelectItem>
                    <SelectItem value="error">Erro</SelectItem>
                    <SelectItem value="critical">Crítico</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Componente</Label>
                <Input
                  placeholder="Ex: scraper"
                  value={componentFilter}
                  onChange={(e) => setComponentFilter(e.target.value)}
                  data-testid="component-filter"
                />
              </div>
              <div>
                <Label className="text-xs">Estado</Label>
                <Select value={resolvedFilter || "all"} onValueChange={(v) => setResolvedFilter(v === "all" ? "" : v)}>
                  <SelectTrigger data-testid="resolved-filter">
                    <SelectValue placeholder="Todos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="false">Por Resolver</SelectItem>
                    <SelectItem value="true">Resolvidos</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Período</Label>
                <Select value={daysFilter} onValueChange={setDaysFilter}>
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
                    setSeverityFilter("");
                    setComponentFilter("");
                    setResolvedFilter("");
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

        {/* Acções em lote */}
        {selectedIds.length > 0 && (
          <div className="flex items-center gap-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <span className="text-sm font-medium">
              {selectedIds.length} seleccionados
            </span>
            <Button size="sm" variant="outline" onClick={() => handleMarkAsRead(selectedIds)}>
              <Eye className="h-4 w-4 mr-1" />
              Marcar como Lidos
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setSelectedIds([])}>
              Cancelar
            </Button>
          </div>
        )}

        {/* Tabela de Logs */}
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <input
                      type="checkbox"
                      checked={selectedIds.length === logs.length && logs.length > 0}
                      onChange={selectAll}
                      className="rounded"
                    />
                  </TableHead>
                  <TableHead className="w-32">Severidade</TableHead>
                  <TableHead className="w-32">Componente</TableHead>
                  <TableHead>Mensagem</TableHead>
                  <TableHead className="w-40">Data</TableHead>
                  <TableHead className="w-24">Estado</TableHead>
                  <TableHead className="w-20">Acções</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      Nenhum log encontrado
                    </TableCell>
                  </TableRow>
                ) : (
                  logs.map((log) => (
                    <TableRow
                      key={log.id}
                      className={`cursor-pointer hover:bg-muted/50 ${!log.read ? "bg-yellow-50/50 dark:bg-yellow-900/10" : ""}`}
                      onClick={() => openDetails(log)}
                    >
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(log.id)}
                          onChange={() => toggleSelect(log.id)}
                          className="rounded"
                        />
                      </TableCell>
                      <TableCell>
                        <SeverityBadge severity={log.severity} />
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                          {log.component || "geral"}
                        </span>
                      </TableCell>
                      <TableCell className="max-w-md truncate">
                        {log.message}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(log.timestamp)}
                      </TableCell>
                      <TableCell>
                        {log.resolved ? (
                          <Badge variant="outline" className="bg-green-100 text-green-800">
                            <Check className="h-3 w-3 mr-1" />
                            Resolvido
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="bg-orange-100 text-orange-800">
                            Pendente
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); openDetails(log); }}>
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
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
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {selectedLog && <SeverityBadge severity={selectedLog.severity} />}
                Detalhes do Erro
              </DialogTitle>
              <DialogDescription>
                {selectedLog?.type} em {selectedLog?.component || "geral"}
              </DialogDescription>
            </DialogHeader>

            {selectedLog && (
              <div className="space-y-4">
                <div>
                  <Label className="text-xs text-muted-foreground">Mensagem</Label>
                  <p className="p-3 bg-muted rounded-lg text-sm">{selectedLog.message}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-muted-foreground">Componente</Label>
                    <p className="font-mono text-sm">{selectedLog.component || "geral"}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Tipo</Label>
                    <p className="font-mono text-sm">{selectedLog.type}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Data</Label>
                    <p className="text-sm">{formatDate(selectedLog.timestamp)}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Request Path</Label>
                    <p className="font-mono text-sm">{selectedLog.request_path || "—"}</p>
                  </div>
                </div>

                {selectedLog.details && Object.keys(selectedLog.details).length > 0 && (
                  <div>
                    <Label className="text-xs text-muted-foreground">Detalhes Adicionais</Label>
                    <ScrollArea className="h-40 rounded-lg border p-3">
                      <pre className="text-xs font-mono whitespace-pre-wrap">
                        {JSON.stringify(selectedLog.details, null, 2)}
                      </pre>
                    </ScrollArea>
                  </div>
                )}

                {selectedLog.resolved ? (
                  <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                    <p className="text-sm text-green-800 dark:text-green-200">
                      <Check className="h-4 w-4 inline mr-1" />
                      Resolvido por {selectedLog.resolved_by} em {formatDate(selectedLog.resolved_at)}
                    </p>
                    {selectedLog.notes && (
                      <p className="text-sm mt-2 text-muted-foreground">{selectedLog.notes}</p>
                    )}
                  </div>
                ) : (
                  <div>
                    <Label className="text-xs text-muted-foreground">Notas de Resolução</Label>
                    <Textarea
                      placeholder="Descreva como resolveu o problema..."
                      value={resolveNotes}
                      onChange={(e) => setResolveNotes(e.target.value)}
                      rows={3}
                    />
                  </div>
                )}
              </div>
            )}

            <DialogFooter className="gap-2">
              {!selectedLog?.read && (
                <Button variant="outline" onClick={() => handleMarkAsRead([selectedLog?.id])}>
                  <Eye className="h-4 w-4 mr-2" />
                  Marcar como Lido
                </Button>
              )}
              {!selectedLog?.resolved && (
                <Button onClick={handleResolve} disabled={resolving}>
                  {resolving ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Check className="h-4 w-4 mr-2" />
                  )}
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

export default SystemLogsPage;
