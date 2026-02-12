import { useState, useEffect, useCallback } from "react";
import DashboardLayout from "../layouts/DashboardLayout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { ScrollArea } from "../components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
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
  CheckCircle2,
  FileText,
  Loader2,
  RefreshCw,
  Eye,
  Check,
  X,
  ArrowRight,
  Clock,
  User,
  FileSearch,
  AlertTriangle,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import api from "../services/api";

// Mapeamento de nomes de campos para português
const fieldLabels = {
  "personal_data.nome": "Nome Completo",
  "personal_data.nif": "NIF",
  "personal_data.cc_number": "Nº Cartão Cidadão",
  "personal_data.data_nascimento": "Data de Nascimento",
  "personal_data.data_validade_cc": "Validade do CC",
  "personal_data.morada": "Morada",
  "personal_data.codigo_postal": "Código Postal",
  "personal_data.localidade": "Localidade",
  "personal_data.estado_civil": "Estado Civil",
  "personal_data.nacionalidade": "Nacionalidade",
  "financial_data.rendimento_mensal": "Rendimento Mensal",
  "financial_data.entidade_patronal": "Entidade Patronal",
  "financial_data.tipo_contrato": "Tipo de Contrato",
  "financial_data.antiguidade": "Antiguidade",
  "financial_data.encargos_mensais": "Encargos Mensais",
  "real_estate_data.valor_imovel": "Valor do Imóvel",
  "real_estate_data.tipologia": "Tipologia",
  "real_estate_data.morada_imovel": "Morada do Imóvel",
  "real_estate_data.artigo_matricial": "Artigo Matricial",
  "client_name": "Nome do Cliente",
  "client_email": "Email",
  "client_phone": "Telefone",
  "client_nif": "NIF",
};

// Mapeamento de tipos de documento para português
const documentTypeLabels = {
  "cc": "Cartão de Cidadão",
  "recibo_vencimento": "Recibo de Vencimento",
  "irs": "Declaração IRS",
  "contrato_trabalho": "Contrato de Trabalho",
  "cpcv": "CPCV",
  "caderneta_predial": "Caderneta Predial",
  "simulacao": "Simulação de Crédito",
  "extrato_bancario": "Extrato Bancário",
  "outro": "Outro Documento",
};

const AIDataReviewPage = () => {
  const [pendingReviews, setPendingReviews] = useState([]);
  const [selectedProcess, setSelectedProcess] = useState(null);
  const [processComparison, setProcessComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingComparison, setLoadingComparison] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [applyingField, setApplyingField] = useState(null);

  // Carregar revisões pendentes
  const loadPendingReviews = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get("/ai/bulk/pending-reviews");
      setPendingReviews(response.data.processes || []);
    } catch (error) {
      console.error("Erro ao carregar revisões pendentes:", error);
      toast.error("Erro ao carregar revisões pendentes");
    } finally {
      setLoading(false);
    }
  }, []);

  // Carregar comparação de dados do processo
  const loadProcessComparison = async (processId) => {
    try {
      setLoadingComparison(true);
      const response = await api.get(`/ai/bulk/compare-data/${processId}`);
      setProcessComparison(response.data);
    } catch (error) {
      console.error("Erro ao carregar comparação:", error);
      toast.error("Erro ao carregar comparação de dados");
    } finally {
      setLoadingComparison(false);
    }
  };

  // Aplicar dados pendentes
  const applyPendingData = async (processId, itemIndex, force = false) => {
    try {
      setApplyingField(`apply-${itemIndex}`);
      const response = await api.post(`/ai/bulk/apply-pending/${processId}?item_index=${itemIndex}&force=${force}`);
      
      if (response.data.success) {
        toast.success("Dados aplicados com sucesso!");
        await loadPendingReviews();
        if (selectedProcess?.process_id === processId) {
          await loadProcessComparison(processId);
        }
      } else {
        toast.error("Falha ao aplicar dados");
      }
    } catch (error) {
      console.error("Erro ao aplicar dados:", error);
      toast.error("Erro ao aplicar dados pendentes");
    } finally {
      setApplyingField(null);
    }
  };

  // Descartar dados pendentes
  const discardPendingData = async (processId, itemIndex) => {
    try {
      setApplyingField(`discard-${itemIndex}`);
      const response = await api.delete(`/ai/bulk/discard-pending/${processId}?item_index=${itemIndex}`);
      
      if (response.data.success) {
        toast.success("Dados descartados");
        await loadPendingReviews();
        if (selectedProcess?.process_id === processId) {
          await loadProcessComparison(processId);
        }
      }
    } catch (error) {
      console.error("Erro ao descartar dados:", error);
      toast.error("Erro ao descartar dados");
    } finally {
      setApplyingField(null);
    }
  };

  // Abrir dialog de detalhes
  const openProcessDetails = async (process) => {
    setSelectedProcess(process);
    setDialogOpen(true);
    await loadProcessComparison(process.process_id);
  };

  useEffect(() => {
    loadPendingReviews();
  }, [loadPendingReviews]);

  // Formatar data
  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    try {
      return new Date(dateStr).toLocaleDateString("pt-PT", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  // Obter label do campo
  const getFieldLabel = (field) => fieldLabels[field] || field;
  
  // Obter label do tipo de documento
  const getDocumentTypeLabel = (type) => documentTypeLabels[type] || type;

  // Formatar valor para exibição
  const formatValue = (value) => {
    if (value === null || value === undefined) return <span className="text-muted-foreground italic">Não preenchido</span>;
    if (typeof value === "boolean") return value ? "Sim" : "Não";
    if (typeof value === "number") {
      if (value >= 1000) return value.toLocaleString("pt-PT", { style: "currency", currency: "EUR" });
      return value.toString();
    }
    return String(value);
  };

  return (
    <DashboardLayout title="Revisão de Dados IA">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Revisão de Dados IA</h1>
            <p className="text-muted-foreground">
              Compare e valide dados extraídos automaticamente pela IA
            </p>
          </div>
          <Button onClick={loadPendingReviews} variant="outline" disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Actualizar
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Processos Pendentes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <FileSearch className="h-5 w-5 text-amber-500" />
                <span className="text-2xl font-bold">{pendingReviews.length}</span>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total de Itens para Revisão
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-orange-500" />
                <span className="text-2xl font-bold">
                  {pendingReviews.reduce((acc, p) => acc + (p.pending_count || 0), 0)}
                </span>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Tipos de Documentos
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-blue-500" />
                <span className="text-2xl font-bold">
                  {[...new Set(pendingReviews.flatMap(p => p.document_types || []))].length}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-amber-500" />
              Processos com Dados Pendentes de Revisão
            </CardTitle>
            <CardDescription>
              Estes processos têm dados extraídos pela IA que aguardam validação manual
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center items-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : pendingReviews.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircle2 className="h-12 w-12 text-green-500 mb-4" />
                <h3 className="text-lg font-medium">Tudo em dia!</h3>
                <p className="text-muted-foreground mt-1">
                  Não há dados pendentes de revisão
                </p>
              </div>
            ) : (
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Cliente</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Itens Pendentes</TableHead>
                      <TableHead>Tipos de Documento</TableHead>
                      <TableHead>Mais Antigo</TableHead>
                      <TableHead className="text-right">Acções</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pendingReviews.map((process) => (
                      <TableRow key={process.process_id} data-testid={`review-row-${process.process_id}`}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium">{process.client_name}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={process.status === "concluido" ? "secondary" : "outline"}>
                            {process.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="destructive" className="tabular-nums">
                            {process.pending_count}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {(process.document_types || []).slice(0, 3).map((type) => (
                              <Badge key={type} variant="outline" className="text-xs">
                                {getDocumentTypeLabel(type)}
                              </Badge>
                            ))}
                            {(process.document_types || []).length > 3 && (
                              <Badge variant="outline" className="text-xs">
                                +{process.document_types.length - 3}
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-muted-foreground text-sm">
                            <Clock className="h-3 w-3" />
                            {formatDate(process.oldest_pending)}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            size="sm"
                            onClick={() => openProcessDetails(process)}
                            data-testid={`review-details-btn-${process.process_id}`}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            Rever
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Dialog de Detalhes */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-4xl max-h-[90vh]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileSearch className="h-5 w-5 text-amber-500" />
                Revisão de Dados - {selectedProcess?.client_name}
              </DialogTitle>
              <DialogDescription>
                Compare os dados actuais com os dados extraídos pela IA e escolha quais aplicar
              </DialogDescription>
            </DialogHeader>

            {loadingComparison ? (
              <div className="flex justify-center items-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : processComparison ? (
              <Tabs defaultValue="differences" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="differences">
                    Diferenças ({processComparison.fields_with_differences})
                  </TabsTrigger>
                  <TabsTrigger value="all">
                    Todos os Campos ({processComparison.total_fields_compared})
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="differences" className="mt-4">
                  <ScrollArea className="h-[400px]">
                    {processComparison.comparisons
                      .filter((c) => c.has_difference)
                      .map((comparison, idx) => (
                        <Card key={comparison.field} className="mb-3" data-testid={`comparison-card-${comparison.field}`}>
                          <CardContent className="pt-4">
                            <div className="flex flex-col gap-3">
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-sm">
                                  {getFieldLabel(comparison.field)}
                                </span>
                                {comparison.has_pending && (
                                  <Badge variant="destructive" className="text-xs">
                                    Pendente
                                  </Badge>
                                )}
                              </div>
                              
                              <div className="grid grid-cols-3 gap-4 text-sm">
                                {/* Valor Actual */}
                                <div className="p-3 bg-muted rounded-lg">
                                  <p className="text-xs text-muted-foreground mb-1">Valor Actual</p>
                                  <p className="font-medium">{formatValue(comparison.current_value)}</p>
                                </div>

                                {/* Seta */}
                                <div className="flex items-center justify-center">
                                  <ArrowRight className="h-5 w-5 text-muted-foreground" />
                                </div>

                                {/* Valor Extraído */}
                                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                                  <p className="text-xs text-amber-700 mb-1">
                                    {comparison.pending_document
                                      ? `Extraído de ${getDocumentTypeLabel(comparison.pending_document)}`
                                      : `Extraído de ${getDocumentTypeLabel(comparison.latest_document)}`}
                                  </p>
                                  <p className="font-medium text-amber-900">
                                    {formatValue(comparison.pending_value || comparison.latest_extracted)}
                                  </p>
                                  {(comparison.pending_value || comparison.latest_date) && (
                                    <p className="text-xs text-amber-600 mt-1">
                                      {formatDate(comparison.latest_date)}
                                    </p>
                                  )}
                                </div>
                              </div>

                              {/* Acções para campos pendentes */}
                              {comparison.has_pending && (
                                <div className="flex justify-end gap-2 mt-2">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => discardPendingData(selectedProcess.process_id, idx)}
                                    disabled={applyingField !== null}
                                    data-testid={`discard-btn-${comparison.field}`}
                                  >
                                    {applyingField === `discard-${idx}` ? (
                                      <Loader2 className="h-4 w-4 animate-spin mr-1" />
                                    ) : (
                                      <X className="h-4 w-4 mr-1" />
                                    )}
                                    Descartar
                                  </Button>
                                  <Button
                                    size="sm"
                                    onClick={() => applyPendingData(selectedProcess.process_id, idx)}
                                    disabled={applyingField !== null}
                                    data-testid={`apply-btn-${comparison.field}`}
                                  >
                                    {applyingField === `apply-${idx}` ? (
                                      <Loader2 className="h-4 w-4 animate-spin mr-1" />
                                    ) : (
                                      <Check className="h-4 w-4 mr-1" />
                                    )}
                                    Aplicar
                                  </Button>
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    
                    {processComparison.comparisons.filter((c) => c.has_difference).length === 0 && (
                      <div className="flex flex-col items-center justify-center py-8 text-center">
                        <CheckCircle2 className="h-10 w-10 text-green-500 mb-3" />
                        <p className="text-muted-foreground">
                          Não há diferenças entre os dados actuais e os extraídos
                        </p>
                      </div>
                    )}
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="all" className="mt-4">
                  <ScrollArea className="h-[400px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Campo</TableHead>
                          <TableHead>Valor Actual</TableHead>
                          <TableHead>Último Extraído</TableHead>
                          <TableHead>Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {processComparison.comparisons.map((comparison) => (
                          <TableRow
                            key={comparison.field}
                            className={comparison.has_difference ? "bg-amber-50/50" : ""}
                          >
                            <TableCell className="font-medium text-sm">
                              {getFieldLabel(comparison.field)}
                            </TableCell>
                            <TableCell className="text-sm">
                              {formatValue(comparison.current_value)}
                            </TableCell>
                            <TableCell className="text-sm">
                              {formatValue(comparison.latest_extracted)}
                            </TableCell>
                            <TableCell>
                              {comparison.has_pending ? (
                                <Badge variant="destructive" className="text-xs">Pendente</Badge>
                              ) : comparison.has_difference ? (
                                <Badge variant="outline" className="text-xs text-amber-700 border-amber-300">Diferente</Badge>
                              ) : (
                                <Badge variant="outline" className="text-xs text-green-700 border-green-300">OK</Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </TabsContent>
              </Tabs>
            ) : null}

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Fechar
              </Button>
              <Button
                variant="default"
                onClick={() => window.open(`/processo/${selectedProcess?.process_id}`, "_blank")}
              >
                <Eye className="h-4 w-4 mr-2" />
                Ver Processo Completo
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
};

export default AIDataReviewPage;
