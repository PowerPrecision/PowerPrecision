/**
 * SystemConfigPage - Página de Configurações do Sistema
 * Permite ao admin configurar integrações e definições
 */
import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { toast } from "sonner";
import {
  Settings,
  Cloud,
  Mail,
  Sparkles,
  Trello,
  Building,
  Save,
  Loader2,
  CheckCircle,
  XCircle,
  RefreshCw,
  TestTube,
  Eye,
  EyeOff,
  Wrench,
  Database,
  AlertTriangle,
  Trash2,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Ícones por secção
const SECTION_ICONS = {
  storage: Cloud,
  email: Mail,
  ai: Sparkles,
  trello: Trello,
  settings: Building,
  maintenance: Wrench,
};

// Componente para campo de configuração
const ConfigFieldInput = ({ field, value, onChange, allValues }) => {
  const [showPassword, setShowPassword] = useState(false);

  // Verificar dependências
  if (field.depends_on) {
    const [depKey, depValue] = Object.entries(field.depends_on)[0];
    if (allValues[depKey] !== depValue) {
      return null;
    }
  }

  const inputType = field.type === "password" && !showPassword ? "password" : "text";

  switch (field.type) {
    case "select":
      return (
        <div className="space-y-2">
          <Label htmlFor={field.key}>{field.label}</Label>
          <Select
            value={value || ""}
            onValueChange={(v) => onChange(field.key, v)}
          >
            <SelectTrigger id={field.key}>
              <SelectValue placeholder="Seleccione..." />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {field.help_text && (
            <p className="text-xs text-muted-foreground">{field.help_text}</p>
          )}
        </div>
      );

    case "boolean":
      return (
        <div className="flex items-center justify-between py-2">
          <div>
            <Label htmlFor={field.key}>{field.label}</Label>
            {field.help_text && (
              <p className="text-xs text-muted-foreground">{field.help_text}</p>
            )}
          </div>
          <Switch
            id={field.key}
            checked={value || false}
            onCheckedChange={(v) => onChange(field.key, v)}
          />
        </div>
      );

    case "password":
      return (
        <div className="space-y-2">
          <Label htmlFor={field.key}>{field.label}</Label>
          <div className="relative">
            <Input
              id={field.key}
              type={inputType}
              value={value || ""}
              onChange={(e) => onChange(field.key, e.target.value)}
              placeholder={field.placeholder}
              className="pr-10"
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 p-0"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </Button>
          </div>
          {field.help_text && (
            <p className="text-xs text-muted-foreground">{field.help_text}</p>
          )}
        </div>
      );

    case "number":
      return (
        <div className="space-y-2">
          <Label htmlFor={field.key}>{field.label}</Label>
          <Input
            id={field.key}
            type="number"
            value={value || ""}
            onChange={(e) => onChange(field.key, parseInt(e.target.value) || "")}
            placeholder={field.placeholder}
          />
          {field.help_text && (
            <p className="text-xs text-muted-foreground">{field.help_text}</p>
          )}
        </div>
      );

    default:
      return (
        <div className="space-y-2">
          <Label htmlFor={field.key}>{field.label}</Label>
          <Input
            id={field.key}
            type="text"
            value={value || ""}
            onChange={(e) => onChange(field.key, e.target.value)}
            placeholder={field.placeholder}
          />
          {field.help_text && (
            <p className="text-xs text-muted-foreground">{field.help_text}</p>
          )}
        </div>
      );
  }
};

// Componente para secção de configuração
const ConfigSection = ({ section, sectionKey, config, fields, onSave, onTest }) => {
  const [localConfig, setLocalConfig] = useState(config || {});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    setLocalConfig(config || {});
    setHasChanges(false);
  }, [config]);

  const handleChange = (key, value) => {
    setLocalConfig((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
    setTestResult(null);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(sectionKey, localConfig);
      setHasChanges(false);
      toast.success("Configuração guardada");
    } catch (error) {
      toast.error("Erro ao guardar");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await onTest(sectionKey);
      setTestResult(result);
      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
    } catch (error) {
      setTestResult({ success: false, message: "Erro ao testar" });
    } finally {
      setTesting(false);
    }
  };

  const Icon = SECTION_ICONS[sectionKey] || Settings;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-primary" />
            <div>
              <CardTitle className="text-lg">{section.title}</CardTitle>
              <CardDescription>{section.description}</CardDescription>
            </div>
          </div>
          {hasChanges && (
            <Badge variant="outline" className="bg-yellow-50 text-yellow-700">
              Alterações por guardar
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {fields.map((field) => (
          <ConfigFieldInput
            key={field.key}
            field={field}
            value={localConfig[field.key]}
            onChange={handleChange}
            allValues={localConfig}
          />
        ))}

        {/* Test result */}
        {testResult && (
          <div
            className={`flex items-center gap-2 p-3 rounded-lg ${
              testResult.success
                ? "bg-green-50 text-green-700"
                : "bg-red-50 text-red-700"
            }`}
          >
            {testResult.success ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <XCircle className="h-4 w-4" />
            )}
            <span className="text-sm">{testResult.message}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-4 border-t">
          <Button onClick={handleSave} disabled={saving || !hasChanges}>
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Guardar
          </Button>

          {["storage", "email", "ai", "trello"].includes(sectionKey) && (
            <Button variant="outline" onClick={handleTest} disabled={testing}>
              {testing ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <TestTube className="h-4 w-4 mr-2" />
              )}
              Testar Ligação
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

const SystemConfigPage = () => {
  const { token, user } = useAuth();
  const [config, setConfig] = useState(null);
  const [fields, setFields] = useState({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("storage");

  const fetchConfig = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/system-config`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setConfig(data.config);
        setFields(data.fields);
      } else {
        toast.error("Erro ao carregar configurações");
      }
    } catch (error) {
      console.error("Erro:", error);
      toast.error("Erro ao carregar configurações");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleSave = async (section, data) => {
    const response = await fetch(`${API_URL}/api/system-config/${section}`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error("Erro ao guardar");
    }

    // Recarregar config
    await fetchConfig();
  };

  const handleTest = async (service) => {
    const response = await fetch(
      `${API_URL}/api/system-config/test-connection/${service}`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    return await response.json();
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </DashboardLayout>
    );
  }

  // Verificar se é admin
  if (user?.role !== "admin") {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold">Acesso Restrito</h2>
          <p className="text-muted-foreground">
            Apenas administradores podem aceder às configurações do sistema.
          </p>
        </div>
      </DashboardLayout>
    );
  }

  const sections = Object.keys(fields);

  // Componente de Manutenção do Sistema
  const MaintenanceSection = () => {
    const [repairingIndexes, setRepairingIndexes] = useState(false);
    const [cleaningJobs, setCleaningJobs] = useState(false);
    const [cleaningLogs, setCleaningLogs] = useState(false);
    const [indexStats, setIndexStats] = useState(null);

    const repairIndexes = async () => {
      setRepairingIndexes(true);
      try {
        const response = await fetch(`${API_URL}/api/admin/db/indexes/repair`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await response.json();
        if (data.success) {
          const dropped = data.cleanup?.dropped?.length || 0;
          toast.success(`Índices reparados! ${dropped > 0 ? `${dropped} índices antigos removidos.` : "Todos os índices OK."}`);
          // Actualizar stats
          fetchIndexStats();
        } else {
          toast.error("Erro ao reparar índices");
        }
      } catch (error) {
        toast.error("Erro de conexão");
      } finally {
        setRepairingIndexes(false);
      }
    };

    const fetchIndexStats = async () => {
      try {
        const response = await fetch(`${API_URL}/api/admin/db/indexes`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await response.json();
        if (data.success) {
          setIndexStats(data.indexes);
        }
      } catch (error) {
        console.error("Erro ao carregar stats:", error);
      }
    };

    const cleanOldJobs = async () => {
      setCleaningJobs(true);
      try {
        const response = await fetch(`${API_URL}/api/admin/cleanup/jobs?days=7`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await response.json();
        if (data.success) {
          toast.success(`${data.deleted_count || 0} jobs antigos removidos`);
        }
      } catch (error) {
        toast.error("Erro ao limpar jobs");
      } finally {
        setCleaningJobs(false);
      }
    };

    const cleanOldLogs = async () => {
      setCleaningLogs(true);
      try {
        const response = await fetch(`${API_URL}/api/admin/cleanup/error-logs?days=30`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await response.json();
        if (data.success) {
          toast.success(`${data.deleted_count || 0} logs antigos removidos`);
        }
      } catch (error) {
        toast.error("Erro ao limpar logs");
      } finally {
        setCleaningLogs(false);
      }
    };

    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Wrench className="h-5 w-5 text-primary" />
            <div>
              <CardTitle className="text-lg">Manutenção do Sistema</CardTitle>
              <CardDescription>Ferramentas de diagnóstico e reparação</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Reparação de Índices */}
          <div className="border rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Índices da Base de Dados
                </h4>
                <p className="text-sm text-muted-foreground">
                  Remove índices antigos/incorretos e recria os correctos. Use se houver erros de "duplicate key".
                </p>
              </div>
              <Button onClick={repairIndexes} disabled={repairingIndexes}>
                {repairingIndexes ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                Reparar Índices
              </Button>
            </div>
            {indexStats && (
              <div className="bg-muted/50 rounded p-3 text-sm">
                <p className="font-medium mb-2">Estado actual:</p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {Object.entries(indexStats).map(([coll, info]) => (
                    <div key={coll} className="flex items-center gap-1">
                      <CheckCircle className="h-3 w-3 text-green-500" />
                      <span>{coll}: {info.count || 0} índices</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <Button variant="outline" size="sm" onClick={fetchIndexStats}>
              <Eye className="h-4 w-4 mr-2" />
              Ver Estado dos Índices
            </Button>
          </div>

          {/* Limpeza de Jobs Antigos */}
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium flex items-center gap-2">
                  <Trash2 className="h-4 w-4" />
                  Limpar Jobs Antigos
                </h4>
                <p className="text-sm text-muted-foreground">
                  Remove jobs de importação concluídos há mais de 7 dias.
                </p>
              </div>
              <Button variant="outline" onClick={cleanOldJobs} disabled={cleaningJobs}>
                {cleaningJobs ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Trash2 className="h-4 w-4 mr-2" />
                )}
                Limpar
              </Button>
            </div>
          </div>

          {/* Limpeza de Logs Antigos */}
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  Limpar Logs de Erro Antigos
                </h4>
                <p className="text-sm text-muted-foreground">
                  Remove logs de erro com mais de 30 dias.
                </p>
              </div>
              <Button variant="outline" onClick={cleanOldLogs} disabled={cleaningLogs}>
                {cleaningLogs ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Trash2 className="h-4 w-4 mr-2" />
                )}
                Limpar
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Settings className="h-6 w-6" />
              Configurações do Sistema
            </h1>
            <p className="text-muted-foreground">
              Configure as integrações e definições da aplicação
            </p>
          </div>
          <Button variant="outline" onClick={fetchConfig}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Recarregar
          </Button>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-5">
            {sections.map((key) => {
              const Icon = SECTION_ICONS[key] || Settings;
              return (
                <TabsTrigger key={key} value={key} className="gap-2">
                  <Icon className="h-4 w-4" />
                  <span className="hidden sm:inline">{fields[key]?.title?.split(" ")[0]}</span>
                </TabsTrigger>
              );
            })}
          </TabsList>

          {sections.map((key) => (
            <TabsContent key={key} value={key} className="mt-6">
              <ConfigSection
                section={fields[key]}
                sectionKey={key}
                config={config?.[key]}
                fields={fields[key]?.fields || []}
                onSave={handleSave}
                onTest={handleTest}
              />
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </DashboardLayout>
  );
};

export default SystemConfigPage;
