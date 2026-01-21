import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { ScrollArea, ScrollBar } from "../components/ui/scroll-area";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Loader2, Search, Phone, Mail, User, Users, GripVertical, Eye, ChevronLeft, ChevronRight, AlertCircle, MapPin, Home, Euro, Calendar } from "lucide-react";
import { toast } from "sonner";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const statusColors = {
  yellow: "bg-yellow-100 border-yellow-300 dark:bg-yellow-900/30",
  blue: "bg-blue-100 border-blue-300 dark:bg-blue-900/30",
  purple: "bg-purple-100 border-purple-300 dark:bg-purple-900/30",
  orange: "bg-orange-100 border-orange-300 dark:bg-orange-900/30",
  green: "bg-green-100 border-green-300 dark:bg-green-900/30",
  red: "bg-red-100 border-red-300 dark:bg-red-900/30",
};

const statusHeaderColors = {
  yellow: "bg-yellow-500",
  blue: "bg-blue-500",
  purple: "bg-purple-500",
  orange: "bg-orange-500",
  green: "bg-green-500",
  red: "bg-red-500",
};

const KanbanBoard = ({ token }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [kanbanData, setKanbanData] = useState({ columns: [], total_processes: 0 });
  const [searchTerm, setSearchTerm] = useState("");
  const [draggingCard, setDraggingCard] = useState(null);
  const [dragOverColumn, setDragOverColumn] = useState(null);
  const [scrollPosition, setScrollPosition] = useState(0);

  const fetchKanbanData = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/processes/kanban`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("Failed to fetch kanban data");
      const data = await response.json();
      setKanbanData(data);
    } catch (error) {
      console.error("Error fetching kanban:", error);
      toast.error("Erro ao carregar dados do Kanban");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchKanbanData();
  }, [fetchKanbanData]);

  const handleDragStart = (e, process, columnName) => {
    setDraggingCard({ process, sourceColumn: columnName });
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e, columnName) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverColumn(columnName);
  };

  const handleDragLeave = () => {
    setDragOverColumn(null);
  };

  const handleDrop = async (e, targetColumn) => {
    e.preventDefault();
    setDragOverColumn(null);

    if (!draggingCard || draggingCard.sourceColumn === targetColumn) {
      setDraggingCard(null);
      return;
    }

    const { process, sourceColumn } = draggingCard;

    // Optimistic update
    setKanbanData((prev) => {
      const newColumns = prev.columns.map((col) => {
        if (col.name === sourceColumn) {
          return {
            ...col,
            processes: col.processes.filter((p) => p.id !== process.id),
            count: col.count - 1,
          };
        }
        if (col.name === targetColumn) {
          return {
            ...col,
            processes: [...col.processes, { ...process, status: targetColumn }],
            count: col.count + 1,
          };
        }
        return col;
      });
      return { ...prev, columns: newColumns };
    });

    setDraggingCard(null);

    // API call to move process
    try {
      const response = await fetch(
        `${API_URL}/api/processes/kanban/${process.id}/move?new_status=${targetColumn}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error("Failed to move process");
      }

      toast.success("Processo movido com sucesso");
    } catch (error) {
      console.error("Error moving process:", error);
      toast.error("Erro ao mover processo");
      // Revert on error
      fetchKanbanData();
    }
  };

  const filteredColumns = kanbanData.columns.map((column) => ({
    ...column,
    processes: column.processes.filter((process) =>
      process.client_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      process.client_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      process.consultor_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      process.mediador_name?.toLowerCase().includes(searchTerm.toLowerCase())
    ),
  }));

  const scrollContainer = (direction) => {
    const container = document.getElementById("kanban-scroll-container");
    if (container) {
      const scrollAmount = 350;
      const newPosition = direction === "left" 
        ? scrollPosition - scrollAmount 
        : scrollPosition + scrollAmount;
      container.scrollTo({ left: newPosition, behavior: "smooth" });
      setScrollPosition(newPosition);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="kanban-board">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold">Quadro Geral de Processos</h2>
          <p className="text-sm text-muted-foreground">
            {kanbanData.total_processes} processos • Arraste para mover entre fases ou clique para ver detalhes
          </p>
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Pesquisar cliente..."
              className="pl-10"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="flex gap-1">
            <Button variant="outline" size="icon" onClick={() => scrollContainer("left")}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={() => scrollContainer("right")}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="relative">
        <ScrollArea className="w-full whitespace-nowrap rounded-md">
          <div
            id="kanban-scroll-container"
            className="flex gap-4 pb-4 min-h-[70vh]"
            onScroll={(e) => setScrollPosition(e.currentTarget.scrollLeft)}
          >
            {filteredColumns.map((column) => (
              <div
                key={column.id}
                className={`flex-shrink-0 w-[320px] rounded-lg border-2 transition-all ${
                  dragOverColumn === column.name
                    ? "border-primary border-dashed bg-primary/5"
                    : "border-transparent"
                }`}
                onDragOver={(e) => handleDragOver(e, column.name)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, column.name)}
              >
                {/* Column Header */}
                <div className={`${statusHeaderColors[column.color] || "bg-gray-500"} rounded-t-lg px-4 py-3`}>
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-white text-sm truncate">
                      {column.label}
                    </h3>
                    <Badge variant="secondary" className="bg-white/20 text-white hover:bg-white/30">
                      {column.count}
                    </Badge>
                  </div>
                </div>

                {/* Column Content */}
                <div className={`${statusColors[column.color] || "bg-gray-100"} min-h-[60vh] rounded-b-lg p-2`}>
                  <ScrollArea className="h-[60vh]">
                    <div className="space-y-2 pr-2">
                      {column.processes.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground text-sm">
                          <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
                          <p>Nenhum processo</p>
                        </div>
                      ) : (
                        column.processes.map((process) => (
                          <Card
                            key={process.id}
                            className={`cursor-pointer hover:shadow-md transition-shadow ${
                              draggingCard?.process.id === process.id ? "opacity-50" : ""
                            }`}
                            draggable
                            onDragStart={(e) => handleDragStart(e, process, column.name)}
                            onClick={(e) => {
                              // Não navegar se estiver arrastando
                              if (!draggingCard) {
                                navigate(`/process/${process.id}`);
                              }
                            }}
                          >
                            <CardContent className="p-3">
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <GripVertical className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                    <p className="font-medium text-sm truncate">
                                      {process.client_name}
                                    </p>
                                  </div>
                                  
                                  {/* Labels */}
                                  {process.prioridade && (
                                    <Badge variant="destructive" className="mt-1 text-xs">
                                      <AlertCircle className="h-3 w-3 mr-1" />
                                      Prioridade
                                    </Badge>
                                  )}
                                  {process.idade_menos_35 && (
                                    <Badge variant="outline" className="mt-1 ml-1 text-xs bg-yellow-50">
                                      &lt;35 anos
                                    </Badge>
                                  )}
                                  
                                  {/* Contact Info */}
                                  {process.client_phone && (
                                    <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
                                      <Phone className="h-3 w-3" />
                                      <span className="truncate">{process.client_phone}</span>
                                    </div>
                                  )}
                                  
                                  {/* Value */}
                                  {process.valor_financiado && (
                                    <p className="text-xs text-emerald-600 font-medium mt-1">
                                      {process.valor_financiado}
                                    </p>
                                  )}
                                  
                                  {/* Assigned Staff */}
                                  <div className="flex flex-wrap gap-1 mt-2">
                                    {process.consultor_name && (
                                      <Badge variant="outline" className="text-xs bg-blue-50 border-blue-200">
                                        <User className="h-3 w-3 mr-1" />
                                        {process.consultor_name.split(' ')[0]}
                                      </Badge>
                                    )}
                                    {process.mediador_name && (
                                      <Badge variant="outline" className="text-xs bg-emerald-50 border-emerald-200">
                                        <User className="h-3 w-3 mr-1" />
                                        Int. {process.mediador_name.split(' ')[0]}
                                      </Badge>
                                    )}
                                  </div>
                                </div>
                                
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8 flex-shrink-0"
                                  onClick={() => navigate(`/process/${process.id}`)}
                                >
                                  <Eye className="h-4 w-4" />
                                </Button>
                              </div>
                            </CardContent>
                          </Card>
                        ))
                      )}
                    </div>
                  </ScrollArea>
                </div>
              </div>
            ))}
          </div>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
      </div>
    </div>
  );
};

export default KanbanBoard;
