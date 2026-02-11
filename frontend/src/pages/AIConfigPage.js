/**
 * ====================================================================
 * PÁGINA DE CONFIGURAÇÃO DE IA - CREDITOIMO
 * ====================================================================
 * Permite ao admin configurar qual modelo de IA usar para cada tarefa:
 * - Extracção de dados (scraping)
 * - Análise de documentos
 * - Relatório semanal de erros
 * - Análise de erros de importação
 * 
 * Também inclui estatísticas e gestão do cache de scraping.
 * ====================================================================
 */

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Separator } from "../components/ui/separator";
import { toast } from "sonner";
import {
  Sparkles,
  Bot,
  FileSearch,
  FileText,
  BarChart3,
  AlertTriangle,
  Save,
  Loader2,
  RefreshCw,
  Trash2,
  Database,
  Zap,
  DollarSign,
  CheckCircle,
  Info,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Ícones por tarefa
const TASK_ICONS = {
  scraper_extraction: FileSearch,
  document_analysis: FileText,
  weekly_report: BarChart3,
  error_analysis: AlertTriangle,
};

// Cores por provider
const PROVIDER_COLORS = {
  gemini: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  openai: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
};

const AIConfigPage = () => {
  const { token } = useAuth();
  
  // Estado da configuração
  const [config, setConfig] = useState({});
  const [defaults, setDefaults] = useState({});
  const [availableModels, setAvailableModels] = useState({});
  const [taskDescriptions, setTaskDescriptions] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  
  // Estado do cache
  const [cacheStats, setCacheStats] = useState(null);
  const [clearingCache, setClearingCache] = useState(false);

  // Carregar configuração
  const loadConfig = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/admin/ai-config`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setConfig(data.current_config || {});
        setDefaults(data.defaults || {});
        setAvailableModels(data.available_models || {});
        setTaskDescriptions(data.task_descriptions || {});
      } else {
        toast.error("Erro ao carregar configuração de IA");
      }
    } catch (error) {
      console.error("Erro:", error);
      toast.error("Erro de conexão");
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Carregar estatísticas do cache
  const loadCacheStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/scraper/cache/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setCacheStats(data);
      }
    } catch (error) {
      console.error("Erro ao carregar cache stats:", error);
    }
  }, [token]);

  useEffect(() => {
    loadConfig();
    loadCacheStats();
  }, [loadConfig, loadCacheStats]);

  // Alterar modelo para uma tarefa
  const handleModelChange = (task, model) => {
    setConfig(prev => ({ ...prev, [task]: model }));
    setHasChanges(true);
  };

  // Guardar configuração
  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/admin/ai-config`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(config),
      });
      
      if (response.ok) {
        toast.success("Configuração de IA guardada com sucesso");
        setHasChanges(false);
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao guardar configuração");
      }
    } catch (error) {
      console.error("Erro:", error);
      toast.error("Erro de conexão");
    } finally {
      setSaving(false);
    }
  };

  // Restaurar defaults
  const handleRestoreDefaults = () => {
    setConfig({ ...defaults });
    setHasChanges(true);
    toast.info("Valores por defeito restaurados. Clique em Guardar para aplicar.");
  };

  // Limpar cache
  const handleClearCache = async () => {
    setClearingCache(true);
    try {
      const response = await fetch(`${API_URL}/api/scraper/cache/clear`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        toast.success(`Cache limpo: ${data.deleted_count} registos eliminados`);
        loadCacheStats();
      } else {
        toast.error("Erro ao limpar cache");
      }
    } catch (error) {
      console.error("Erro:", error);
      toast.error("Erro de conexão");
    } finally {
      setClearingCache(false);
    }
  };

  // Obter info do modelo
  const getModelInfo = (modelKey) => {
    return availableModels[modelKey] || {};
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="ai-config-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-primary" />
              Configuração de IA
            </h1>
            <p className="text-muted-foreground mt-1">
              Configure qual modelo de IA usar para cada tarefa do sistema
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={handleRestoreDefaults}
              disabled={saving}
              data-testid="restore-defaults-btn"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Restaurar Defeitos
            </Button>
            <Button
              onClick={handleSave}
              disabled={!hasChanges || saving}
              data-testid="save-ai-config-btn"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Save className="h-4 w-4 mr-2" />
              )}
              Guardar Alterações
            </Button>
          </div>
        </div>

        {/* Info Banner */}
        <Card className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
          <CardContent className="pt-4">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-blue-800 dark:text-blue-200">
                <p className="font-medium mb-1">Como funciona a configuração de IA</p>
                <ul className="list-disc list-inside space-y-1 text-blue-700 dark:text-blue-300">
                  <li><strong>Gemini 2.0 Flash</strong> - Mais económico, ideal para extracção de dados (scraping)</li>
                  <li><strong>GPT-4o Mini</strong> - Bom equilíbrio custo/qualidade para análise de documentos</li>
                  <li><strong>GPT-4o</strong> - Mais avançado, para análises complexas e relatórios</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Configuração por Tarefa */}
        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries(taskDescriptions).map(([task, description]) => {
            const TaskIcon = TASK_ICONS[task] || Bot;
            const currentModel = config[task] || defaults[task];
            const modelInfo = getModelInfo(currentModel);
            
            return (
              <Card key={task} data-testid={`ai-task-card-${task}`}>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <TaskIcon className="h-5 w-5 text-primary" />
                    {description}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor={`model-${task}`}>Modelo de IA</Label>
                    <Select
                      value={currentModel}
                      onValueChange={(value) => handleModelChange(task, value)}
                    >
                      <SelectTrigger id={`model-${task}`} data-testid={`select-model-${task}`}>
                        <SelectValue placeholder="Seleccione um modelo" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(availableModels).map(([key, model]) => (
                          <SelectItem key={key} value={key}>
                            <div className="flex items-center gap-2">
                              <span>{model.name}</span>
                              <Badge variant="outline" className="text-xs">
                                {model.provider}
                              </Badge>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {modelInfo && (
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <Badge className={PROVIDER_COLORS[modelInfo.provider] || "bg-gray-100"}>
                        {modelInfo.provider?.toUpperCase()}
                      </Badge>
                      <span className="text-muted-foreground flex items-center gap-1">
                        <DollarSign className="h-3 w-3" />
                        {modelInfo.cost_per_1k_tokens?.toFixed(4)}€/1k tokens
                      </span>
                      {modelInfo.best_for && (
                        <span className="text-muted-foreground flex items-center gap-1">
                          <Zap className="h-3 w-3" />
                          {modelInfo.best_for?.join(", ")}
                        </span>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        <Separator />

        {/* Cache de Scraping */}
        <Card data-testid="scraper-cache-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-primary" />
              Cache de Scraping
            </CardTitle>
            <CardDescription>
              URLs já processadas são guardadas em cache por {cacheStats?.cache_expiry_days || 7} dias 
              para evitar chamadas repetidas à API de IA.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              {cacheStats ? (
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-sm">
                      <strong>{cacheStats.valid_entries}</strong> entradas válidas
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                    <span className="text-sm">
                      <strong>{cacheStats.expired_entries}</strong> expiradas
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">
                      <strong>{cacheStats.total_entries}</strong> total
                    </span>
                  </div>
                </div>
              ) : (
                <span className="text-sm text-muted-foreground">A carregar estatísticas...</span>
              )}
              
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={loadCacheStats}
                  data-testid="refresh-cache-stats-btn"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Actualizar
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleClearCache}
                  disabled={clearingCache || !cacheStats?.total_entries}
                  data-testid="clear-cache-btn"
                >
                  {clearingCache ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4 mr-2" />
                  )}
                  Limpar Cache
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Modelos Disponíveis */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-primary" />
              Modelos Disponíveis
            </CardTitle>
            <CardDescription>
              Lista de todos os modelos de IA configurados e disponíveis para uso.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(availableModels).map(([key, model]) => (
                <div
                  key={key}
                  className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                  data-testid={`model-card-${key}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{model.name}</span>
                    <Badge className={PROVIDER_COLORS[model.provider] || "bg-gray-100"}>
                      {model.provider?.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="space-y-1 text-sm text-muted-foreground">
                    <p className="flex items-center gap-1">
                      <DollarSign className="h-3 w-3" />
                      {model.cost_per_1k_tokens?.toFixed(4)}€ / 1k tokens
                    </p>
                    <p className="flex items-center gap-1">
                      <Zap className="h-3 w-3" />
                      Melhor para: {model.best_for?.join(", ")}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default AIConfigPage;
