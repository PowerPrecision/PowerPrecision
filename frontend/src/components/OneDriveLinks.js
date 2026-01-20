import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Badge } from "./ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./ui/dialog";
import { FolderOpen, Plus, Trash2, ExternalLink, Loader2, Link as LinkIcon } from "lucide-react";
import { toast } from "sonner";
import { getProcessOneDriveLinks, addProcessOneDriveLink, deleteProcessOneDriveLink } from "../services/api";

const OneDriveLinks = ({ processId, clientName }) => {
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    url: "",
    description: ""
  });

  useEffect(() => {
    fetchLinks();
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
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <FolderOpen className="h-5 w-5 text-blue-500" />
              Documentos OneDrive
            </CardTitle>
            <CardDescription>
              Links para pastas partilhadas de {clientName}
            </CardDescription>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="h-4 w-4 mr-1" />
                Adicionar Link
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Adicionar Link OneDrive</DialogTitle>
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
                  <Label>Link de Partilha OneDrive *</Label>
                  <Input
                    placeholder="https://1drv.ms/..."
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    Cole o link de partilha do OneDrive aqui
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
      </CardHeader>
      <CardContent>
        {links.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <FolderOpen className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p>Nenhum link adicionado</p>
            <p className="text-sm mt-1">Clique em "Adicionar Link" para associar pastas do OneDrive</p>
          </div>
        ) : (
          <div className="space-y-3">
            {links.map((link) => (
              <div
                key={link.id}
                className="flex items-center justify-between p-3 bg-muted/30 rounded-lg hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                    <LinkIcon className="h-4 w-4 text-blue-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium truncate">{link.name}</p>
                    {link.description && (
                      <p className="text-sm text-muted-foreground truncate">{link.description}</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      Adicionado por {link.added_by}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => window.open(link.url, "_blank")}
                  >
                    <ExternalLink className="h-4 w-4 mr-1" />
                    Abrir
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteLink(link.id)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Instructions */}
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
          <h4 className="font-medium text-sm mb-2">📁 Como adicionar links do OneDrive:</h4>
          <ol className="text-sm text-muted-foreground space-y-1">
            <li>1. Abra o OneDrive e navegue até à pasta do cliente</li>
            <li>2. Clique com o botão direito na pasta → "Partilhar"</li>
            <li>3. Configure as permissões (ver ou editar)</li>
            <li>4. Copie o link e cole aqui</li>
          </ol>
        </div>
      </CardContent>
    </Card>
  );
};

export default OneDriveLinks;
