/**
 * LeadsKanban - Gestão de Leads de Imóveis
 * Quadro Kanban para gerir leads/visitas de imóveis
 */
import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Badge } from "./ui/badge";
import { Card, CardContent } from "./ui/card";
import { ScrollArea } from "./ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { toast } from "sonner";
import {
  Plus,
  Link as LinkIcon,
  Loader2,
  MapPin,
  Euro,
  Home,
  Phone,
  User,
  ExternalLink,
  Trash2,
  Edit,
  GripVertical,
  Search,
  Building,
  Maximize2,
  Users,
  Sparkles,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Estados do Kanban
const LEAD_STATUSES = [
  { id: "novo", label: "Novo", color: "bg-blue-500" },
  { id: "contactado", label: "Contactado", color: "bg-yellow-500" },
  { id: "visita_agendada", label: "Visita Agendada", color: "bg-purple-500" },
  { id: "proposta", label: "Proposta", color: "bg-orange-500" },
  { id: "reservado", label: "Reservado", color: "bg-green-500" },
  { id: "descartado", label: "Descartado", color: "bg-gray-500" },
];

// Componente de cartão de lead
const LeadCard = ({ lead, onEdit, onStatusChange, onDelete, onRefreshPrice, onShowSuggestions, clients }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleDragStart = (e) => {
    setIsDragging(true);
    e.dataTransfer.setData("leadId", lead.id);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  const formatPrice = (price) => {
    if (!price) return "N/D";
    return new Intl.NumberFormat("pt-PT", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    }).format(price);
  };

  const handleRefreshPrice = async () => {
    setIsRefreshing(true);
    try {
      await onRefreshPrice(lead.id);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Formatar data relativa
  const formatRelativeDate = (dateStr) => {
    if (!dateStr) return null;
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
      if (diffDays === 0) return "Hoje";
      if (diffDays === 1) return "Há 1 dia";
      return `Há ${diffDays} dias`;
    } catch {
      return null;
    }
  };

  const isStale = lead.is_stale || (lead.days_old > 7 && lead.status === "novo");
  const daysOldText = formatRelativeDate(lead.created_at);

  return (
    <Card
      draggable
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      className={`cursor-grab active:cursor-grabbing transition-all ${
        isDragging ? "opacity-50 rotate-2 scale-105" : "hover:shadow-md"
      } ${isStale ? "border-red-400 border-2" : ""}`}
      data-testid={`lead-card-${lead.id}`}
    >
      <CardContent className="p-2 space-y-1">
        {/* Header: Título + Ações */}
        <div className="flex items-start justify-between gap-1">
          <h4 className="text-xs font-medium line-clamp-1 flex-1" title={lead.title}>
            {lead.title || "Sem título"}
          </h4>
          <div className="flex gap-0.5 flex-shrink-0">
            <Button variant="ghost" size="icon" className="h-5 w-5" onClick={() => onEdit(lead)} title="Editar">
              <Edit className="h-2.5 w-2.5" />
            </Button>
            <Button variant="ghost" size="icon" className="h-5 w-5 text-red-500" onClick={() => onDelete(lead.id)} title="Eliminar">
              <Trash2 className="h-2.5 w-2.5" />
            </Button>
          </div>
        </div>

        {/* Preço + Localização */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-green-600 font-semibold">{formatPrice(lead.price)}</span>
          {lead.location && (
            <span className="text-muted-foreground truncate max-w-[80px]" title={lead.location}>
              {lead.location}
            </span>
          )}
        </div>

        {/* Badges: Tipologia + Área + Data */}
        <div className="flex flex-wrap gap-1 items-center">
          {lead.typology && <Badge variant="secondary" className="text-[10px] px-1 py-0">{lead.typology}</Badge>}
          {lead.area && <Badge variant="outline" className="text-[10px] px-1 py-0">{lead.area}m²</Badge>}
          {daysOldText && (
            <span className={`text-[10px] ${isStale ? "text-red-600 font-medium" : "text-muted-foreground"}`}>
              {isStale && "⚠️"}{daysOldText}
            </span>
          )}
          <Button variant="ghost" size="icon" className="h-4 w-4 ml-auto" onClick={handleRefreshPrice} disabled={isRefreshing} title="Verificar preço">
            {isRefreshing ? <Loader2 className="h-2.5 w-2.5 animate-spin" /> : <span className="text-[10px]">🔄</span>}
          </Button>
        </div>

        {/* Cliente + Link */}
        <div className="flex items-center justify-between text-[10px]">
          {lead.client_name ? (
            <span className="text-blue-600 truncate max-w-[100px]">{lead.client_name}</span>
          ) : <span />}
          <a href={lead.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline flex items-center gap-0.5">
            <ExternalLink className="h-2.5 w-2.5" />Ver
          </a>
        </div>
      </CardContent>
    </Card>
  );
};

// Componente de coluna do Kanban
const KanbanColumn = ({ status, leads, onDrop, onEdit, onStatusChange, onDelete, onRefreshPrice, clients }) => {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const leadId = e.dataTransfer.getData("leadId");
    if (leadId) {
      onDrop(leadId, status.id);
    }
  };

  return (
    <div
      className={`flex-shrink-0 w-56 bg-gray-50 rounded-lg p-2 transition-colors ${
        isDragOver ? "bg-blue-50 ring-2 ring-blue-300" : ""
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      data-testid={`kanban-column-${status.id}`}
    >
      {/* Header da coluna */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${status.color}`} />
          <h3 className="font-medium text-sm">{status.label}</h3>
        </div>
        <Badge variant="secondary" className="text-xs">
          {leads.length}
        </Badge>
      </div>

      {/* Cartões */}
      <ScrollArea className="h-[calc(100vh-280px)]">
        <div className="space-y-2 pr-2">
          {leads.map((lead) => (
            <LeadCard
              key={lead.id}
              lead={lead}
              onEdit={onEdit}
              onStatusChange={onStatusChange}
              onDelete={onDelete}
              onRefreshPrice={onRefreshPrice}
              clients={clients}
            />
          ))}
          {leads.length === 0 && (
            <div className="text-center text-sm text-muted-foreground py-8">
              Sem leads
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};

// Componente principal
const LeadsKanban = () => {
  const { token, user } = useAuth();
  const [leads, setLeads] = useState({});
  const [clients, setClients] = useState([]);
  const [consultores, setConsultores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingLead, setEditingLead] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Filtros
  const [filterConsultor, setFilterConsultor] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  
  // Clientes Sugeridos
  const [suggestedClientsDialog, setSuggestedClientsDialog] = useState(false);
  const [suggestedClients, setSuggestedClients] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [selectedLeadForSuggestions, setSelectedLeadForSuggestions] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    url: "",
    title: "",
    price: "",
    location: "",
    typology: "",
    area: "",
    photo_url: "",
    client_id: "",
    notes: "",
    consultant: {
      name: "",
      phone: "",
      email: "",
      agency_name: "",
    },
  });

  // Carregar leads
  const fetchLeads = useCallback(async () => {
    try {
      let url = `${API_URL}/api/leads/by-status`;
      const params = new URLSearchParams();
      
      if (filterConsultor && filterConsultor !== "all") {
        params.append("consultor_id", filterConsultor);
      }
      if (filterStatus && filterStatus !== "all") {
        params.append("status_filter", filterStatus);
      }
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setLeads(data);
      }
    } catch (error) {
      console.error("Erro ao carregar leads:", error);
      toast.error("Erro ao carregar leads");
    } finally {
      setLoading(false);
    }
  }, [token, filterConsultor, filterStatus]);

  // Carregar clientes para associação
  const fetchClients = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/processes`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setClients(data);
      }
    } catch (error) {
      console.error("Erro ao carregar clientes:", error);
    }
  }, [token]);

  // Carregar consultores para o filtro
  const fetchConsultores = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/leads/consultores`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setConsultores(data);
      }
    } catch (error) {
      console.error("Erro ao carregar consultores:", error);
    }
  }, [token]);

  useEffect(() => {
    fetchLeads();
    fetchClients();
    fetchConsultores();
  }, [fetchLeads, fetchClients, fetchConsultores]);

  // Refresh preço de um lead
  const handleRefreshPrice = async (leadId) => {
    try {
      const response = await fetch(`${API_URL}/api/leads/${leadId}/refresh`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.price_changed) {
          toast.success(`Preço actualizado: ${result.old_price}€ → ${result.new_price}€`);
        } else {
          toast.info("Preço sem alteração");
        }
        fetchLeads();
      } else {
        const error = await response.json();
        toast.error(error.message || "Erro ao verificar preço");
      }
    } catch (error) {
      console.error("Erro ao verificar preço:", error);
      toast.error("Erro ao verificar preço");
    }
  };

  // Buscar clientes sugeridos para um lead
  const handleShowSuggestedClients = async (lead) => {
    setSelectedLeadForSuggestions(lead);
    setLoadingSuggestions(true);
    setSuggestedClientsDialog(true);
    setSuggestedClients([]);
    
    try {
      const response = await fetch(`${API_URL}/api/match/lead/${lead.id}/clients`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setSuggestedClients(data.matches || []);
        if (data.matches?.length === 0) {
          toast.info("Nenhum cliente compatível encontrado");
        }
      } else {
        toast.error("Erro ao buscar clientes sugeridos");
      }
    } catch (error) {
      console.error("Erro ao buscar clientes sugeridos:", error);
      toast.error("Erro ao buscar clientes sugeridos");
    } finally {
      setLoadingSuggestions(false);
    }
  };

  // Extrair dados do URL
  const handleExtractUrl = async () => {
    if (!formData.url) {
      toast.error("Insira um URL");
      return;
    }

    setExtracting(true);
    try {
      const response = await fetch(
        `${API_URL}/api/leads/extract-url?url=${encodeURIComponent(formData.url)}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );


      if (response.ok) {
        const result = await response.json();
        const data = result.data;

        setFormData((prev) => ({
          ...prev,
          title: data.title || prev.title,
          price: data.price || prev.price,
          location: data.location || prev.location,
          typology: data.typology || prev.typology,
          area: data.area || prev.area,
          photo_url: data.photo_url || prev.photo_url,
          consultant: {
            ...prev.consultant,
            name: data.consultant?.name || prev.consultant.name,
            phone: data.consultant?.phone || prev.consultant.phone,
            email: data.consultant?.email || prev.consultant.email,
            agency_name: data.consultant?.agency_name || prev.consultant.agency_name,
          },
        }));

        toast.success(`Dados extraídos de ${result.data.source}`);
      } else {
        toast.warning("Não foi possível extrair dados. Preencha manualmente.");
      }
    } catch (error) {
      console.error("Erro ao extrair:", error);
      toast.warning("Não foi possível extrair dados. Preencha manualmente.");
    } finally {
      setExtracting(false);
    }
  };

  // Guardar lead
  const handleSave = async () => {
    if (!formData.url) {
      toast.error("URL é obrigatório");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        ...formData,
        price: formData.price ? parseFloat(formData.price) : null,
        area: formData.area ? parseFloat(formData.area) : null,
        consultant: formData.consultant.name ? formData.consultant : null,
        // Handle "none" value for client_id
        client_id: formData.client_id === "none" ? "" : formData.client_id,
      };

      const url = editingLead
        ? `${API_URL}/api/leads/${editingLead.id}`
        : `${API_URL}/api/leads`;

      const response = await fetch(url, {
        method: editingLead ? "PATCH" : "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        toast.success(editingLead ? "Lead actualizado" : "Lead criado");
        setIsDialogOpen(false);
        resetForm();
        fetchLeads();
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao guardar lead");
      }
    } catch (error) {
      console.error("Erro ao guardar:", error);
      toast.error("Erro ao guardar lead");
    } finally {
      setSaving(false);
    }
  };

  // Mudar status (drag & drop)
  const handleStatusChange = async (leadId, newStatus) => {
    try {
      const response = await fetch(
        `${API_URL}/api/leads/${leadId}/status?status=${newStatus}`,
        {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        fetchLeads();
      }
    } catch (error) {
      console.error("Erro ao mudar status:", error);
      toast.error("Erro ao mudar status");
    }
  };

  // Eliminar lead
  const handleDelete = async (leadId) => {
    if (!window.confirm("Tem a certeza que deseja eliminar este lead?")) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/leads/${leadId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        toast.success("Lead eliminado");
        fetchLeads();
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao eliminar");
      }
    } catch (error) {
      console.error("Erro ao eliminar:", error);
      toast.error("Erro ao eliminar lead");
    }
  };

  // Editar lead
  const handleEdit = (lead) => {
    setEditingLead(lead);
    setFormData({
      url: lead.url || "",
      title: lead.title || "",
      price: lead.price || "",
      location: lead.location || "",
      typology: lead.typology || "",
      area: lead.area || "",
      photo_url: lead.photo_url || "",
      client_id: lead.client_id || "",
      notes: lead.notes || "",
      consultant: {
        name: lead.consultant?.name || "",
        phone: lead.consultant?.phone || "",
        email: lead.consultant?.email || "",
        agency_name: lead.consultant?.agency_name || "",
      },
    });
    setIsDialogOpen(true);
  };

  // Reset form
  const resetForm = () => {
    setEditingLead(null);
    setFormData({
      url: "",
      title: "",
      price: "",
      location: "",
      typology: "",
      area: "",
      photo_url: "",
      client_id: "",
      notes: "",
      consultant: {
        name: "",
        phone: "",
        email: "",
        agency_name: "",
      },
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-full" data-testid="leads-kanban">
      {/* Header */}
      <div className="flex flex-col gap-4 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Building className="h-5 w-5" />
              Gestão de Leads / Visitas
            </h2>
            <p className="text-sm text-muted-foreground">
              Arraste os cartões entre colunas para alterar o estado
            </p>
          </div>
          <Button
            onClick={() => {
              resetForm();
              setIsDialogOpen(true);
            }}
            data-testid="add-lead-btn"
          >
            <Plus className="h-4 w-4 mr-2" />
            Novo Lead
          </Button>
        </div>

        {/* Filtros */}
        <div className="flex flex-wrap gap-4 items-center p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2">
            <Label className="text-sm whitespace-nowrap">Filtrar por Consultor:</Label>
            <Select value={filterConsultor} onValueChange={setFilterConsultor}>
              <SelectTrigger className="w-[200px]" data-testid="filter-consultor">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {consultores.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name || c.email}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <Label className="text-sm whitespace-nowrap">Filtrar por Estado:</Label>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[180px]" data-testid="filter-status">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {LEAD_STATUSES.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {(filterConsultor !== "all" || filterStatus !== "all") && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setFilterConsultor("all");
                setFilterStatus("all");
              }}
            >
              Limpar filtros
            </Button>
          )}
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {LEAD_STATUSES.map((status) => (
          <KanbanColumn
            key={status.id}
            status={status}
            leads={leads[status.id] || []}
            onDrop={handleStatusChange}
            onEdit={handleEdit}
            onStatusChange={handleStatusChange}
            onDelete={handleDelete}
            onRefreshPrice={handleRefreshPrice}
            clients={clients}
          />
        ))}
      </div>

      {/* Dialog para criar/editar lead */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingLead ? "Editar Lead" : "Novo Lead de Imóvel"}
            </DialogTitle>
            <DialogDescription>
              Cole o URL do anúncio para extrair dados automaticamente ou
              preencha manualmente
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* URL + Extracção */}
            <div className="space-y-2">
              <Label>URL do Anúncio *</Label>
              <div className="flex gap-2">
                <Input
                  value={formData.url}
                  onChange={(e) =>
                    setFormData({ ...formData, url: e.target.value })
                  }
                  placeholder="https://www.idealista.pt/imovel/..."
                  data-testid="lead-url-input"
                />
                <Button
                  variant="outline"
                  onClick={handleExtractUrl}
                  disabled={extracting || !formData.url}
                  data-testid="extract-url-btn"
                >
                  {extracting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Dados do imóvel */}
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2 space-y-2">
                <Label>Título</Label>
                <Input
                  value={formData.title}
                  onChange={(e) =>
                    setFormData({ ...formData, title: e.target.value })
                  }
                  placeholder="Ex: T2 em Lisboa com terraço"
                  data-testid="lead-title-input"
                />
              </div>

              <div className="space-y-2">
                <Label>Preço (€)</Label>
                <Input
                  type="number"
                  value={formData.price}
                  onChange={(e) =>
                    setFormData({ ...formData, price: e.target.value })
                  }
                  placeholder="250000"
                  data-testid="lead-price-input"
                />
              </div>

              <div className="space-y-2">
                <Label>Área (m²)</Label>
                <Input
                  type="number"
                  value={formData.area}
                  onChange={(e) =>
                    setFormData({ ...formData, area: e.target.value })
                  }
                  placeholder="85"
                  data-testid="lead-area-input"
                />
              </div>

              <div className="space-y-2">
                <Label>Localização</Label>
                <Input
                  value={formData.location}
                  onChange={(e) =>
                    setFormData({ ...formData, location: e.target.value })
                  }
                  placeholder="Lisboa, Benfica"
                  data-testid="lead-location-input"
                />
              </div>

              <div className="space-y-2">
                <Label>Tipologia</Label>
                <Select
                  value={formData.typology}
                  onValueChange={(value) =>
                    setFormData({ ...formData, typology: value })
                  }
                >
                  <SelectTrigger data-testid="lead-typology-select">
                    <SelectValue placeholder="Seleccione" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="T0">T0</SelectItem>
                    <SelectItem value="T1">T1</SelectItem>
                    <SelectItem value="T2">T2</SelectItem>
                    <SelectItem value="T3">T3</SelectItem>
                    <SelectItem value="T4">T4</SelectItem>
                    <SelectItem value="T5+">T5+</SelectItem>
                    <SelectItem value="Moradia">Moradia</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="col-span-2 space-y-2">
                <Label>URL da Foto</Label>
                <Input
                  value={formData.photo_url}
                  onChange={(e) =>
                    setFormData({ ...formData, photo_url: e.target.value })
                  }
                  placeholder="https://..."
                  data-testid="lead-photo-input"
                />
              </div>
            </div>

            {/* Dados do consultor */}
            <div className="border-t pt-4">
              <h4 className="font-medium mb-3">Contacto do Comercial</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Nome</Label>
                  <Input
                    value={formData.consultant.name}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        consultant: { ...formData.consultant, name: e.target.value },
                      })
                    }
                    placeholder="Nome do comercial"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Telefone</Label>
                  <Input
                    value={formData.consultant.phone}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        consultant: { ...formData.consultant, phone: e.target.value },
                      })
                    }
                    placeholder="+351 912 345 678"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input
                    value={formData.consultant.email}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        consultant: { ...formData.consultant, email: e.target.value },
                      })
                    }
                    placeholder="email@imobiliaria.pt"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Imobiliária</Label>
                  <Input
                    value={formData.consultant.agency_name}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        consultant: { ...formData.consultant, agency_name: e.target.value },
                      })
                    }
                    placeholder="Nome da imobiliária"
                  />
                </div>
              </div>
            </div>

            {/* Cliente associado */}
            <div className="border-t pt-4">
              <div className="space-y-2">
                <Label>Associar a Cliente</Label>
                <Select
                  value={formData.client_id}
                  onValueChange={(value) =>
                    setFormData({ ...formData, client_id: value })
                  }
                >
                  <SelectTrigger data-testid="lead-client-select">
                    <SelectValue placeholder="Seleccione um cliente (opcional)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Nenhum</SelectItem>
                    {clients.map((client) => (
                      <SelectItem key={client.id} value={client.id}>
                        {client.client_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Notas */}
            <div className="space-y-2">
              <Label>Notas</Label>
              <Textarea
                value={formData.notes}
                onChange={(e) =>
                  setFormData({ ...formData, notes: e.target.value })
                }
                placeholder="Notas adicionais..."
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              {editingLead ? "Guardar" : "Criar Lead"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default LeadsKanban;
