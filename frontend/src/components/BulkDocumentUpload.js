/**
 * BulkDocumentUpload - Upload massivo de documentos para análise com IA
 * Apenas disponível para administradores
 * 
 * Mostra progresso individual por ficheiro usando Server-Sent Events (SSE)
 */
import { useState, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import { ScrollArea } from "./ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./ui/dialog";
import {
  Sparkles,
  Upload,
  Loader2,
  FolderUp,
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileText,
  Users,
  RefreshCw,
  Clock,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../contexts/AuthContext";

const API_URL = process.env.REACT_APP_BACKEND_URL || "";

// Estados possíveis de um ficheiro
const FILE_STATUS = {
  PENDING: "pending",
  PROCESSING: "processing",
  SUCCESS: "success",
  ERROR: "error",
};

const BulkDocumentUpload = () => {
  const { token, user } = useAuth();
  const folderInputRef = useRef(null);
  
  const [isOpen, setIsOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [fileStatuses, setFileStatuses] = useState({}); // filename -> {status, message, fields}
  const [summary, setSummary] = useState(null);
  const [clientsList, setClientsList] = useState([]);
  const [loadingClients, setLoadingClients] = useState(false);

  // Verificar se é admin
  if (user?.role !== "admin") {
    return null;
  }

  // Carregar lista de clientes
  const loadClientsList = async () => {
    setLoadingClients(true);
    try {
      const response = await fetch(`${API_URL}/api/ai/bulk/clients-list`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setClientsList(data.clients || []);
      }
    } catch (error) {
      console.error("Erro ao carregar clientes:", error);
    } finally {
      setLoadingClients(false);
    }
  };

  // Selecionar pasta/ficheiros
  const handleFolderSelect = (e) => {
    const files = Array.from(e.target.files || []);
    // Filtrar apenas PDFs e imagens
    const validFiles = files.filter((f) => {
      const ext = f.name.toLowerCase().split(".").pop();
      return ["pdf", "jpg", "jpeg", "png", "webp"].includes(ext);
    });
    setSelectedFiles(validFiles);
    setSummary(null);
    setFileStatuses({});
  };

  // Agrupar ficheiros por cliente
  const getFilesByClient = () => {
    const grouped = {};
    selectedFiles.forEach((file) => {
      const path = file.webkitRelativePath || file.name;
      const parts = path.split("/");
      const clientName = parts.length >= 2 ? parts[parts.length - 2] : "Desconhecido";
      if (!grouped[clientName]) {
        grouped[clientName] = [];
      }
      grouped[clientName].push({ file, path });
    });
    return grouped;
  };

  // Actualizar estado de um ficheiro
  const updateFileStatus = (filename, status, message = "", fields = []) => {
    setFileStatuses((prev) => ({
      ...prev,
      [filename]: { status, message, fields },
    }));
  };

  // Fazer upload e análise com streaming de progresso
  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      toast.error("Selecione uma pasta com documentos");
      return;
    }

    setUploading(true);
    setSummary(null);
    
    // Inicializar todos os ficheiros como pending
    const initialStatuses = {};
    selectedFiles.forEach((file) => {
      const path = file.webkitRelativePath || file.name;
      initialStatuses[path] = { status: FILE_STATUS.PENDING, message: "A aguardar..." };
    });
    setFileStatuses(initialStatuses);

    try {
      const formData = new FormData();
      selectedFiles.forEach((file) => {
        const path = file.webkitRelativePath || file.name;
        formData.append("files", file, path);
      });

      // Usar endpoint com streaming
      const response = await fetch(`${API_URL}/api/ai/bulk/analyze-stream`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Erro ao iniciar processamento");
      }

      // Processar eventos SSE
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Guardar linha incompleta

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              handleSSEEvent(data);
            } catch (e) {
              console.warn("Erro ao processar SSE:", e);
            }
          }
        }
      }
    } catch (error) {
      toast.error(error.message);
      setSummary({ success: false, error: error.message });
    } finally {
      setUploading(false);
    }
  };

  // Processar eventos SSE
  const handleSSEEvent = (data) => {
    const { type, file, client, error, fields, updated, total, processed, updated_clients, errors_count } = data;

    switch (type) {
      case "start":
        toast.info(`A processar ${total} ficheiros...`);
        break;

      case "processing":
        updateFileStatus(
          findFilePath(file, client),
          FILE_STATUS.PROCESSING,
          "A analisar com IA..."
        );
        break;

      case "success":
        updateFileStatus(
          findFilePath(file, client),
          FILE_STATUS.SUCCESS,
          updated ? "Ficha actualizada" : "Analisado",
          fields || []
        );
        break;

      case "error":
        updateFileStatus(
          findFilePath(file, client),
          FILE_STATUS.ERROR,
          error || "Erro desconhecido"
        );
        break;

      case "complete":
        setSummary({
          success: true,
          total,
          processed,
          updated_clients,
          errors_count,
        });
        if (processed > 0) {
          toast.success(`Processados ${processed}/${total} documentos. ${updated_clients} clientes actualizados.`);
        } else {
          toast.warning("Nenhum documento foi processado com sucesso");
        }
        break;

      default:
        break;
    }
  };

  // Encontrar path completo do ficheiro
  const findFilePath = (filename, clientName) => {
    for (const file of selectedFiles) {
      const path = file.webkitRelativePath || file.name;
      if (path.endsWith(filename) && path.includes(clientName)) {
        return path;
      }
    }
    return `${clientName}/${filename}`;
  };

  const resetState = () => {
    setSelectedFiles([]);
    setSummary(null);
    setFileStatuses({});
    if (folderInputRef.current) {
      folderInputRef.current.value = "";
    }
  };

  const filesByClient = getFilesByClient();
  const clientCount = Object.keys(filesByClient).length;

  // Calcular progresso geral
  const totalFiles = selectedFiles.length;
  const completedFiles = Object.values(fileStatuses).filter(
    (s) => s.status === FILE_STATUS.SUCCESS || s.status === FILE_STATUS.ERROR
  ).length;
  const progressPercent = totalFiles > 0 ? Math.round((completedFiles / totalFiles) * 100) : 0;

  // Ícone de estado do ficheiro
  const getStatusIcon = (status) => {
    switch (status) {
      case FILE_STATUS.SUCCESS:
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case FILE_STATUS.ERROR:
        return <XCircle className="h-4 w-4 text-red-500" />;
      case FILE_STATUS.PROCESSING:
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => {
      setIsOpen(open);
      if (open) loadClientsList();
    }}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          className="bg-gradient-to-r from-purple-500 to-indigo-500 text-white border-0 hover:from-purple-600 hover:to-indigo-600"
          data-testid="bulk-upload-btn"
        >
          <FolderUp className="h-4 w-4 mr-2" />
          Upload Massivo IA
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            Upload Massivo de Documentos
          </DialogTitle>
          <DialogDescription>
            Selecione uma pasta com subpastas de clientes. A IA analisa os documentos e preenche as fichas automaticamente.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {/* Instruções */}
          {!uploading && !summary && (
            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="pt-4">
                <h4 className="font-medium text-blue-800 mb-2">📁 Estrutura esperada:</h4>
                <pre className="text-xs bg-white/50 p-2 rounded text-blue-700">
{`PastaRaiz/
├── João Silva/
│   ├── CC.pdf
│   ├── Recibo_Vencimento.pdf
│   └── IRS.pdf
├── Maria Santos/
│   ├── CartaoCidadao.jpg
│   └── Contrato.pdf
└── ...`}
                </pre>
                <p className="text-xs text-blue-600 mt-2">
                  O nome da pasta deve corresponder ao nome do cliente no sistema. Máx. 10MB por ficheiro.
                </p>
              </CardContent>
            </Card>
          )}

          {/* Selecção de pasta */}
          {!uploading && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <input
                  ref={folderInputRef}
                  type="file"
                  webkitdirectory="true"
                  directory="true"
                  multiple
                  onChange={handleFolderSelect}
                  className="hidden"
                  id="folder-input"
                />
                <Button
                  variant="outline"
                  onClick={() => folderInputRef.current?.click()}
                  className="flex-1"
                  disabled={uploading}
                >
                  <FolderUp className="h-4 w-4 mr-2" />
                  Selecionar Pasta
                </Button>
                {selectedFiles.length > 0 && (
                  <Button variant="ghost" size="icon" onClick={resetState}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Progresso geral */}
          {uploading && (
            <div className="space-y-2 p-4 bg-purple-50 rounded-lg">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">A processar documentos com IA...</span>
                <span>{completedFiles}/{totalFiles} ({progressPercent}%)</span>
              </div>
              <Progress value={progressPercent} className="h-3" />
            </div>
          )}

          {/* Lista de ficheiros com progresso individual */}
          {selectedFiles.length > 0 && (
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Ficheiros
                  </span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{selectedFiles.length} ficheiros</Badge>
                    <Badge variant="secondary">{clientCount} clientes</Badge>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <ScrollArea className="h-[300px]">
                  <div className="space-y-3">
                    {Object.entries(filesByClient).map(([clientName, files]) => (
                      <div key={clientName} className="border rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <Users className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium text-sm">{clientName}</span>
                          <Badge variant="outline" className="text-xs">
                            {files.length} docs
                          </Badge>
                        </div>
                        <div className="space-y-2">
                          {files.map(({ file, path }, idx) => {
                            const status = fileStatuses[path] || { status: FILE_STATUS.PENDING };
                            return (
                              <div
                                key={idx}
                                className={`flex items-center justify-between p-2 rounded text-sm ${
                                  status.status === FILE_STATUS.SUCCESS
                                    ? "bg-green-50"
                                    : status.status === FILE_STATUS.ERROR
                                    ? "bg-red-50"
                                    : status.status === FILE_STATUS.PROCESSING
                                    ? "bg-blue-50"
                                    : "bg-gray-50"
                                }`}
                              >
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                  {getStatusIcon(status.status)}
                                  <span className="truncate">{file.name}</span>
                                </div>
                                <div className="flex items-center gap-2 ml-2">
                                  {status.status === FILE_STATUS.SUCCESS && status.fields?.length > 0 && (
                                    <Badge variant="outline" className="text-xs bg-green-100">
                                      {status.fields.length} campos
                                    </Badge>
                                  )}
                                  {status.message && (
                                    <span className={`text-xs ${
                                      status.status === FILE_STATUS.ERROR ? "text-red-600" : "text-muted-foreground"
                                    }`}>
                                      {status.message}
                                    </span>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          )}

          {/* Resumo final */}
          {summary && (
            <Card className={summary.success ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}>
              <CardHeader className="py-3">
                <CardTitle className="text-base flex items-center gap-2">
                  {summary.success ? (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-600" />
                  )}
                  Processamento Concluído
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="grid grid-cols-4 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold text-blue-600">{summary.total}</p>
                    <p className="text-xs text-muted-foreground">Total</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-green-600">{summary.processed}</p>
                    <p className="text-xs text-muted-foreground">Processados</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-purple-600">{summary.updated_clients}</p>
                    <p className="text-xs text-muted-foreground">Actualizados</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-red-600">{summary.errors_count || 0}</p>
                    <p className="text-xs text-muted-foreground">Erros</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Lista de clientes do sistema */}
          {!uploading && !summary && clientsList.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                Ver lista de clientes no sistema ({clientsList.length})
              </summary>
              <ScrollArea className="h-[150px] mt-2 border rounded p-2">
                <div className="space-y-1">
                  {clientsList.map((client) => (
                    <div key={client.id} className="text-xs flex items-center gap-2">
                      <Badge variant="outline" className="font-mono">
                        #{client.number || "—"}
                      </Badge>
                      <span>{client.name}</span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </details>
          )}
        </div>

        {/* Botões */}
        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="outline" onClick={() => setIsOpen(false)} disabled={uploading}>
            {uploading ? "A processar..." : "Fechar"}
          </Button>
          {!summary && (
            <Button
              onClick={handleUpload}
              disabled={selectedFiles.length === 0 || uploading}
              className="bg-purple-600 hover:bg-purple-700"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  A processar...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Analisar {selectedFiles.length} Documentos
                </>
              )}
            </Button>
          )}
          {summary && (
            <Button onClick={resetState} className="bg-blue-600 hover:bg-blue-700">
              <RefreshCw className="h-4 w-4 mr-2" />
              Nova Análise
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default BulkDocumentUpload;
