/**
 * BulkDocumentUpload - Upload massivo de documentos para análise com IA
 * Apenas disponível para administradores
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
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../contexts/AuthContext";

const API_URL = process.env.REACT_APP_BACKEND_URL || "";

const BulkDocumentUpload = () => {
  const { token, user } = useAuth();
  const folderInputRef = useRef(null);
  
  const [isOpen, setIsOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
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
    setResult(null);
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
      grouped[clientName].push(file);
    });
    return grouped;
  };

  // Fazer upload e análise
  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      toast.error("Selecione uma pasta com documentos");
      return;
    }

    setUploading(true);
    setProgress(0);
    setResult(null);

    try {
      const formData = new FormData();
      selectedFiles.forEach((file) => {
        // Usar o path relativo como nome para preservar a estrutura de pastas
        const path = file.webkitRelativePath || file.name;
        formData.append("files", file, path);
      });

      // Simular progresso (a API não retorna progresso real)
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 5, 90));
      }, 500);

      const response = await fetch(`${API_URL}/api/ai/bulk/analyze`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Erro ao processar documentos");
      }

      const data = await response.json();
      setResult(data);

      if (data.success) {
        toast.success(
          `Processados ${data.processed}/${data.total_files} documentos. ${data.updated_clients} clientes actualizados.`
        );
      } else {
        toast.warning("Alguns documentos não foram processados");
      }
    } catch (error) {
      toast.error(error.message);
      setResult({ success: false, errors: [error.message] });
    } finally {
      setUploading(false);
    }
  };

  const resetState = () => {
    setSelectedFiles([]);
    setResult(null);
    setProgress(0);
    if (folderInputRef.current) {
      folderInputRef.current.value = "";
    }
  };

  const filesByClient = getFilesByClient();
  const clientCount = Object.keys(filesByClient).length;

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
                O nome da pasta deve corresponder ao nome do cliente no sistema.
              </p>
            </CardContent>
          </Card>

          {/* Selecção de pasta */}
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

          {/* Ficheiros selecionados */}
          {selectedFiles.length > 0 && (
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Ficheiros Selecionados
                  </span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{selectedFiles.length} ficheiros</Badge>
                    <Badge variant="secondary">{clientCount} clientes</Badge>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <ScrollArea className="h-[200px]">
                  <div className="space-y-3">
                    {Object.entries(filesByClient).map(([clientName, files]) => (
                      <div key={clientName} className="border rounded-lg p-2">
                        <div className="flex items-center gap-2 mb-1">
                          <Users className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium text-sm">{clientName}</span>
                          <Badge variant="outline" className="text-xs">
                            {files.length} docs
                          </Badge>
                        </div>
                        <div className="pl-6 space-y-1">
                          {files.map((file, idx) => (
                            <div key={idx} className="text-xs text-muted-foreground flex items-center gap-1">
                              <FileText className="h-3 w-3" />
                              {file.name}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          )}

          {/* Progresso */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>A processar documentos com IA...</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
          )}

          {/* Resultado */}
          {result && (
            <Card className={result.success ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}>
              <CardHeader className="py-3">
                <CardTitle className="text-base flex items-center gap-2">
                  {result.success ? (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-600" />
                  )}
                  Resultado da Análise
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0 space-y-3">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold text-blue-600">{result.total_files}</p>
                    <p className="text-xs text-muted-foreground">Total ficheiros</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-green-600">{result.processed}</p>
                    <p className="text-xs text-muted-foreground">Processados</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-purple-600">{result.updated_clients}</p>
                    <p className="text-xs text-muted-foreground">Clientes actualizados</p>
                  </div>
                </div>

                {result.errors && result.errors.length > 0 && (
                  <div className="mt-3">
                    <p className="text-sm font-medium text-red-700 mb-1 flex items-center gap-1">
                      <AlertTriangle className="h-4 w-4" />
                      Erros ({result.errors.length})
                    </p>
                    <ScrollArea className="h-[100px]">
                      <div className="space-y-1">
                        {result.errors.map((error, idx) => (
                          <p key={idx} className="text-xs text-red-600 bg-red-100 p-1 rounded">
                            {error}
                          </p>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>
                )}

                {result.results && result.results.length > 0 && (
                  <div className="mt-3">
                    <p className="text-sm font-medium mb-1">Detalhes:</p>
                    <ScrollArea className="h-[150px]">
                      <div className="space-y-1">
                        {result.results.map((r, idx) => (
                          <div
                            key={idx}
                            className={`text-xs p-2 rounded flex items-center justify-between ${
                              r.success ? "bg-green-100" : "bg-red-100"
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              {r.success ? (
                                <CheckCircle className="h-3 w-3 text-green-600" />
                              ) : (
                                <XCircle className="h-3 w-3 text-red-600" />
                              )}
                              <span>{r.client_name}</span>
                              <span className="text-muted-foreground">/ {r.filename}</span>
                            </div>
                            {r.success && r.updated && (
                              <Badge variant="outline" className="text-xs bg-green-200">
                                Actualizado
                              </Badge>
                            )}
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Lista de clientes do sistema */}
          {!result && clientsList.length > 0 && (
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
          <Button variant="outline" onClick={() => setIsOpen(false)}>
            Fechar
          </Button>
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
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default BulkDocumentUpload;
