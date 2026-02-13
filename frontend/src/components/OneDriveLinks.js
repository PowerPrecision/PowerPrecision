import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./ui/dialog";
import { FolderOpen, Plus, Trash2, ExternalLink, Loader2, Link as LinkIcon, Search, Save } from "lucide-react";
import { toast } from "sonner";
import { getProcessOneDriveLinks, addProcessOneDriveLink, deleteProcessOneDriveLink } from "../services/api";

const API_URL = process.env.REACT_APP_BACKEND_URL || "";

const OneDriveLinks = ({ processId, clientName }) => {
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [mainFolderUrl, setMainFolderUrl] = useState(null);
  const [savedFolderUrl, setSavedFolderUrl] = useState(null);
  const [loadingFolder, setLoadingFolder] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    url: "",
    description: ""
  });

  useEffect(() => {
    fetchLinks();
    fetchFolderUrl();
  }, [processId]);

  const fetchLinks = async () => {
    try {
      const response = await getProcessOneDriveLinks(processId);
      setLinks(response.data);
    } catch (error) {
      console.error("Error fetching links:", error);
    } finally {
      setLoading(false);
    }
  };

  // Buscar URL da pasta do Drive
  const fetchFolderUrl = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_URL}/api/onedrive/process/${processId}/folder-url`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setMainFolderUrl(data.url);
        if (data.type === "saved") {
          setSavedFolderUrl(data.url);
        }
      }
    } catch (error) {
      console.error("Error fetching folder URL:", error);
    }
  };

  // Abrir pasta do cliente no Drive
  const handleOpenFolder = () => {
    if (savedFolderUrl) {
      window.open(savedFolderUrl, "_blank");
    } else if (mainFolderUrl) {
      window.open(mainFolderUrl, "_blank");
      toast.info(`Procure pela pasta "${clientName}" no Drive`, { duration: 5000 });
    } else {
      toast.error("Drive não configurado");
    }
  };

  // Guardar link da pasta específica do cliente
  const handleSaveFolderUrl = async () => {
    const url = prompt(
      "Cole aqui o link da pasta específica do cliente no Drive:\n\n(Ex: https://1drv.ms/f/... ou s3://bucket/path/...)",
      ""
    );
    if (!url) return;

    setLoadingFolder(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `${API_URL}/api/onedrive/process/${processId}/folder-url?folder_url=${encodeURIComponent(url)}`,
        {
          method: "PUT",
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      if (response.ok) {
        toast.success("Link da pasta guardado com sucesso!");
        setSavedFolderUrl(url);
      } else {
        const data = await response.json();
        toast.error(data.detail || "Erro ao guardar link");
      }
    } catch (error) {
      toast.error("Erro ao guardar link da pasta");
    } finally {
      setLoadingFolder(false);
    }
  };

  // Remover link da pasta
  const handleRemoveFolderUrl = async () => {
    if (!window.confirm("Tem a certeza que deseja remover o link da pasta?")) return;

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_URL}/api/onedrive/process/${processId}/folder-url`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        toast.success("Link removido");
        setSavedFolderUrl(null);
      }
    } catch (error) {
      toast.error("Erro ao remover link");
    }
  };

  const handleAddLink = async (e) => {
    e.preventDefault();
    if (!formData.name || !formData.url) {
      toast.error("Nome e URL são obrigatórios");
      return;
    }

    setSaving(true);
    try {
      await addProcessOneDriveLink(processId, formData);
      toast.success("Link adicionado com sucesso");
      setIsDialogOpen(false);
      setFormData({ name: "", url: "", description: "" });
      fetchLinks();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao adicionar link");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteLink = async (linkId) => {
    if (!window.confirm("Tem a certeza que deseja eliminar este link?")) return;

    try {
      await deleteProcessOneDriveLink(processId, linkId);
      toast.success("Link eliminado");
      fetchLinks();
    } catch (error) {
      toast.error("Erro ao eliminar link");
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Botão principal para abrir pasta do OneDrive */}
      {mainFolderUrl && (
        <div className="p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm flex items-center gap-2">
                <FolderOpen className="h-4 w-4 text-blue-600" />
                Pasta Drive: {clientName}
              </h4>
              <p className="text-xs text-muted-foreground mt-1">
                {savedFolderUrl ? "Link específico guardado" : "Pasta principal - pesquisar pelo nome do cliente"}
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <Button
                onClick={handleOpenFolder}
                size="sm"
                className="bg-blue-600 hover:bg-blue-700"
                data-testid="open-drive-btn"
              >
                <ExternalLink className="h-4 w-4 mr-1" />
                Abrir
              </Button>
              {savedFolderUrl ? (
                <Button
                  onClick={handleRemoveFolderUrl}
                  size="sm"
                  variant="outline"
                  className="text-red-600 border-red-200 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              ) : (
                <Button
                  onClick={handleSaveFolderUrl}
                  size="sm"
                  variant="outline"
                  disabled={loadingFolder}
                  title="Guardar link específico da pasta do cliente"
                >
                  {loadingFolder ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Links adicionais */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="font-medium text-sm">Links Adicionais</h4>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm" variant="outline">
                <Plus className="h-4 w-4 mr-1" />
                Adicionar
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Adicionar Link</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleAddLink} className="space-y-4">
                <div className="space-y-2">
                  <Label>Nome da Pasta *</Label>
                  <Input
                    placeholder="Ex: Documentos Pessoais"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Link de Partilha *</Label>
                  <Input
                    placeholder="https://... ou s3://bucket/path/..."
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    Cole o link de partilha do Drive, OneDrive, S3, Google Drive, etc.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Descrição (opcional)</Label>
                  <Input
                    placeholder="Ex: CC, NIF, comprovativo morada..."
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </div>
                <DialogFooter>
                  <Button type="submit" disabled={saving}>
                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Adicionar"}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {links.length === 0 ? (
          <div className="text-center py-6 text-muted-foreground border border-dashed rounded-lg">
            <LinkIcon className="h-8 w-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">Nenhum link adicional</p>
          </div>
        ) : (
          <ScrollArea className="max-h-[200px]">
            <div className="space-y-2">
              {links.map((link) => (
                <div
                  key={link.id}
                  className="flex items-center justify-between p-2 bg-muted/30 rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <LinkIcon className="h-4 w-4 text-blue-600 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="font-medium text-sm truncate">{link.name}</p>
                      {link.description && (
                        <p className="text-xs text-muted-foreground truncate">{link.description}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 ml-2 flex-shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => window.open(link.url, "_blank")}
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => handleDeleteLink(link.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </div>

      {/* Instruções - mais compactas */}
      {!mainFolderUrl && (
        <div className="p-3 bg-yellow-50 dark:bg-yellow-950/30 rounded-lg text-sm">
          <p className="font-medium text-yellow-800 dark:text-yellow-200">⚠️ OneDrive não configurado</p>
          <p className="text-xs text-muted-foreground mt-1">
            Configure o link de partilha nas definições do sistema.
          </p>
        </div>
      )}
    </div>
  );
};

export default OneDriveLinks;
