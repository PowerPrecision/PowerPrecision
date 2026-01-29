/**
 * EmailHistoryPanel - Painel de Histórico de Emails
 * Componente para visualizar e registar emails na ficha do cliente
 */
import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Badge } from "./ui/badge";
import { Label } from "./ui/label";
import { ScrollArea } from "./ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { 
  Mail, Send, Inbox, Plus, Loader2, Clock, User, 
  Paperclip, MoreVertical, Trash2, Eye, ChevronDown, ChevronUp, RefreshCw,
  Settings, X, AtSign
} from "lucide-react";
import { toast } from "sonner";
import { format, parseISO } from "date-fns";
import { pt } from "date-fns/locale";
import { getProcessEmails, getEmailStats, createEmail, deleteEmail, syncProcessEmails, getMonitoredEmails, addMonitoredEmail, removeMonitoredEmail } from "../services/api";

const EmailHistoryPanel = ({ 
  processId, 
  clientEmail,
  clientName,
  compact = false,
  maxHeight = "400px"
}) => {
  const [emails, setEmails] = useState([]);
  const [stats, setStats] = useState({ total: 0, sent: 0, received: 0 });
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [filter, setFilter] = useState("all"); // all, sent, received
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [expandedEmail, setExpandedEmail] = useState(null);
  
  // Emails monitorizados
  const [monitoredEmails, setMonitoredEmails] = useState([]);
  const [newMonitoredEmail, setNewMonitoredEmail] = useState("");
  const [addingEmail, setAddingEmail] = useState(false);
  
  // Form state
  const [newEmail, setNewEmail] = useState({
    direction: "sent",
    from_email: "",
    to_emails: "",
    subject: "",
    body: "",
    notes: ""
  });

  useEffect(() => {
    if (processId) {
      fetchData();
      fetchMonitoredEmails();
    }
  }, [processId, filter]);

  const fetchMonitoredEmails = async () => {
    try {
      const response = await getMonitoredEmails(processId);
      setMonitoredEmails(response.data.monitored_emails || []);
    } catch (error) {
      console.error("Erro ao carregar emails monitorizados:", error);
    }
  };

  const handleAddMonitoredEmail = async () => {
    if (!newMonitoredEmail.trim() || !newMonitoredEmail.includes("@")) {
      toast.error("Introduza um email válido");
      return;
    }
    try {
      setAddingEmail(true);
      await addMonitoredEmail(processId, newMonitoredEmail.trim());
      toast.success("Email adicionado à monitorização");
      setNewMonitoredEmail("");
      fetchMonitoredEmails();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao adicionar email");
    } finally {
      setAddingEmail(false);
    }
  };

  const handleRemoveMonitoredEmail = async (email) => {
    try {
      await removeMonitoredEmail(processId, email);
      toast.success("Email removido da monitorização");
      fetchMonitoredEmails();
    } catch (error) {
      toast.error("Erro ao remover email");
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const [emailsRes, statsRes] = await Promise.all([
        getProcessEmails(processId, filter === "all" ? null : filter),
        getEmailStats(processId)
      ]);
      setEmails(emailsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error("Erro ao carregar emails:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncEmails = async () => {
    if (!clientEmail) {
      toast.error("Cliente não tem email definido");
      return;
    }

    try {
      setSyncing(true);
      toast.info("A sincronizar emails... Isto pode demorar alguns segundos.");
      
      const response = await syncProcessEmails(processId, 60);
      
      if (response.data.success) {
        toast.success(`Sincronização concluída: ${response.data.new_imported} novos emails importados`);
        fetchData();
      } else {
        toast.error(response.data.error || "Erro na sincronização");
      }
    } catch (error) {
      console.error("Erro ao sincronizar:", error);
      toast.error(error.response?.data?.detail || "Erro ao sincronizar emails");
    } finally {
      setSyncing(false);
    }
  };

  const handleCreateEmail = async () => {
    if (!newEmail.subject.trim() || !newEmail.body.trim()) {
      toast.error("Assunto e corpo são obrigatórios");
      return;
    }
    if (!newEmail.to_emails.trim()) {
      toast.error("Destinatário é obrigatório");
      return;
    }

    try {
      setCreating(true);
      
      // Preparar dados
      const toEmails = newEmail.to_emails.split(",").map(e => e.trim()).filter(e => e);
      
      await createEmail({
        process_id: processId,
        direction: newEmail.direction,
        from_email: newEmail.from_email || (newEmail.direction === "sent" ? "sistema@precisioncredito.pt" : clientEmail),
        to_emails: toEmails,
        subject: newEmail.subject,
        body: newEmail.body,
        notes: newEmail.notes,
        status: "sent"
      });
      
      toast.success("Email registado com sucesso");
      setIsCreateDialogOpen(false);
      setNewEmail({
        direction: "sent",
        from_email: "",
        to_emails: "",
        subject: "",
        body: "",
        notes: ""
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao registar email");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteEmail = async (emailId) => {
    if (!window.confirm("Tem a certeza que deseja eliminar este registo de email?")) return;
    try {
      await deleteEmail(emailId);
      toast.success("Email eliminado");
      fetchData();
    } catch (error) {
      toast.error("Erro ao eliminar email");
    }
  };

  const openCreateDialog = (direction = "sent") => {
    setNewEmail({
      direction,
      from_email: direction === "sent" ? "" : clientEmail || "",
      to_emails: direction === "sent" ? clientEmail || "" : "",
      subject: "",
      body: "",
      notes: ""
    });
    setIsCreateDialogOpen(true);
  };

  const toggleExpandEmail = (emailId) => {
    setExpandedEmail(expandedEmail === emailId ? null : emailId);
  };

  if (loading && emails.length === 0) {
    return (
      <Card className="border-border">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className="border-border">
        <CardHeader className={compact ? "pb-2" : ""}>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className={`flex items-center gap-2 ${compact ? "text-base" : "text-lg"}`}>
                <Mail className="h-5 w-5" />
                Histórico de Emails
                {stats.total > 0 && (
                  <Badge variant="secondary" className="ml-2">{stats.total}</Badge>
                )}
              </CardTitle>
              {!compact && (
                <CardDescription>
                  {stats.sent} enviado(s) • {stats.received} recebido(s)
                  {monitoredEmails.length > 0 && ` • ${monitoredEmails.length + 1} email(s) monitorizados`}
                </CardDescription>
              )}
            </div>
            <div className="flex gap-1">
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => setIsSettingsOpen(true)}
                title="Configurar emails monitorizados"
              >
                <Settings className="h-4 w-4" />
              </Button>
              <Button 
                size="sm" 
                variant="outline"
                onClick={handleSyncEmails}
                disabled={syncing || (!clientEmail && monitoredEmails.length === 0)}
                title="Sincronizar emails do servidor"
              >
                {syncing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
              </Button>
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => openCreateDialog("received")}
                title="Registar email recebido"
              >
                <Inbox className="h-4 w-4" />
              </Button>
              <Button 
                size="sm"
                onClick={() => openCreateDialog("sent")}
                className="bg-blue-900 hover:bg-blue-800"
                title="Registar email enviado"
              >
                <Send className="h-4 w-4 mr-1" />
                Novo
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filtros */}
          <Tabs value={filter} onValueChange={setFilter} className="mb-4">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="all" className="text-xs">
                Todos ({stats.total})
              </TabsTrigger>
              <TabsTrigger value="sent" className="text-xs">
                <Send className="h-3 w-3 mr-1" />
                Enviados ({stats.sent})
              </TabsTrigger>
              <TabsTrigger value="received" className="text-xs">
                <Inbox className="h-3 w-3 mr-1" />
                Recebidos ({stats.received})
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {/* Lista de emails */}
          {emails.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Mail className="h-12 w-12 mx-auto mb-2 opacity-20" />
              <p>Nenhum email registado</p>
              <Button 
                variant="outline" 
                className="mt-4"
                onClick={() => openCreateDialog("sent")}
              >
                <Plus className="h-4 w-4 mr-2" />
                Registar Email
              </Button>
            </div>
          ) : (
            <ScrollArea style={{ maxHeight }}>
              <div className="space-y-2">
                {emails.map((email) => (
                  <div
                    key={email.id}
                    className="border rounded-lg overflow-hidden"
                  >
                    {/* Header do email */}
                    <div 
                      className={`flex items-start gap-3 p-3 cursor-pointer hover:bg-muted/50 transition-colors ${
                        email.direction === "sent" 
                          ? "bg-blue-50/50 dark:bg-blue-950/20" 
                          : "bg-emerald-50/50 dark:bg-emerald-950/20"
                      }`}
                      onClick={() => toggleExpandEmail(email.id)}
                    >
                      {/* Ícone de direção */}
                      <div className={`mt-0.5 p-1.5 rounded ${
                        email.direction === "sent" 
                          ? "bg-blue-100 text-blue-600" 
                          : "bg-emerald-100 text-emerald-600"
                      }`}>
                        {email.direction === "sent" ? (
                          <Send className="h-4 w-4" />
                        ) : (
                          <Inbox className="h-4 w-4" />
                        )}
                      </div>

                      {/* Conteúdo */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="font-medium text-sm truncate">
                              {email.subject}
                            </p>
                            <p className="text-xs text-muted-foreground truncate">
                              {email.direction === "sent" ? "Para: " : "De: "}
                              {email.direction === "sent" 
                                ? email.to_emails?.join(", ")
                                : email.from_email
                              }
                            </p>
                          </div>
                          {expandedEmail === email.id ? (
                            <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            {email.sent_at 
                              ? format(parseISO(email.sent_at), "dd/MM/yyyy HH:mm", { locale: pt })
                              : "-"
                            }
                          </div>
                          {email.attachments?.length > 0 && (
                            <Badge variant="outline" className="text-[10px]">
                              <Paperclip className="h-3 w-3 mr-1" />
                              {email.attachments.length}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Corpo expandido */}
                    {expandedEmail === email.id && (
                      <div className="px-3 pb-3 border-t bg-background">
                        <div className="pt-3 space-y-3">
                          {/* Detalhes */}
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>
                              <span className="text-muted-foreground">De:</span>
                              <span className="ml-1">{email.from_email}</span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Para:</span>
                              <span className="ml-1">{email.to_emails?.join(", ")}</span>
                            </div>
                            {email.cc_emails?.length > 0 && (
                              <div className="col-span-2">
                                <span className="text-muted-foreground">CC:</span>
                                <span className="ml-1">{email.cc_emails.join(", ")}</span>
                              </div>
                            )}
                          </div>

                          {/* Corpo */}
                          <div className="bg-muted/30 rounded p-3 max-h-[300px] overflow-y-auto">
                            <p className="text-sm whitespace-pre-wrap">{email.body}</p>
                          </div>

                          {/* Notas */}
                          {email.notes && (
                            <div className="text-xs">
                              <span className="text-muted-foreground">Notas:</span>
                              <span className="ml-1">{email.notes}</span>
                            </div>
                          )}

                          {/* Registado por */}
                          {email.created_by_name && (
                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                              <User className="h-3 w-3" />
                              Registado por {email.created_by_name}
                            </div>
                          )}

                          {/* Ações */}
                          <div className="flex justify-end pt-2 border-t">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteEmail(email.id);
                              }}
                            >
                              <Trash2 className="h-4 w-4 mr-1" />
                              Eliminar
                            </Button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Dialog para registar email */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>
              {newEmail.direction === "sent" ? "Registar Email Enviado" : "Registar Email Recebido"}
            </DialogTitle>
            <DialogDescription>
              {newEmail.direction === "sent" 
                ? "Registe um email que foi enviado ao cliente"
                : "Registe um email que foi recebido do cliente"
              }
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Direção */}
            <div className="space-y-2">
              <Label>Tipo</Label>
              <Select 
                value={newEmail.direction} 
                onValueChange={(v) => setNewEmail(prev => ({ 
                  ...prev, 
                  direction: v,
                  from_email: v === "sent" ? "" : clientEmail || "",
                  to_emails: v === "sent" ? clientEmail || "" : ""
                }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sent">
                    <div className="flex items-center gap-2">
                      <Send className="h-4 w-4" />
                      Email Enviado
                    </div>
                  </SelectItem>
                  <SelectItem value="received">
                    <div className="flex items-center gap-2">
                      <Inbox className="h-4 w-4" />
                      Email Recebido
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>De</Label>
                <Input
                  placeholder="email@exemplo.pt"
                  value={newEmail.from_email}
                  onChange={(e) => setNewEmail(prev => ({ ...prev, from_email: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label>Para *</Label>
                <Input
                  placeholder="email@exemplo.pt (separar com vírgula)"
                  value={newEmail.to_emails}
                  onChange={(e) => setNewEmail(prev => ({ ...prev, to_emails: e.target.value }))}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Assunto *</Label>
              <Input
                placeholder="Assunto do email"
                value={newEmail.subject}
                onChange={(e) => setNewEmail(prev => ({ ...prev, subject: e.target.value }))}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Corpo do Email *</Label>
              <Textarea
                placeholder="Conteúdo do email..."
                value={newEmail.body}
                onChange={(e) => setNewEmail(prev => ({ ...prev, body: e.target.value }))}
                rows={6}
              />
            </div>

            <div className="space-y-2">
              <Label>Notas (opcional)</Label>
              <Input
                placeholder="Notas internas sobre este email"
                value={newEmail.notes}
                onChange={(e) => setNewEmail(prev => ({ ...prev, notes: e.target.value }))}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleCreateEmail} 
              disabled={creating}
              className="bg-blue-900 hover:bg-blue-800"
            >
              {creating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
              Registar Email
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog de Configurações de Emails Monitorizados */}
      <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AtSign className="h-5 w-5" />
              Emails Monitorizados
            </DialogTitle>
            <DialogDescription>
              Configure os emails que serão sincronizados para este processo.
              Os emails de geral@powerealestate.pt e geral@precisioncredito.pt são verificados automaticamente.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Email principal do cliente */}
            <div>
              <Label className="text-sm font-medium">Email Principal do Cliente</Label>
              <div className="flex items-center gap-2 mt-1 p-2 bg-muted rounded-md">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">{clientEmail || "Não definido"}</span>
                <Badge variant="outline" className="ml-auto text-xs">Principal</Badge>
              </div>
            </div>

            {/* Emails adicionais */}
            <div>
              <Label className="text-sm font-medium">Emails Adicionais</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Adicione outros emails relacionados com este processo (bancos, intermediários, etc.)
              </p>
              
              {/* Lista de emails monitorizados */}
              {monitoredEmails.length > 0 ? (
                <div className="space-y-2 mb-3">
                  {monitoredEmails.map((email) => (
                    <div key={email} className="flex items-center gap-2 p-2 bg-muted/50 rounded-md">
                      <AtSign className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm flex-1">{email}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                        onClick={() => handleRemoveMonitoredEmail(email)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground italic mb-3">
                  Nenhum email adicional configurado
                </p>
              )}

              {/* Adicionar novo email */}
              <div className="flex gap-2">
                <Input
                  placeholder="email@exemplo.pt"
                  value={newMonitoredEmail}
                  onChange={(e) => setNewMonitoredEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddMonitoredEmail()}
                />
                <Button 
                  onClick={handleAddMonitoredEmail}
                  disabled={addingEmail}
                  size="sm"
                >
                  {addingEmail ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Contas de email da empresa */}
            <div className="pt-2 border-t">
              <Label className="text-sm font-medium">Contas da Empresa</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Emails da empresa onde os emails são sincronizados
              </p>
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-sm">
                  <Badge variant="outline" className="text-xs">Precision</Badge>
                  geral@precisioncredito.pt
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Badge variant="outline" className="text-xs">Power</Badge>
                  geral@powerealestate.pt
                </div>
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsSettingsOpen(false)}>
              Fechar
            </Button>
            <Button 
              onClick={() => {
                setIsSettingsOpen(false);
                handleSyncEmails();
              }}
              className="bg-blue-900 hover:bg-blue-800"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Sincronizar Agora
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default EmailHistoryPanel;
