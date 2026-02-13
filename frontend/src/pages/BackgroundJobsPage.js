/**
 * BackgroundJobsPage - Página de Processos em Background
 * Permite visualizar o estado de importações e outros processos a correr
 */
import React, { useState, useEffect, useCallback } from "react";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { ScrollArea } from "../components/ui/scroll-area";
import { toast } from "sonner";
import {
  Activity,
  RefreshCw,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  Trash2,
  Play,
  AlertTriangle,
  FileText,
  Upload,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Mapeamento de tipos de job para ícones
const JOB_TYPE_ICONS = {
  bulk_import: Upload,
  document_analysis: FileText,
  email_sync: Activity,
  default: Play,
};

// Mapeamento de status para badges
const STATUS_CONFIG = {
  running: { label: "A correr", variant: "default", className: "bg-blue-500", icon: Loader2 },
  success: { label: "Concluído", variant: "default", className: "bg-green-500", icon: CheckCircle },
  failed: { label: "Falhado", variant: "destructive", icon: XCircle },
  cancelled: { label: "Cancelado", variant: "secondary", className: "bg-amber-500", icon: XCircle },
  pending: { label: "Pendente", variant: "secondary", icon: Clock },
};

// Componente de Job Individual
const JobCard = ({ job, onDelete, onCancel }) => {
  const Icon = JOB_TYPE_ICONS[job.type] || JOB_TYPE_ICONS.default;
  const statusConfig = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;
  const StatusIcon = statusConfig.icon;
  const [cancelling, setCancelling] = useState(false);
  
  const formatDate = (isoString) => {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleString("pt-PT", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const getDuration = () => {
    if (!job.started_at) return "-";
    const start = new Date(job.started_at);
    const end = job.finished_at ? new Date(job.finished_at) : new Date();
    const diffMs = end - start;
    const diffSecs = Math.floor(diffMs / 1000);
    
    if (diffSecs < 60) return `${diffSecs}s`;
    const diffMins = Math.floor(diffSecs / 60);
    if (diffMins < 60) return `${diffMins}m ${diffSecs % 60}s`;
    const diffHours = Math.floor(diffMins / 60);
    return `${diffHours}h ${diffMins % 60}m`;
  };

  return (
    <Card className={`transition-all ${job.status === 'running' ? 'border-blue-300 shadow-md' : ''}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          {/* Ícone e Info Principal */}
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className={`p-2.5 rounded-lg shrink-0 ${
              job.status === 'running' ? 'bg-blue-100 dark:bg-blue-900/30' :
              job.status === 'success' ? 'bg-green-100 dark:bg-green-900/30' :
              job.status === 'failed' ? 'bg-red-100 dark:bg-red-900/30' :
              'bg-gray-100 dark:bg-gray-800'
            }`}>
              <Icon className={`h-5 w-5 ${
                job.status === 'running' ? 'text-blue-600' :
                job.status === 'success' ? 'text-green-600' :
                job.status === 'failed' ? 'text-red-600' :
                'text-gray-600'
              }`} />
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="font-medium text-sm">
                  {job.type === 'bulk_import' ? 'Importação Massiva' :
                   job.type === 'document_analysis' ? 'Análise de Documentos' :
                   job.type === 'email_sync' ? 'Sincronização de Email' :
                   job.type}
                </h4>
                <Badge 
                  variant={statusConfig.variant}
                  className={`text-xs ${statusConfig.className || ''}`}
                >
                  <StatusIcon className={`h-3 w-3 mr-1 ${job.status === 'running' ? 'animate-spin' : ''}`} />
                  {statusConfig.label}
                </Badge>
              </div>
              
              {/* Detalhes */}
              <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                <span>Início: {formatDate(job.started_at)}</span>
                {job.finished_at && <span>Fim: {formatDate(job.finished_at)}</span>}
                <span>Duração: {getDuration()}</span>
              </div>
              
              {/* Progresso */}
              {job.status === 'running' && job.total > 0 && (
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span>{job.processed} de {job.total} processados</span>
                    <span>{job.progress}%</span>
                  </div>
                  <Progress value={job.progress} className="h-2" />
                </div>
              )}
              
              {/* Erros */}
              {job.errors > 0 && (
                <div className="flex items-center gap-1 mt-2 text-xs text-amber-600">
                  <AlertTriangle className="h-3 w-3" />
                  {job.errors} erro(s) durante processamento
                </div>
              )}
              
              {/* Mensagem de erro/sucesso */}
              {job.message && (
                <p className={`mt-2 text-xs ${
                  job.status === 'failed' ? 'text-red-600' : 'text-muted-foreground'
                }`}>
                  {job.message}
                </p>
              )}
              
              {/* Detalhes adicionais */}
              {job.details && Object.keys(job.details).length > 0 && (
                <div className="mt-2 text-xs text-muted-foreground">
                  {job.details.folder && <span>Pasta: {job.details.folder}</span>}
                  {job.details.source && <span className="ml-2">Fonte: {job.details.source}</span>}
                </div>
              )}
            </div>
          </div>
          
          {/* Acções */}
          <div className="flex items-center gap-2 shrink-0">
            {job.status === 'running' && (
              <Button 
                variant="outline" 
                size="sm"
                className="text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                onClick={async () => {
                  setCancelling(true);
                  await onCancel(job.id);
                  setCancelling(false);
                }}
                disabled={cancelling}
              >
                {cancelling ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <XCircle className="h-4 w-4 mr-1" />
                    Cancelar
                  </>
                )}
              </Button>
            )}
            {job.status !== 'running' && (
              <Button 
                variant="ghost" 
                size="sm"
                className="text-muted-foreground hover:text-destructive"
                onClick={() => onDelete(job.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const BackgroundJobsPage = () => {
  const [jobs, setJobs] = useState([]);
  const [counts, setCounts] = useState({ running: 0, success: 0, failed: 0, total: 0 });
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchJobs = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      const url = statusFilter 
        ? `${API_URL}/api/ai/bulk/background-jobs?status=${statusFilter}`
        : `${API_URL}/api/ai/bulk/background-jobs`;
      
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setJobs(data.jobs || []);
        setCounts(data.counts || { running: 0, success: 0, failed: 0, total: 0 });
      }
    } catch (error) {
      console.error("Erro ao carregar jobs:", error);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  // Fetch inicial e auto-refresh
  useEffect(() => {
    fetchJobs();
    
    if (autoRefresh) {
      const interval = setInterval(fetchJobs, 5000); // Refresh a cada 5 segundos
      return () => clearInterval(interval);
    }
  }, [fetchJobs, autoRefresh]);

  const handleDelete = async (jobId) => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_URL}/api/ai/bulk/background-jobs/${jobId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success("Job removido");
        fetchJobs();
      }
    } catch (error) {
      toast.error("Erro ao remover job");
    }
  };

  const handleCancel = async (jobId) => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_URL}/api/ai/bulk/background-jobs/${jobId}/cancel`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success("Processo cancelado");
        fetchJobs();
      } else {
        toast.error("Não foi possível cancelar o processo");
      }
    } catch (error) {
      toast.error("Erro ao cancelar processo");
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm("Tem a certeza que deseja limpar todos os jobs terminados?")) {
      return;
    }
    
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_URL}/api/ai/bulk/background-jobs`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        toast.success(data.message);
        fetchJobs();
      }
    } catch (error) {
      toast.error("Erro ao limpar jobs");
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Activity className="h-6 w-6" />
              Processos em Background
            </h1>
            <p className="text-muted-foreground">
              Monitorize importações e outros processos a correr no sistema
            </p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={autoRefresh ? "bg-green-50 border-green-300" : ""}
            >
              {autoRefresh ? (
                <><RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Auto-refresh</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-2" /> Auto-refresh OFF</>
              )}
            </Button>
            <Button variant="outline" onClick={fetchJobs}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Recarregar
            </Button>
            {counts.total - counts.running > 0 && (
              <Button variant="outline" onClick={handleClearAll}>
                <Trash2 className="h-4 w-4 mr-2" />
                Limpar Terminados
              </Button>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card 
            className={`cursor-pointer transition-all ${statusFilter === null ? 'ring-2 ring-primary' : 'hover:shadow-md'}`}
            onClick={() => setStatusFilter(null)}
          >
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{counts.total}</div>
              <p className="text-sm text-muted-foreground">Total</p>
            </CardContent>
          </Card>
          <Card 
            className={`cursor-pointer transition-all ${statusFilter === 'running' ? 'ring-2 ring-blue-500' : 'hover:shadow-md'}`}
            onClick={() => setStatusFilter(statusFilter === 'running' ? null : 'running')}
          >
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-blue-600 flex items-center gap-2">
                {counts.running}
                {counts.running > 0 && <Loader2 className="h-5 w-5 animate-spin" />}
              </div>
              <p className="text-sm text-muted-foreground">A correr</p>
            </CardContent>
          </Card>
          <Card 
            className={`cursor-pointer transition-all ${statusFilter === 'success' ? 'ring-2 ring-green-500' : 'hover:shadow-md'}`}
            onClick={() => setStatusFilter(statusFilter === 'success' ? null : 'success')}
          >
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-green-600">{counts.success}</div>
              <p className="text-sm text-muted-foreground">Concluídos</p>
            </CardContent>
          </Card>
          <Card 
            className={`cursor-pointer transition-all ${statusFilter === 'failed' ? 'ring-2 ring-red-500' : 'hover:shadow-md'}`}
            onClick={() => setStatusFilter(statusFilter === 'failed' ? null : 'failed')}
          >
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-red-600">{counts.failed}</div>
              <p className="text-sm text-muted-foreground">Falhados</p>
            </CardContent>
          </Card>
        </div>

        {/* Lista de Jobs */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              {statusFilter ? (
                <>
                  Filtro: {STATUS_CONFIG[statusFilter]?.label}
                  <Button variant="ghost" size="sm" onClick={() => setStatusFilter(null)}>
                    <XCircle className="h-4 w-4" />
                  </Button>
                </>
              ) : (
                "Todos os Processos"
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : jobs.length === 0 ? (
              <div className="text-center py-12">
                <Activity className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">Nenhum processo em background</h3>
                <p className="text-muted-foreground">
                  Os processos de importação e análise aparecerão aqui.
                </p>
              </div>
            ) : (
              <ScrollArea className="h-[500px] pr-2">
                <div className="space-y-3">
                  {jobs.map(job => (
                    <JobCard 
                      key={job.id} 
                      job={job} 
                      onDelete={handleDelete}
                      onCancel={handleCancel}
                    />
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default BackgroundJobsPage;
