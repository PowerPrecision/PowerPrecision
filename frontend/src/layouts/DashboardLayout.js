import React, { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "../components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import {
  LayoutDashboard,
  FileText,
  Users,
  Calendar,
  Settings,
  LogOut,
  Menu,
  X,
  User,
  Building2,
  CreditCard,
  PlusCircle,
  BarChart3,
  Cog,
  Home,
  LayoutGrid,
  Search,
  Sparkles,
  AlertCircle,
  AlertTriangle,
  Database,
  FileArchive,
  Brain,
  ChevronDown,
  ChevronRight,
  Bell,
  Wrench,
  Sun,
  Moon,
  Keyboard,
} from "lucide-react";
import NotificationsDropdown from "../components/NotificationsDropdown";
import MobileBottomNav from "../components/layout/MobileBottomNav";
import GlobalSearchModal from "../components/GlobalSearchModal";
import { useKeyboardShortcuts, KeyboardShortcutsHelp } from "../hooks/useKeyboardShortcuts";

const roleLabels = {
  cliente: "Cliente",
  consultor: "Consultor",
  mediador: "Mediador",
  intermediario: "Intermediário de Crédito",
  consultor_intermediario: "Consultor/Intermediário",
  ceo: "CEO",
  admin: "Administrador",
};

// Cores dos badges de papel - Azul Power Real Estate, Dourado Precision
const roleColors = {
  cliente: "bg-blue-100 text-blue-800",
  consultor: "bg-teal-600 text-white",                    // Power Real Estate
  mediador: "bg-amber-500 text-white",                    // Precision Crédito
  intermediario: "bg-amber-500 text-white",               // Precision Crédito
  consultor_intermediario: "bg-gradient-to-r from-blue-900 to-amber-500 text-white",
  ceo: "bg-blue-800 text-white",                          // Power Real Estate
  admin: "bg-slate-800 text-white",
};

const DashboardLayout = ({ children, title }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  // Keyboard shortcuts
  const { showHelpModal, setShowHelpModal, showSearchModal, setShowSearchModal, shortcuts } = useKeyboardShortcuts({
    onNew: () => navigate("/processos/novo"),
  });
  
  // Determinar quais secções devem estar abertas baseado na rota actual
  const getInitialOpenSections = () => {
    const path = location.pathname;
    
    // Rotas do grupo Negócio
    const negocioRoutes = ["/utilizadores", "/processos", "/clientes", "/leads", "/imoveis", "/minutas", "/meus-clientes"];
    // Rotas do grupo IA
    const iaRoutes = ["/configuracoes/ia", "/ai-insights", "/revisao-dados-ia", "/configuracoes/treino-ia"];
    // Rotas do grupo Sistema
    const sistemaRoutes = ["/admin/backups", "/definicoes", "/configuracoes", "/configuracoes/notificacoes", "/admin/logs", "/admin/mapeamentos-nif", "/admin/processos-background"];
    
    return {
      negocio: negocioRoutes.some(r => path.startsWith(r)),
      ia: iaRoutes.some(r => path.startsWith(r)),
      sistema: sistemaRoutes.some(r => path.startsWith(r)),
    };
  };
  
  const [openSections, setOpenSections] = useState(getInitialOpenSections);
  
  // Actualizar secções abertas quando a rota muda
  useEffect(() => {
    setOpenSections(getInitialOpenSections());
  }, [location.pathname]);

  const toggleSection = (section) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const getNavItems = () => {
    // Determinar o href correcto para o dashboard
    const dashboardHref = user?.role === "admin" ? "/admin" : "/staff";
    
    const baseItems = [
      {
        label: "Dashboard",
        icon: LayoutDashboard,
        href: dashboardHref,
      },
    ];

    // Estatísticas para todos os utilizadores autenticados
    const statsItem = {
      label: "Estatísticas",
      icon: BarChart3,
      href: "/estatisticas",
    };

    // Definições apenas para admin
    const settingsItem = {
      label: "Definições",
      icon: Settings,
      href: "/definicoes",
    };

    if (user?.role === "cliente") {
      return [
        ...baseItems,
        statsItem,
      ];
    }

    if (user?.role === "admin") {
      return {
        main: [
          ...baseItems,
          statsItem,
          {
            label: "Quadro Geral",
            icon: LayoutGrid,
            href: "/staff",
          },
        ],
        groups: [
          {
            id: "negocio",
            label: "Negócio",
            icon: Building2,
            items: [
              {
                label: "Utilizadores",
                icon: Users,
                href: "/utilizadores",
              },
              {
                label: "Clientes",
                icon: User,
                href: "/clientes",
              },
              {
                label: "Gestor de Visitas",
                icon: Search,
                href: "/leads",
              },
              {
                label: "Imóveis",
                icon: Building2,
                href: "/imoveis",
              },
              {
                label: "Minutas",
                icon: FileArchive,
                href: "/minutas",
              },
            ],
          },
          {
            id: "ia",
            label: "Ferramentas IA",
            icon: Brain,
            items: [
              {
                label: "Configuração de IA",
                icon: Sparkles,
                href: "/configuracoes/ia",
              },
              {
                label: "Treino do Agente",
                icon: Brain,
                href: "/configuracoes/treino-ia",
              },
              {
                label: "Agente IA",
                icon: Brain,
                href: "/ai-insights",
              },
              {
                label: "Revisão Dados IA",
                icon: FileText,
                href: "/revisao-dados-ia",
              },
            ],
          },
          {
            id: "sistema",
            label: "Sistema",
            icon: Wrench,
            items: [
              {
                label: "Mapeamentos NIF",
                icon: Database,
                href: "/admin/mapeamentos-nif",
              },
              {
                label: "Processos Background",
                icon: LayoutGrid,
                href: "/admin/processos-background",
              },
              {
                label: "Importar Idealista",
                icon: Home,
                href: "/admin/importar-idealista",
              },
              {
                label: "Backups",
                icon: Database,
                href: "/admin/backups",
              },
              settingsItem,
              {
                label: "Configurações",
                icon: Cog,
                href: "/configuracoes",
              },
              {
                label: "Notificações",
                icon: Bell,
                href: "/configuracoes/notificacoes",
              },
              {
                label: "Logs do Sistema",
                icon: AlertCircle,
                href: "/admin/logs",
              },
            ],
          },
        ],
      };
    }

    // For staff roles (consultor, mediador, intermediario, ceo, etc.)
    if (["consultor", "mediador", "intermediario", "consultor_intermediario", "ceo", "diretor", "administrativo"].includes(user?.role)) {
      const mainItems = [
        ...baseItems,
        statsItem,
      ];
      
      const negocioItems = [];
      
      // Adicionar "Os Meus Clientes" para consultores e intermediários
      if (["consultor", "intermediario", "mediador"].includes(user?.role)) {
        negocioItems.push({
          label: "Os Meus Clientes",
          icon: Users,
          href: "/meus-clientes",
        });
      }
      
      // Clientes para todos
      negocioItems.push({
        label: "Clientes",
        icon: User,
        href: "/clientes",
      });
      
      // Gestor de Visitas para todos
      negocioItems.push({
        label: "Gestor de Visitas",
        icon: Search,
        href: "/leads",
      });
      
      // Imóveis apenas para roles que não são intermediário/mediador
      if (!["intermediario", "mediador"].includes(user?.role)) {
        negocioItems.push({
          label: "Imóveis",
          icon: Building2,
          href: "/imoveis",
        });
      }
      
      // Minutas para todos os staff
      negocioItems.push({
        label: "Minutas",
        icon: FileArchive,
        href: "/minutas",
      });
      
      return {
        main: mainItems,
        groups: negocioItems.length > 0 ? [
          {
            id: "negocio",
            label: "Negócio",
            icon: Building2,
            items: negocioItems,
          },
        ] : [],
      };
    }

    return { main: [...baseItems], groups: [] };
  };

  const navData = getNavItems();

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 z-50 h-full w-64 bg-slate-900 text-white border-r border-slate-800 transform transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo - Power Real Estate & Precision Crédito */}
          <div className="h-16 flex items-center justify-between px-6 border-b border-slate-700 bg-slate-900">
            <div className="flex items-center gap-2">
              <Building2 className="h-6 w-6 text-amber-400" />
              <div className="flex flex-col">
                <span className="font-bold text-sm tracking-tight text-white">Power Real Estate</span>
                <span className="text-xs text-teal-400">&amp; Precision Crédito</span>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden text-white hover:bg-slate-700"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <ScrollArea className="flex-1 py-4">
            <nav className="space-y-1 px-3">
              {/* Main items - always visible */}
              {navData.main.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    to={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-teal-600 text-white"
                        : "text-slate-300 hover:bg-slate-800 hover:text-white"
                    }`}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <item.icon className="h-5 w-5" />
                    {item.label}
                  </Link>
                );
              })}
              
              {/* Collapsible groups */}
              {navData.groups.map((group) => (
                <Collapsible
                  key={group.id}
                  open={openSections[group.id]}
                  onOpenChange={() => toggleSection(group.id)}
                  className="mt-2"
                >
                  <CollapsibleTrigger className="flex items-center justify-between w-full px-3 py-2.5 rounded-md text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors">
                    <div className="flex items-center gap-3">
                      <group.icon className="h-5 w-5" />
                      {group.label}
                    </div>
                    {openSections[group.id] ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </CollapsibleTrigger>
                  <CollapsibleContent className="pl-4 mt-1 space-y-1">
                    {group.items.map((item) => {
                      const isActive = location.pathname === item.href;
                      return (
                        <Link
                          key={item.href}
                          to={item.href}
                          className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                            isActive
                              ? "bg-teal-600/80 text-white"
                              : "text-slate-400 hover:bg-slate-800 hover:text-white"
                          }`}
                          onClick={() => setSidebarOpen(false)}
                        >
                          <item.icon className="h-4 w-4" />
                          {item.label}
                        </Link>
                      );
                    })}
                  </CollapsibleContent>
                </Collapsible>
              ))}
            </nav>
          </ScrollArea>

          {/* User section */}
          <div className="p-4 border-t border-blue-800">
            <div className="flex items-center gap-3 px-2">
              <div className="h-9 w-9 rounded-full bg-amber-500/20 flex items-center justify-center">
                <User className="h-5 w-5 text-amber-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate text-white">{user?.name}</p>
                <span
                  className={`inline-block px-2 py-0.5 text-xs font-semibold rounded-full ${
                    roleColors[user?.role]
                  }`}
                >
                  {roleLabels[user?.role]}
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="h-16 border-b border-border bg-card sticky top-0 z-30">
          <div className="flex items-center justify-between h-full px-4 lg:px-6">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden"
                onClick={() => setSidebarOpen(true)}
              >
                <Menu className="h-5 w-5" />
              </Button>
              <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
            </div>

            <div className="flex items-center gap-2">
              {/* Search Button (Ctrl+K) */}
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setShowSearchModal(true)}
                className="hidden sm:flex items-center gap-2 text-muted-foreground"
              >
                <Search className="h-4 w-4" />
                <span className="text-xs">Pesquisar...</span>
                <kbd className="ml-2 px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">
                  Ctrl+K
                </kbd>
              </Button>
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => setShowSearchModal(true)}
                className="sm:hidden"
              >
                <Search className="h-5 w-5" />
              </Button>
              
              {/* Dark Mode Toggle */}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                title={isDark ? "Modo Claro" : "Modo Escuro"}
              >
                {isDark ? (
                  <Sun className="h-5 w-5" />
                ) : (
                  <Moon className="h-5 w-5" />
                )}
              </Button>
              
              {/* Keyboard Shortcuts Help */}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowHelpModal(true)}
                title="Atalhos de Teclado (Ctrl+/)"
                className="hidden sm:flex"
              >
                <Keyboard className="h-5 w-5" />
              </Button>
              
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => navigate("/")}
                className="gap-2 hidden sm:flex"
              >
                <Home className="h-4 w-4" />
                <span className="hidden md:inline">Página Inicial</span>
              </Button>
              
              {/* Notificações - só para utilizadores autenticados (não clientes) */}
              {user?.role !== "cliente" && (
                <NotificationsDropdown />
              )}
              
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="rounded-full">
                    <User className="h-5 w-5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <div className="px-2 py-1.5">
                    <p className="text-sm font-medium">{user?.name}</p>
                    <p className="text-xs text-muted-foreground">{user?.email}</p>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                    <LogOut className="h-4 w-4 mr-2" />
                    Terminar Sessão
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-6 pb-20 md:pb-6">{children}</main>
      </div>
      
      {/* Mobile Bottom Navigation */}
      <MobileBottomNav />
      
      {/* Global Search Modal */}
      <GlobalSearchModal open={showSearchModal} onOpenChange={setShowSearchModal} />
      
      {/* Keyboard Shortcuts Help Modal */}
      <Dialog open={showHelpModal} onOpenChange={setShowHelpModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Keyboard className="h-5 w-5" />
              Atalhos de Teclado
            </DialogTitle>
          </DialogHeader>
          <KeyboardShortcutsHelp shortcuts={shortcuts} />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DashboardLayout;
