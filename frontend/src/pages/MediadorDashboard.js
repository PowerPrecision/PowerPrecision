import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { 
  getProcesses, getStats, getUpcomingExpiries, 
  createDocumentExpiry, getWorkflowStatuses, analyzeOneDriveDocument,
  getClientOneDriveFiles
} from "../services/api";
import {
  FileText, Search, Clock, ArrowRight, CreditCard, Users, Eye,
  AlertTriangle, Calendar, Plus, Loader2, Sparkles, FolderOpen, Euro
} from "lucide-react";
import { toast } from "sonner";
import { format, parseISO, differenceInDays } from "date-fns";
import { pt } from "date-fns/locale";

const typeLabels = {
  credito: "Crédito",
  imobiliaria: "Imobiliária",
  ambos: "Crédito + Imobiliária",
};

const DOCUMENT_TYPES = [
  { type: "cc", name: "Cartão de Cidadão" },
  { type: "passaporte", name: "Passaporte" },
  { type: "comprovativo_iban", name: "Comprovativo IBAN" },
  { type: "recibo_vencimento", name: "Recibo de Vencimento" },
  { type: "declaracao_irs", name: "Declaração de IRS" },
  { type: "nota_liquidacao", name: "Nota de Liquidação IRS" },
  { type: "contrato_trabalho", name: "Contrato de Trabalho" },
  { type: "mapa_responsabilidades", name: "Mapa Responsabilidades BP" },
  { type: "outro", name: "Outro" },
];

const MediadorDashboard = () => {
  const [processes, setProcesses] = useState([]);
  const [workflowStatuses, setWorkflowStatuses] = useState([]);
  const [upcomingExpiries, setUpcomingExpiries] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [activeTab, setActiveTab] = useState("clients");
  
  // Dialog states
  const [isAddExpiryOpen, setIsAddExpiryOpen] = useState(false);
  const [selectedProcessId, setSelectedProcessId] = useState("");
  const [expiryFormData, setExpiryFormData] = useState({
    document_type: "",
    document_name: "",
    expiry_date: "",
    notes: ""
  });
  const [formLoading, setFormLoading] = useState(false);
  
  // AI Analysis states
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [oneDriveFiles, setOneDriveFiles] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [processesRes, statsRes, expiriesRes, statusesRes] = await Promise.all([
        getProcesses(),
        getStats(),
        getUpcomingExpiries(60),
        getWorkflowStatuses()
      ]);
      setProcesses(processesRes.data);
      setStats(statsRes.data);
      setUpcomingExpiries(expiriesRes.data);
      setWorkflowStatuses(statusesRes.data);
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  };

  const filteredProcesses = useMemo(() => {
    return processes.filter(process => {
      const matchesSearch = 
        process.client_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        process.client_email.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === "all" || process.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [processes, searchTerm, statusFilter]);

  // Credit-specific processes (credito or ambos)
  const creditProcesses = useMemo(() => {
    return filteredProcesses.filter(p => p.process_type === "credito" || p.process_type === "ambos");
  }, [filteredProcesses]);

  const getStatusBadge = (status) => {
    const statusInfo = workflowStatuses.find(s => s.name === status);
    if (!statusInfo) return <Badge variant="outline">{status}</Badge>;
    
    const colorClasses = {
      yellow: "bg-yellow-100 text-yellow-800",
      blue: "bg-blue-100 text-blue-800",
      orange: "bg-orange-100 text-orange-800",
      green: "bg-green-100 text-green-800",
      red: "bg-red-100 text-red-800",
      purple: "bg-purple-100 text-purple-800",
    };
    
    return (
      <Badge className={`${colorClasses[statusInfo.color] || "bg-gray-100 text-gray-800"} border`}>
        {statusInfo.label}
      </Badge>
    );
  };

  const getExpiryUrgency = (expiryDate) => {
    const days = differenceInDays(parseISO(expiryDate), new Date());
    if (days < 0) return { color: "text-red-600 bg-red-50", label: "Expirado" };
    if (days <= 7) return { color: "text-red-600 bg-red-50", label: `${days} dias` };
    if (days <= 30) return { color: "text-orange-600 bg-orange-50", label: `${days} dias` };
    return { color: "text-green-600 bg-green-50", label: `${days} dias` };
  };

  const handleAddExpiry = async (e) => {
    e.preventDefault();
    if (!selectedProcessId) return;
    
    setFormLoading(true);
    try {
      await createDocumentExpiry({
        process_id: selectedProcessId,
        ...expiryFormData
      });
      toast.success("Data de documento adicionada");
      setIsAddExpiryOpen(false);
      setExpiryFormData({ document_type: "", document_name: "", expiry_date: "", notes: "" });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao adicionar");
    } finally {
      setFormLoading(false);
    }
  };

  const openAddExpiryDialog = (processId) => {
    setSelectedProcessId(processId);
    setIsAddExpiryOpen(true);
  };

  const loadClientFiles = async (process) => {
    setSelectedClient(process);
    setAnalysisResult(null);
    try {
      const res = await getClientOneDriveFiles(process.client_name);
      setOneDriveFiles(res.data);
    } catch (error) {
      console.error("Error loading OneDrive files:", error);
      setOneDriveFiles([]);
    }
  };

  const analyzeDocumentWithAI = async (fileName, docType) => {
    if (!selectedClient) return;
    
    setIsAnalyzing(true);
    setAnalysisResult(null);
    try {
      const res = await analyzeOneDriveDocument({
        client_folder: selectedClient.client_name,
        file_name: fileName,
        document_type: docType
      });
      
      if (res.data.success) {
        toast.success("Documento analisado com sucesso!");
        setAnalysisResult({
          fileName,
          docType,
          extracted: res.data.extracted_data,
          mapped: res.data.mapped_data
        });
        
        // Auto-fill expiry if available
        const extracted = res.data.extracted_data;
        if (extracted.data_validade) {
          setExpiryFormData(prev => ({
            ...prev,
            document_type: docType,
            expiry_date: extracted.data_validade,
            document_name: fileName
          }));
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao analisar documento");
    } finally {
      setIsAnalyzing(false);
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
      <div className="space-y-6" data-testid="mediador-dashboard">
        <div>
          <h1 className="text-2xl font-bold">Painel do Mediador de Crédito</h1>
          <p className="text-muted-foreground">Gestão dos seus clientes e processos de crédito</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
                  <Users className="h-6 w-6 text-emerald-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{creditProcesses.length}</p>
                  <p className="text-sm text-muted-foreground">Processos Crédito</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
                  <Clock className="h-6 w-6 text-yellow-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.pending_deadlines || 0}</p>
                  <p className="text-sm text-muted-foreground">Prazos Pendentes</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                  <AlertTriangle className="h-6 w-6 text-orange-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{upcomingExpiries.length}</p>
                  <p className="text-sm text-muted-foreground">Docs a Expirar</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-100 dark:bg-teal-600/30 rounded-lg">
                  <Euro className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{creditProcesses.filter(p => p.status === "autorizacao_bancaria" || p.status === "aprovado").length}</p>
                  <p className="text-sm text-muted-foreground">Em Aprovação</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="clients" className="gap-2">
              <CreditCard className="h-4 w-4" />
              Meus Clientes
            </TabsTrigger>
            <TabsTrigger value="documents" className="gap-2">
              <Calendar className="h-4 w-4" />
              Documentos a Expirar
            </TabsTrigger>
            <TabsTrigger value="ai" className="gap-2">
              <Sparkles className="h-4 w-4" />
              Análise IA
            </TabsTrigger>
          </TabsList>

          {/* Clients Tab */}
          <TabsContent value="clients" className="mt-6">
            <Card className="border-border">
              <CardHeader>
                <div className="flex flex-col sm:flex-row gap-4 justify-between">
                  <div>
                    <CardTitle className="text-lg">Os Meus Clientes de Crédito</CardTitle>
                    <CardDescription>Processos de crédito atribuídos a si</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input 
                        placeholder="Pesquisar..." 
                        className="pl-10 w-64" 
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                      />
                    </div>
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger className="w-40">
                        <SelectValue placeholder="Estado" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos</SelectItem>
                        {workflowStatuses.map((s) => (
                          <SelectItem key={s.name} value={s.name}>{s.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Cliente</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Rendimento</TableHead>
                        <TableHead>Valor Financiar</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead className="text-right">Ações</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {creditProcesses.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                            Nenhum processo encontrado
                          </TableCell>
                        </TableRow>
                      ) : (
                        creditProcesses.map((process) => (
                          <TableRow key={process.id}>
                            <TableCell className="font-medium">{process.client_name}</TableCell>
                            <TableCell>{process.client_email}</TableCell>
                            <TableCell>
                              {process.financial_data?.monthly_income 
                                ? `€${process.financial_data.monthly_income.toLocaleString()}` 
                                : "-"}
                            </TableCell>
                            <TableCell>
                              {process.financial_data?.valor_financiado || "-"}
                            </TableCell>
                            <TableCell>{getStatusBadge(process.status)}</TableCell>
                            <TableCell className="text-right">
                              <Button variant="ghost" size="icon" onClick={() => navigate(`/process/${process.id}`)}>
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="icon" onClick={() => openAddExpiryDialog(process.id)}>
                                <Plus className="h-4 w-4" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Documents Expiry Tab */}
          <TabsContent value="documents" className="mt-6">
            <Card className="border-border">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-orange-500" />
                  Documentos a Expirar (Próximos 60 dias)
                </CardTitle>
                <CardDescription>Documentos dos seus clientes que estão próximos da data de validade</CardDescription>
              </CardHeader>
              <CardContent>
                {upcomingExpiries.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Nenhum documento a expirar nos próximos 60 dias</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {upcomingExpiries.map((doc) => {
                      const urgency = getExpiryUrgency(doc.expiry_date);
                      return (
                        <div key={doc.id} className={`flex items-center justify-between p-4 rounded-lg ${urgency.color}`}>
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <p className="font-medium">{doc.document_name}</p>
                              <Badge variant="outline" className="text-xs">{doc.document_type}</Badge>
                            </div>
                            <p className="text-sm">
                              Cliente: {doc.client_name} • {doc.client_email}
                            </p>
                            <p className="text-sm">
                              Expira: {format(parseISO(doc.expiry_date), "dd/MM/yyyy", { locale: pt })}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="font-mono">
                              {urgency.label}
                            </Badge>
                            <Button variant="ghost" size="icon" onClick={() => navigate(`/process/${doc.process_id}`)}>
                              <ArrowRight className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* AI Analysis Tab */}
          <TabsContent value="ai" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="border-border">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-purple-500" />
                    Análise de Documentos com IA
                  </CardTitle>
                  <CardDescription>
                    Extraia automaticamente dados financeiros de recibos de vencimento e IRS
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label>Selecione um cliente</Label>
                      <Select onValueChange={(value) => {
                        const process = creditProcesses.find(p => p.id === value);
                        if (process) loadClientFiles(process);
                      }}>
                        <SelectTrigger>
                          <SelectValue placeholder="Escolha um cliente" />
                        </SelectTrigger>
                        <SelectContent>
                          {creditProcesses.map((p) => (
                            <SelectItem key={p.id} value={p.id}>{p.client_name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {selectedClient && (
                      <div className="p-4 bg-muted/50 rounded-lg">
                        <p className="font-medium mb-2">Cliente: {selectedClient.client_name}</p>
                        <p className="text-sm text-muted-foreground">Pasta OneDrive: {selectedClient.client_name}</p>
                      </div>
                    )}

                    {analysisResult && (
                      <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                        <p className="font-medium text-green-800 dark:text-green-200 mb-2">
                          ✓ Dados Extraídos: {analysisResult.fileName}
                        </p>
                        <div className="text-sm space-y-1">
                          {analysisResult.mapped?.financial_data && (
                            <>
                              <p><strong>Salário Líquido:</strong> €{analysisResult.mapped.financial_data.monthly_income || "N/D"}</p>
                              <p><strong>Empresa:</strong> {analysisResult.mapped.financial_data.employer_name || "N/D"}</p>
                              <p><strong>Tipo Contrato:</strong> {analysisResult.mapped.financial_data.employment_type || "N/D"}</p>
                            </>
                          )}
                          {analysisResult.mapped?.personal_data && (
                            <>
                              <p><strong>NIF:</strong> {analysisResult.mapped.personal_data.nif || "N/D"}</p>
                              <p><strong>Data Nascimento:</strong> {analysisResult.mapped.personal_data.birth_date || "N/D"}</p>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FolderOpen className="h-5 w-5" />
                    Ficheiros do OneDrive
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {!selectedClient ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <FolderOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Selecione um cliente para ver os ficheiros</p>
                    </div>
                  ) : oneDriveFiles.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>Nenhum ficheiro encontrado ou OneDrive não configurado</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {oneDriveFiles.map((file) => (
                        <div key={file.id} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                          <div className="flex items-center gap-3">
                            <FileText className="h-5 w-5 text-muted-foreground" />
                            <span className="text-sm">{file.name}</span>
                          </div>
                          <Select onValueChange={(docType) => analyzeDocumentWithAI(file.name, docType)}>
                            <SelectTrigger className="w-44">
                              <SelectValue placeholder="Analisar como..." />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="cc">Cartão Cidadão</SelectItem>
                              <SelectItem value="recibo_vencimento">Recibo Vencimento</SelectItem>
                              <SelectItem value="irs">Declaração IRS</SelectItem>
                              <SelectItem value="outro">Outro</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      ))}
                      {isAnalyzing && (
                        <div className="flex items-center justify-center py-4">
                          <Loader2 className="h-5 w-5 animate-spin mr-2" />
                          <span>A analisar documento com IA...</span>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Add Document Expiry Dialog */}
        <Dialog open={isAddExpiryOpen} onOpenChange={setIsAddExpiryOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Adicionar Data de Validade de Documento</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleAddExpiry} className="space-y-4">
              <div className="space-y-2">
                <Label>Tipo de Documento</Label>
                <Select 
                  value={expiryFormData.document_type} 
                  onValueChange={(v) => setExpiryFormData(prev => ({ ...prev, document_type: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione" />
                  </SelectTrigger>
                  <SelectContent>
                    {DOCUMENT_TYPES.map((dt) => (
                      <SelectItem key={dt.type} value={dt.type}>{dt.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Nome do Documento</Label>
                <Input 
                  value={expiryFormData.document_name}
                  onChange={(e) => setExpiryFormData(prev => ({ ...prev, document_name: e.target.value }))}
                  placeholder="Ex: CC João Silva"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Data de Validade</Label>
                <Input 
                  type="date"
                  value={expiryFormData.expiry_date}
                  onChange={(e) => setExpiryFormData(prev => ({ ...prev, expiry_date: e.target.value }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Notas (opcional)</Label>
                <Input 
                  value={expiryFormData.notes}
                  onChange={(e) => setExpiryFormData(prev => ({ ...prev, notes: e.target.value }))}
                  placeholder="Notas adicionais..."
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={formLoading}>
                  {formLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Adicionar"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
};

export default MediadorDashboard;
