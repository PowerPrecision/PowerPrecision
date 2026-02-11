/**
 * S3FileManager - Gestor de Ficheiros AWS S3
 * Componente para listar, fazer upload e gerir ficheiros no S3
 */
import React, { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../contexts/AuthContext";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
import { Progress } from "./ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./ui/alert-dialog";
import { toast } from "sonner";
import {
  FileText,
  Upload,
  Loader2,
  Download,
  Trash2,
  FolderOpen,
  RefreshCw,
  User,
  Briefcase,
  Building2,
  CreditCard,
  MoreVertical,
  FileImage,
  FileSpreadsheet,
  File,
  CheckCircle,
  AlertCircle,
  Cloud,
} from "lucide-react";
import { format } from "date-fns";
import { pt } from "date-fns/locale";

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Categorias com ícones e cores
const CATEGORIES = [
  { id: "Documentos Pessoais", label: "Pessoais", icon: User, color: "blue" },
  { id: "Financeiros", label: "Financeiros", icon: Briefcase, color: "green" },
  { id: "Imóvel", label: "Imóvel", icon: Building2, color: "purple" },
  { id: "Bancários", label: "Bancários", icon: CreditCard, color: "orange" },
  { id: "Outros", label: "Outros", icon: FolderOpen, color: "gray" },
];

// Ícone baseado na extensão do ficheiro
const FileIcon = ({ filename }) => {
  const ext = filename?.split('.').pop()?.toLowerCase();
  
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) {
    return <FileImage className="h-4 w-4 text-pink-500" />;
  }
  if (['xls', 'xlsx', 'csv'].includes(ext)) {
    return <FileSpreadsheet className="h-4 w-4 text-green-500" />;
  }
  if (['pdf'].includes(ext)) {
    return <FileText className="h-4 w-4 text-red-500" />;
  }
  return <File className="h-4 w-4 text-gray-500" />;
};

const S3FileManager = ({ processId, clientName }) => {
  const { token } = useAuth();
  const [files, setFiles] = useState({});
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [activeTab, setActiveTab] = useState("Documentos Pessoais");
  const [deleteDialog, setDeleteDialog] = useState({ open: false, file: null });
  const [deleting, setDeleting] = useState(false);
  const fileInputRef = useRef(null);

  // Carregar ficheiros
  const fetchFiles = useCallback(async () => {
    if (!processId) return;
    
    try {
      const response = await fetch(
        `${API_URL}/api/documents/client/${processId}/files`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setFiles(data.files || {});
        setStats(data.stats || null);
      } else {
        const error = await response.json();
        if (error.detail !== "S3 não configurado") {
          toast.error(error.detail || "Erro ao carregar ficheiros");
        }
      }
    } catch (error) {
      console.error("Erro ao carregar ficheiros:", error);
    } finally {
      setLoading(false);
    }
  }, [processId, token]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  // Inicializar pastas
  const initializeFolders = async () => {
    try {
      const response = await fetch(
        `${API_URL}/api/documents/client/${processId}/init-folders`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        toast.success("Estrutura de pastas criada");
        fetchFiles();
      }
    } catch (error) {
      console.error("Erro ao criar pastas:", error);
    }
  };

  // Upload de ficheiro
  const handleUpload = async (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length === 0) return;

    setUploading(true);
    setUploadProgress(0);

    let successCount = 0;
    const totalFiles = selectedFiles.length;

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      const formData = new FormData();
      formData.append("file", file);
      formData.append("category", activeTab);

      try {
        const response = await fetch(
          `${API_URL}/api/documents/client/${processId}/upload`,
          {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
            body: formData,
          }
        );

        if (response.ok) {
          successCount++;
        } else {
          const error = await response.json();
          toast.error(`Erro no upload de ${file.name}: ${error.detail}`);
        }
      } catch (error) {
        toast.error(`Erro no upload de ${file.name}`);
      }

      setUploadProgress(((i + 1) / totalFiles) * 100);
    }

    if (successCount > 0) {
      toast.success(
        successCount === totalFiles
          ? `${successCount} ficheiro(s) enviado(s) com sucesso`
          : `${successCount}/${totalFiles} ficheiros enviados`
      );
      fetchFiles();
    }

    setUploading(false);
    setUploadProgress(0);
    
    // Limpar input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Download de ficheiro
  const handleDownload = async (file) => {
    try {
      const response = await fetch(
        `${API_URL}/api/documents/client/${processId}/download?file_path=${encodeURIComponent(file.path)}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        // Abrir URL num novo separador
        window.open(data.url, "_blank");
      } else {
        toast.error("Erro ao gerar link de download");
      }
    } catch (error) {
      toast.error("Erro ao fazer download");
    }
  };

  // Eliminar ficheiro
  const handleDelete = async () => {
    if (!deleteDialog.file) return;
    
    setDeleting(true);
    try {
      const response = await fetch(
        `${API_URL}/api/documents/client/${processId}/file?file_path=${encodeURIComponent(deleteDialog.file.path)}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        toast.success("Ficheiro eliminado");
        fetchFiles();
      } else {
        toast.error("Erro ao eliminar ficheiro");
      }
    } catch (error) {
      toast.error("Erro ao eliminar ficheiro");
    } finally {
      setDeleting(false);
      setDeleteDialog({ open: false, file: null });
    }
  };

  // Formatar data
  const formatDate = (dateStr) => {
    try {
      return format(new Date(dateStr), "d MMM yyyy, HH:mm", { locale: pt });
    } catch {
      return dateStr;
    }
  };

  // Contar ficheiros por categoria
  const getCategoryCount = (categoryId) => {
    return files[categoryId]?.length || 0;
  };

  if (loading) {
    return (
      <Card data-testid="s3-file-manager">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const currentFiles = files[activeTab] || [];

  return (
    <>
      <Card data-testid="s3-file-manager" className="h-full">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Cloud className="h-5 w-5 text-blue-500" />
                Documentos
              </CardTitle>
              <CardDescription>
                {stats ? (
                  <span>{stats.total_files} ficheiros ({stats.total_size_formatted})</span>
                ) : (
                  <span>Gestão de documentos do cliente</span>
                )}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={fetchFiles}
                disabled={loading}
                data-testid="refresh-files-btn"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              <Button
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                data-testid="upload-file-btn"
              >
                {uploading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Upload className="h-4 w-4 mr-2" />
                )}
                Upload
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleUpload}
                className="hidden"
                accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.webp"
              />
            </div>
          </div>

          {/* Barra de progresso do upload */}
          {uploading && (
            <div className="mt-3">
              <Progress value={uploadProgress} className="h-2" />
              <p className="text-xs text-muted-foreground mt-1">
                A enviar... {Math.round(uploadProgress)}%
              </p>
            </div>
          )}
        </CardHeader>

        <CardContent className="pt-0">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full flex flex-wrap h-auto gap-1 p-1">
              {CATEGORIES.map((cat) => {
                const Icon = cat.icon;
                const count = getCategoryCount(cat.id);
                return (
                  <TabsTrigger
                    key={cat.id}
                    value={cat.id}
                    className="flex-1 min-w-[80px] gap-1 text-xs py-1.5 px-2"
                    data-testid={`tab-${cat.id.toLowerCase().replace(/\s/g, '-')}`}
                  >
                    <Icon className="h-3 w-3" />
                    <span className="hidden sm:inline">{cat.label}</span>
                    {count > 0 && (
                      <Badge variant="secondary" className="ml-1 h-4 px-1 text-[10px]">
                        {count}
                      </Badge>
                    )}
                  </TabsTrigger>
                );
              })}
            </TabsList>

            {CATEGORIES.map((cat) => (
              <TabsContent key={cat.id} value={cat.id} className="mt-3">
                {currentFiles.length > 0 ? (
                  <ScrollArea className="h-[250px]">
                    <div className="space-y-2">
                      {currentFiles.map((file, idx) => (
                        <div
                          key={`${file.path}-${idx}`}
                          className="flex items-center justify-between p-2 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                          data-testid={`file-item-${idx}`}
                        >
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            <FileIcon filename={file.name} />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate" title={file.name}>
                                {file.name}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {file.size_formatted} • {formatDate(file.last_modified)}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => handleDownload(file)}
                              title="Download"
                              data-testid={`download-btn-${idx}`}
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-red-500 hover:text-red-600"
                              onClick={() => setDeleteDialog({ open: true, file })}
                              title="Eliminar"
                              data-testid={`delete-btn-${idx}`}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <FolderOpen className="h-10 w-10 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">Nenhum ficheiro em {cat.label}</p>
                    <p className="text-xs mt-1">
                      Clique em "Upload" para adicionar documentos
                    </p>
                  </div>
                )}
              </TabsContent>
            ))}
          </Tabs>

          {/* Botão para inicializar estrutura */}
          {stats?.total_files === 0 && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-blue-700">
                    Pasta do cliente vazia
                  </p>
                  <p className="text-xs text-blue-600 mt-1">
                    Clique para criar a estrutura de pastas e começar a fazer upload de documentos.
                  </p>
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-2"
                    onClick={initializeFolders}
                  >
                    <FolderOpen className="h-4 w-4 mr-2" />
                    Criar Estrutura de Pastas
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog de confirmação de eliminação */}
      <AlertDialog open={deleteDialog.open} onOpenChange={(open) => setDeleteDialog({ open, file: null })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar ficheiro?</AlertDialogTitle>
            <AlertDialogDescription>
              Tem a certeza que deseja eliminar "{deleteDialog.file?.name}"?
              Esta ação não pode ser revertida.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="bg-red-500 hover:bg-red-600"
            >
              {deleting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Trash2 className="h-4 w-4 mr-2" />
              )}
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default S3FileManager;
