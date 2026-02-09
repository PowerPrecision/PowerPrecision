/**
 * BulkDocumentUpload - Upload massivo de documentos para análise com IA
 * Apenas disponível para administradores
 * 
 * IMPORTANTE: Envia um ficheiro de cada vez (fila de espera) para evitar
 * que o browser feche os ficheiros antes de serem processados.
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
  const abortControllerRef = useRef(null);
  
  const [isOpen, setIsOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [fileStatuses, setFileStatuses] = useState({});
  const [summary, setSummary] = useState(null);
  const [clientsList, setClientsList] = useState([]);
  const [loadingClients, setLoadingClients] = useState(false);
  const [currentFile, setCurrentFile] = useState(null);

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

  // Agrupar ficheiros por cliente (apenas para visualização)
  // A pasta do cliente é a PRIMEIRA pasta após a pasta raiz selecionada
  // Subpastas dentro da pasta do cliente também pertencem ao mesmo cliente
  const getFilesByClient = () => {
    const grouped = {};
    selectedFiles.forEach((file) => {
      const path = file.webkitRelativePath || file.name;
      const parts = path.split("/");
      
      // parts[0] = pasta raiz selecionada
      // parts[1] = pasta do cliente
      // parts[2+] = subpastas ou ficheiro
      const clientName = parts.length >= 2 ? parts[1] : "Desconhecido";
      
      if (!grouped[clientName]) {
        grouped[clientName] = [];
      }
      grouped[clientName].push({ file, path });
    });
    return grouped;
  };

  // Actualizar estado de um ficheiro
  const updateFileStatus = (path, status, message = "", fields = []) => {
    setFileStatuses((prev) => ({
      ...prev,
      [path]: { status, message, fields },
    }));
  };

  // Processar um único ficheiro
  const processOneFile = async (file) => {
    const path = file.webkitRelativePath || file.name;
    
    // Extrair nome do cliente do path
    // Estrutura: PastaRaiz/NomeCliente/[subpastas/]ficheiro.pdf
    // O cliente é sempre a SEGUNDA pasta (índice 1)
    const parts = path.replace("\\", "/").split("/");
    let clientName, docFilename;
    
    if (parts.length >= 2) {
      // parts[0] = pasta raiz, parts[1] = cliente, parts[last] = ficheiro
      clientName = parts[1];
      docFilename = parts[parts.length - 1];
    } else {
      docFilename = parts[0];
      clientName = docFilename.includes("_") 
        ? docFilename.split("_")[0] 
        : "Desconhecido";
    }

    setCurrentFile({ name: docFilename, client: clientName });
    updateFileStatus(path, FILE_STATUS.PROCESSING, "A enviar...");

    try {
      // Criar cópia do ficheiro para evitar problemas com postMessage
      const fileBlob = new Blob([await file.arrayBuffer()], { type: file.type });
      const formData = new FormData();
      formData.append("file", fileBlob, path);

      const response = await fetch(`${API_URL}/api/ai/bulk/analyze-single`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
        signal: abortControllerRef.current?.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Erro ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        updateFileStatus(
          path,
          FILE_STATUS.SUCCESS,
          result.updated ? "Ficha actualizada" : "Analisado",
          result.fields_extracted || []
        );
        return { success: true, updated: result.updated };
      } else {
        updateFileStatus(path, FILE_STATUS.ERROR, result.error || "Erro na análise");
        return { success: false, error: result.error };
      }
    } catch (error) {
      if (error.name === "AbortError") {
        updateFileStatus(path, FILE_STATUS.ERROR, "Cancelado");
        return { success: false, error: "Cancelado" };
      }
      // Ignorar erros de postMessage - ficheiro já foi processado
      if (error.message && error.message.includes("postMessage")) {
        console.warn("Aviso postMessage ignorado:", error);
        return { success: true, updated: false };
      }
      updateFileStatus(path, FILE_STATUS.ERROR, error.message);
      return { success: false, error: error.message };
    }
  };

  // Verificar se um cliente existe
  const checkClientExists = async (clientName) => {
    try {
      const response = await fetch(
        `${API_URL}/api/ai/bulk/check-client?name=${encodeURIComponent(clientName)}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          signal: abortControllerRef.current?.signal,
        }
      );
      if (response.ok) {
        const data = await response.json();
        return data.exists;
      }
      return false;
    } catch (error) {
      return false;
    }
  };

  // Processar ficheiros um a um (fila de espera)
  // Verifica primeiro se o cliente existe antes de processar os seus ficheiros
  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      toast.error("Selecione uma pasta com documentos");
      return;
    }

    setUploading(true);
    setSummary(null);
    abortControllerRef.current = new AbortController();

    // Inicializar todos como pendentes
    const initialStatuses = {};
    selectedFiles.forEach((file) => {
      const path = file.webkitRelativePath || file.name;
      initialStatuses[path] = { status: FILE_STATUS.PENDING, message: "Na fila..." };
    });
    setFileStatuses(initialStatuses);

    let processed = 0;
    let updatedClients = 0;
    let errors = 0;
    let skippedClients = 0;

    // Agrupar ficheiros por cliente
    const filesByClient = getFilesByClient();
    const clientNames = Object.keys(filesByClient);

    toast.info(`A processar ${selectedFiles.length} ficheiros de ${clientNames.length} clientes...`);

    // Processar cliente a cliente
    for (const clientName of clientNames) {
      // Verificar se foi cancelado
      if (abortControllerRef.current?.signal.aborted) {
        break;
      }

      const clientFiles = filesByClient[clientName];
      
      // Verificar se o cliente existe ANTES de processar os ficheiros
      setCurrentFile({ name: "A verificar...", client: clientName });
      const clientExists = await checkClientExists(clientName);

      if (!clientExists) {
        // Cliente não existe - marcar todos os ficheiros como erro e passar ao próximo
        skippedClients++;
        for (const { path } of clientFiles) {
          updateFileStatus(path, FILE_STATUS.ERROR, `Cliente "${clientName}" não encontrado`);
          errors++;
        }
        console.warn(`Cliente não encontrado: ${clientName} - ${clientFiles.length} ficheiros ignorados`);
        continue;
      }

      // Cliente existe - processar os ficheiros
      for (const { file, path } of clientFiles) {
        // Verificar se foi cancelado
        if (abortControllerRef.current?.signal.aborted) {
          break;
        }

        const result = await processOneFile(file);

        if (result.success) {
          processed++;
          if (result.updated) {
            updatedClients++;
          }
        } else {
          errors++;
        }

        // Pequena pausa entre ficheiros
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
    }

    setCurrentFile(null);
    setUploading(false);

    // Resumo final
    setSummary({
      success: processed > 0,
      total: selectedFiles.length,
      processed,
      updated_clients: updatedClients,
      errors_count: errors,
      skipped_clients: skippedClients,
    });

    if (processed > 0) {
      let msg = `Concluído! ${processed}/${selectedFiles.length} processados, ${updatedClients} fichas actualizadas.`;
      if (skippedClients > 0) {
        msg += ` (${skippedClients} clientes não encontrados)`;
      }
      toast.success(msg);
    } else if (skippedClients > 0) {
      toast.error(`Nenhum documento processado. ${skippedClients} clientes não encontrados.`);
    } else {
      toast.error("Nenhum documento foi processado com sucesso.");
    }
  };

  // Cancelar processamento
  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      toast.info("A cancelar...");
    }
  };

  const resetState = () => {
    setSelectedFiles([]);
    setSummary(null);
    setFileStatuses({});
    setCurrentFile(null);
    if (folderInputRef.current) {
      folderInputRef.current.value = "";
    }
  };

  const filesByClient = getFilesByClient();
  const clientCount = Object.keys(filesByClient).length;

  // Calcular progresso
  const totalFiles = selectedFiles.length;
  const completedFiles = Object.values(fileStatuses).filter(
    (s) => s.status === FILE_STATUS.SUCCESS || s.status === FILE_STATUS.ERROR
  ).length;
  const progressPercent = totalFiles > 0 ? Math.round((completedFiles / totalFiles) * 100) : 0;

  // Ícone de estado
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
            Selecione uma pasta com subpastas de clientes. Os ficheiros são processados um a um.
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
│   ├── Recibo.pdf
│   └── Documentos/        ← subpastas OK
│       ├── NIF.pdf
│       └── Morada.pdf
├── Maria Santos/
│   └── IRS.pdf
└── ...`}
                </pre>
                <p className="text-xs text-blue-600 mt-2">
                  O nome da <strong>primeira pasta</strong> é o nome do cliente. Subpastas são suportadas.
                </p>
              </CardContent>
            </Card>
          )}

          {/* Selecção de pasta */}
          {!uploading && (
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
              >
                <FolderUp className="h-4 w-4 mr-2" />
                Selecionar Pasta
              </Button>
              {selectedFiles.length > 0 && !uploading && (
                <Button variant="ghost" size="icon" onClick={resetState}>
                  <RefreshCw className="h-4 w-4" />
                </Button>
              )}
            </div>
          )}

          {/* Progresso geral */}
          {uploading && (
            <div className="space-y-2 p-4 bg-purple-50 rounded-lg">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {currentFile ? `A processar: ${currentFile.client}/${currentFile.name}` : "A processar..."}
                </span>
                <span>{completedFiles}/{totalFiles} ({progressPercent}%)</span>
              </div>
              <Progress value={progressPercent} className="h-3" />
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleCancel}
                className="mt-2"
              >
                Cancelar
              </Button>
            </div>
          )}

          {/* Lista de ficheiros */}
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
                <ScrollArea className="h-[280px]">
                  <div className="space-y-3 pr-4">
                    {Object.entries(filesByClient).map(([clientName, files]) => (
                      <div key={clientName} className="border rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <Users className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <span className="font-medium text-sm truncate" title={clientName}>{clientName}</span>
                          <Badge variant="outline" className="text-xs flex-shrink-0">
                            {files.length} docs
                          </Badge>
                        </div>
                        <div className="space-y-1">
                          {files.map(({ file, path }, idx) => {
                            const status = fileStatuses[path] || { status: FILE_STATUS.PENDING };
                            return (
                              <div
                                key={idx}
                                className={`flex items-start gap-2 p-2 rounded text-sm ${
                                  status.status === FILE_STATUS.SUCCESS
                                    ? "bg-green-50"
                                    : status.status === FILE_STATUS.ERROR
                                    ? "bg-red-50"
                                    : status.status === FILE_STATUS.PROCESSING
                                    ? "bg-blue-50 animate-pulse"
                                    : "bg-gray-50"
                                }`}
                              >
                                <div className="flex-shrink-0 mt-0.5">
                                  {getStatusIcon(status.status)}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-xs font-medium truncate max-w-[200px]" title={file.name}>
                                      {file.name}
                                    </span>
                                    {status.fields?.length > 0 && (
                                      <Badge variant="outline" className="text-xs bg-green-100 flex-shrink-0">
                                        {status.fields.length} campos
                                      </Badge>
                                    )}
                                  </div>
                                  {status.message && (
                                    <p className={`text-xs mt-1 break-words ${
                                      status.status === FILE_STATUS.ERROR ? "text-red-600" : "text-muted-foreground"
                                    }`}>
                                      {status.message}
                                    </p>
                                  )}
                                  {status.fields?.length > 0 && (
                                    <p className="text-xs text-green-600 mt-1 break-words">
                                      Campos: {status.fields.join(", ")}
                                    </p>
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
                    <p className="text-2xl font-bold text-red-600">{summary.errors_count}</p>
                    <p className="text-xs text-muted-foreground">Erros</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Lista de clientes */}
          {!uploading && !summary && clientsList.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                Ver lista de clientes no sistema ({clientsList.length})
              </summary>
              <ScrollArea className="h-[120px] mt-2 border rounded p-2">
                <div className="space-y-1">
                  {clientsList.map((client) => (
                    <div key={client.id} className="text-xs flex items-center gap-2">
                      <Badge variant="outline" className="font-mono">#{client.number || "—"}</Badge>
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
          {!summary && !uploading && (
            <Button
              onClick={handleUpload}
              disabled={selectedFiles.length === 0}
              className="bg-purple-600 hover:bg-purple-700"
            >
              <Sparkles className="h-4 w-4 mr-2" />
              Analisar {selectedFiles.length} Documentos
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
