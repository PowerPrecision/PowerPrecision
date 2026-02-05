/**
 * ====================================================================
 * COMPONENTE DE INTEGRAÇÃO TRELLO - CREDITOIMO
 * ====================================================================
 * Painel de gestão da integração com o Trello.
 * 
 * Funcionalidades:
 * - Verificar estado da conexão com diagnóstico detalhado
 * - Sincronizar dados do Trello com atribuição automática
 * - Visualizar mapeamento de membros Trello ↔ Utilizadores
 * - Configurar webhook para sync em tempo real
 * ====================================================================
 */

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { useToast } from "../hooks/use-toast";
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  ExternalLink,
  Loader2,
  AlertTriangle,
  Trash2,
  Download,
  Upload,
  Webhook,
  Users,
  UserCheck,
  UserX,
  Link2,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL || "";

const TrelloIntegration = () => {
  const { token } = useAuth();
  const { toast } = useToast();
  
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [syncResult, setSyncResult] = useState(null);
  const [webhooks, setWebhooks] = useState([]);
  const [settingUpWebhook, setSettingUpWebhook] = useState(false);
  const [showMemberMapping, setShowMemberMapping] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/trello/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      }
      
      // Também buscar webhooks
      const webhookResponse = await fetch(`${API_URL}/api/trello/webhook/list`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (webhookResponse.ok) {
        const webhookData = await webhookResponse.json();
        setWebhooks(webhookData.webhooks || []);
      }
    } catch (error) {
      console.error("Erro ao verificar Trello:", error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleSyncFromTrello = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const response = await fetch(`${API_URL}/api/trello/sync/from-trello`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setSyncResult(data);
      toast({
        title: data.success ? "Sincronização concluída" : "Erro na sincronização",
        description: data.message,
        variant: data.success ? "default" : "destructive",
      });
    } catch (error) {
      toast({
        title: "Erro",
        description: "Não foi possível sincronizar com o Trello.",
        variant: "destructive",
      });
    } finally {
      setSyncing(false);
    }
  };

  const handleSyncToTrello = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const response = await fetch(`${API_URL}/api/trello/sync/to-trello`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setSyncResult(data);
      toast({
        title: data.success ? "Sincronização concluída" : "Erro na sincronização",
        description: data.message,
        variant: data.success ? "default" : "destructive",
      });
    } catch (error) {
      toast({
        title: "Erro",
        description: "Não foi possível sincronizar para o Trello.",
        variant: "destructive",
      });
    } finally {
      setSyncing(false);
    }
  };

  const handleFullReset = async () => {
    if (!window.confirm(
      "⚠️ ATENÇÃO: Esta ação vai APAGAR TODOS os processos, tarefas, prazos e utilizadores (exceto admins) e importar tudo do Trello.\n\nTem a certeza que quer continuar?"
    )) {
      return;
    }
    
    setResetting(true);
    setSyncResult(null);
    try {
      const response = await fetch(`${API_URL}/api/trello/reset-and-sync`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setSyncResult({
        success: data.success,
        message: data.message,
        created: data.imported?.processes || 0,
        updated: 0,
        errors: data.imported?.errors || [],
        deleted: data.deleted
      });
      toast({
        title: data.success ? "Reset concluído" : "Erro no reset",
        description: data.message,
        variant: data.success ? "default" : "destructive",
      });
    } catch (error) {
      toast({
        title: "Erro",
        description: "Não foi possível fazer o reset.",
        variant: "destructive",
      });
    } finally {
      setResetting(false);
    }
  };

  const handleSetupWebhook = async () => {
    setSettingUpWebhook(true);
    try {
      const response = await fetch(`${API_URL}/api/trello/webhook/setup`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      
      if (data.success) {
        toast({
          title: "Webhook configurado",
          description: data.message,
        });
        fetchStatus(); // Atualizar lista de webhooks
      } else {
        throw new Error(data.detail || "Erro ao configurar webhook");
      }
    } catch (error) {
      toast({
        title: "Erro",
        description: error.message || "Não foi possível configurar o webhook.",
        variant: "destructive",
      });
    } finally {
      setSettingUpWebhook(false);
    }
  };

  const handleDeleteWebhook = async (webhookId) => {
    try {
      await fetch(`${API_URL}/api/trello/webhook/${webhookId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      toast({
        title: "Webhook removido",
        description: "O webhook foi removido com sucesso.",
      });
      fetchStatus();
    } catch (error) {
      toast({
        title: "Erro",
        description: "Não foi possível remover o webhook.",
        variant: "destructive",
      });
    }
  };

  const handleAssignExisting = async () => {
    setAssigning(true);
    setSyncResult(null);
    try {
      const response = await fetch(`${API_URL}/api/trello/assign-existing`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setSyncResult(data);
      toast({
        title: data.success ? "Atribuição concluída" : "Erro na atribuição",
        description: data.message,
        variant: data.success ? "default" : "destructive",
      });
      // Atualizar status para mostrar novas estatísticas
      fetchStatus();
    } catch (error) {
      toast({
        title: "Erro",
        description: "Não foi possível atribuir os processos.",
        variant: "destructive",
      });
    } finally {
      setAssigning(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-10 flex justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-900" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M21 0H3C1.34 0 0 1.34 0 3v18c0 1.66 1.34 3 3 3h18c1.66 0 3-1.34 3-3V3c0-1.66-1.34-3-3-3zM10.44 18.18c0 .9-.72 1.62-1.62 1.62H4.62c-.9 0-1.62-.72-1.62-1.62V4.62c0-.9.72-1.62 1.62-1.62h4.2c.9 0 1.62.72 1.62 1.62v13.56zm10.56-6c0 .9-.72 1.62-1.62 1.62h-4.2c-.9 0-1.62-.72-1.62-1.62V4.62c0-.9.72-1.62 1.62-1.62h4.2c.9 0 1.62.72 1.62 1.62v7.56z"/>
              </svg>
              Integração Trello
            </CardTitle>
            <CardDescription>
              Sincronize processos entre o CreditoIMO e o Trello
            </CardDescription>
          </div>
          {status?.connected ? (
            <Badge className="bg-green-100 text-green-800 border-green-200">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Conectado
            </Badge>
          ) : (
            <Badge variant="destructive">
              <XCircle className="h-3 w-3 mr-1" />
              Desconectado
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Informação do Board */}
        {status?.board && (
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Board conectado</p>
                <p className="font-semibold text-blue-900">{status.board.name}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {status.board.lists_count} listas
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(status.board.url, '_blank')}
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Abrir no Trello
              </Button>
            </div>
          </div>
        )}

        {/* Listas do Trello */}
        {status?.lists && status.lists.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Listas mapeadas:</p>
            <div className="flex flex-wrap gap-2">
              {status.lists.map((list) => (
                <Badge key={list.id} variant="outline" className="text-xs">
                  {list.name}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Estatísticas de Sincronização */}
        {status?.sync_stats && (
          <div className="p-4 bg-gray-50 rounded-lg border">
            <div className="flex items-center gap-2 mb-3">
              <Users className="h-4 w-4 text-teal-600" />
              <span className="font-medium">Estatísticas de Sincronização</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="text-center p-2 bg-white rounded border">
                <p className="text-2xl font-bold text-teal-600">{status.sync_stats.total_processes}</p>
                <p className="text-xs text-muted-foreground">Total Processos</p>
              </div>
              <div className="text-center p-2 bg-white rounded border">
                <p className="text-2xl font-bold text-blue-600">{status.sync_stats.trello_synced}</p>
                <p className="text-xs text-muted-foreground">Do Trello</p>
              </div>
              <div className="text-center p-2 bg-white rounded border">
                <p className="text-2xl font-bold text-green-600">{status.sync_stats.with_assignment}</p>
                <p className="text-xs text-muted-foreground">Com Atribuição</p>
              </div>
              <div className="text-center p-2 bg-white rounded border">
                <p className="text-2xl font-bold text-amber-600">{status.sync_stats.without_assignment}</p>
                <p className="text-xs text-muted-foreground">Sem Atribuição</p>
              </div>
            </div>
            {status.sync_stats.last_sync && (
              <p className="text-xs text-muted-foreground mt-3 text-center">
                Última sincronização: {new Date(status.sync_stats.last_sync).toLocaleString("pt-PT")}
              </p>
            )}
            {status.sync_stats.without_assignment > 0 && (
              <div className="mt-3 p-2 bg-amber-50 rounded border border-amber-200">
                <p className="text-xs text-amber-700 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Existem {status.sync_stats.without_assignment} processos sem utilizador atribuído. 
                  Utilize o botão "Atribuir Automático" para corrigir.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Mapeamento de Membros */}
        {status?.member_mapping && status.member_mapping.length > 0 && (
          <div className="border rounded-lg">
            <button
              onClick={() => setShowMemberMapping(!showMemberMapping)}
              className="w-full p-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Link2 className="h-4 w-4 text-blue-900" />
                <span className="font-medium text-sm">Mapeamento Membros Trello ↔ Utilizadores</span>
                <Badge variant="outline" className="text-xs">
                  {status.member_mapping.filter(m => m.matched).length}/{status.member_mapping.length} mapeados
                </Badge>
              </div>
              <span className="text-xs text-muted-foreground">
                {showMemberMapping ? "Ocultar" : "Mostrar"}
              </span>
            </button>
            
            {showMemberMapping && (
              <div className="border-t p-3 space-y-2">
                <p className="text-xs text-muted-foreground mb-2">
                  Os membros do Trello são automaticamente associados aos utilizadores da aplicação pelo nome.
                  Para que a atribuição automática funcione, os nomes devem coincidir.
                </p>
                {status.member_mapping.map((mapping, idx) => (
                  <div 
                    key={idx}
                    className={`flex items-center justify-between p-2 rounded text-sm ${
                      mapping.matched ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {mapping.matched ? (
                        <UserCheck className="h-4 w-4 text-green-600" />
                      ) : (
                        <UserX className="h-4 w-4 text-red-600" />
                      )}
                      <div>
                        <p className="font-medium">{mapping.trello_name}</p>
                        <p className="text-xs text-muted-foreground">@{mapping.trello_username}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      {mapping.matched ? (
                        <>
                          <p className="text-green-700">{mapping.app_user}</p>
                          <p className="text-xs text-green-600">{mapping.app_email}</p>
                          <p className="text-xs text-muted-foreground">{mapping.app_role} • via {mapping.match_method}</p>
                        </>
                      ) : (
                        <p className="text-red-600 text-xs">Sem correspondência</p>
                      )}
                    </div>
                  </div>
                ))}
                {status.member_mapping.some(m => !m.matched) && (
                  <p className="text-xs text-amber-700 mt-2 p-2 bg-amber-50 rounded">
                    💡 Para mapear membros não correspondidos, crie utilizadores na aplicação com o mesmo nome exacto do Trello.
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Botões de Sincronização */}
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
          <Button
            onClick={handleSyncFromTrello}
            disabled={syncing || resetting || assigning || !status?.connected}
            className="bg-teal-600 hover:bg-teal-700"
          >
            {syncing ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            Trello → App
          </Button>
          
          <Button
            onClick={handleSyncToTrello}
            disabled={syncing || resetting || assigning || !status?.connected}
            variant="outline"
          >
            {syncing ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Upload className="h-4 w-4 mr-2" />
            )}
            App → Trello
          </Button>

          <Button
            onClick={handleAssignExisting}
            disabled={syncing || resetting || assigning || !status?.connected}
            className="bg-amber-500 hover:bg-amber-600"
            title="Atribuir processos existentes a utilizadores"
          >
            {assigning ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <UserCheck className="h-4 w-4 mr-2" />
            )}
            Atribuir Auto
          </Button>

          <Button
            onClick={fetchStatus}
            variant="outline"
            disabled={syncing || resetting || assigning}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Atualizar
          </Button>
          
          <Button
            onClick={handleFullReset}
            disabled={syncing || resetting || assigning || !status?.connected}
            variant="destructive"
          >
            {resetting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4 mr-2" />
            )}
            Reset Total
          </Button>
        </div>

        {/* Resultado da Sincronização */}
        {syncResult && (
          <div className={`p-4 rounded-lg border ${syncResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
            <div className="flex items-start gap-3">
              {syncResult.success ? (
                <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
              )}
              <div className="flex-1">
                <p className={`font-medium ${syncResult.success ? 'text-green-800' : 'text-red-800'}`}>
                  {syncResult.message}
                </p>
                <div className="mt-2 text-sm space-y-1">
                  {syncResult.created > 0 && (
                    <p className="text-green-700">✓ {syncResult.created} processos criados</p>
                  )}
                  {syncResult.updated > 0 && (
                    <p className="text-blue-700">↻ {syncResult.updated} processos atualizados</p>
                  )}
                  {syncResult.deleted && (
                    <div className="text-amber-700">
                      <p>Apagados: {syncResult.deleted.processes} processos, {syncResult.deleted.tasks} tarefas, {syncResult.deleted.deadlines} prazos</p>
                    </div>
                  )}
                  {syncResult.errors && syncResult.errors.length > 0 && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-red-700">
                        {syncResult.errors.length} erros/avisos
                      </summary>
                      <ul className="mt-1 pl-4 text-xs text-red-600">
                        {syncResult.errors.slice(0, 10).map((err, i) => (
                          <li key={i}>• {err}</li>
                        ))}
                        {syncResult.errors.length > 10 && (
                          <li>... e mais {syncResult.errors.length - 10}</li>
                        )}
                      </ul>
                    </details>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Aviso se não estiver conectado */}
        {!status?.connected && (
          <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium text-amber-800">Trello não configurado</p>
                <p className="text-sm text-amber-700 mt-1">
                  As credenciais do Trello não estão configuradas ou são inválidas.
                </p>
                {status?.error && (
                  <div className="mt-3 p-2 bg-red-100 rounded text-xs text-red-700">
                    <strong>Erro:</strong> {status.error}
                  </div>
                )}
                <div className="mt-3 p-3 bg-white rounded border text-xs space-y-1">
                  <p className="font-medium text-gray-700 mb-2">Variáveis necessárias no Render:</p>
                  <div className="grid gap-1">
                    <div className="flex items-center gap-2">
                      {status?.config?.has_api_key ? (
                        <CheckCircle2 className="h-3 w-3 text-green-600" />
                      ) : (
                        <XCircle className="h-3 w-3 text-red-600" />
                      )}
                      <code className="bg-gray-100 px-1 rounded">TRELLO_API_KEY</code>
                      <span className="text-gray-500">
                        {status?.config?.has_api_key ? "Configurada" : "Não configurada"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {status?.config?.has_token ? (
                        <CheckCircle2 className="h-3 w-3 text-green-600" />
                      ) : (
                        <XCircle className="h-3 w-3 text-red-600" />
                      )}
                      <code className="bg-gray-100 px-1 rounded">TRELLO_TOKEN</code>
                      <span className="text-gray-500">
                        {status?.config?.has_token ? "Configurado" : "Não configurado"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {status?.config?.has_board_id ? (
                        <CheckCircle2 className="h-3 w-3 text-green-600" />
                      ) : (
                        <XCircle className="h-3 w-3 text-red-600" />
                      )}
                      <code className="bg-gray-100 px-1 rounded">TRELLO_BOARD_ID</code>
                      <span className="text-gray-500">
                        {status?.config?.board_id || "Não configurado"}
                      </span>
                    </div>
                  </div>
                  <div className="mt-3 pt-2 border-t">
                    <p className="text-gray-600">
                      <strong>Como obter:</strong> Aceda a{" "}
                      <a 
                        href="https://trello.com/power-ups/admin" 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-600 underline"
                      >
                        trello.com/power-ups/admin
                      </a>
                      {" "}para criar uma API Key e Token.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Webhook em Tempo Real */}
        {status?.connected && (
          <div className="border rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Webhook className="h-4 w-4 text-blue-900" />
                <span className="font-medium">Sincronização em Tempo Real</span>
              </div>
              {webhooks.length > 0 ? (
                <Badge className="bg-green-100 text-green-800 border-green-200">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Ativo
                </Badge>
              ) : (
                <Badge variant="secondary">
                  Inativo
                </Badge>
              )}
            </div>
            
            {webhooks.length > 0 ? (
              <div className="text-sm text-muted-foreground">
                <p className="text-green-700">
                  ✓ Webhook ativo - Alterações no Trello são sincronizadas automaticamente
                </p>
                <p className="text-green-700">
                  ✓ Alterações na App são enviadas automaticamente para o Trello
                </p>
                <div className="mt-2 flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteWebhook(webhooks[0].id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-3 w-3 mr-1" />
                    Remover Webhook
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-amber-700">
                  ⚠️ Para receber atualizações do Trello em tempo real, configure o webhook.
                </p>
                <Button
                  size="sm"
                  onClick={handleSetupWebhook}
                  disabled={settingUpWebhook}
                  className="bg-teal-600 hover:bg-teal-700"
                >
                  {settingUpWebhook ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Webhook className="h-4 w-4 mr-2" />
                  )}
                  Ativar Webhook
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Informação sobre sincronização */}
        <div className="text-xs text-muted-foreground space-y-1 border-t pt-4">
          <p><strong>Trello → App:</strong> Importa novos cards e atualiza estados de processos existentes.</p>
          <p><strong>App → Trello:</strong> Exporta processos novos e atualiza cards existentes no Trello.</p>
          <p><strong>Reset Total:</strong> Apaga TODOS os dados e importa tudo do Trello (usar com cuidado!).</p>
          <p className="text-blue-700 mt-2">
            <Webhook className="h-3 w-3 inline mr-1" />
            A sincronização bidirecional em tempo real está ativa: quando move um processo no Kanban, o card é atualizado automaticamente no Trello.
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

export default TrelloIntegration;
