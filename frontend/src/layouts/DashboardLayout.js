import { useAuth } from "../contexts/AuthContext";
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
  Home,
  LayoutGrid,
} from "lucide-react";
import { useState } from "react";

const roleLabels = {
  cliente: "Cliente",
  consultor: "Consultor",
  mediador: "Mediador",
  admin: "Administrador",
};

const roleColors = {
  cliente: "bg-blue-100 text-blue-800",
  consultor: "bg-emerald-100 text-emerald-800",
  mediador: "bg-purple-100 text-purple-800",
  admin: "bg-red-100 text-red-800",
};

const DashboardLayout = ({ children, title }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const getNavItems = () => {
    const baseItems = [
      {
        label: "Dashboard",
        icon: LayoutDashboard,
        href: `/${user?.role}`,
      },
    ];

    // Estatísticas para todos os utilizadores autenticados
    const statsItem = {
      label: "Estatísticas",
      icon: BarChart3,
      href: "/estatisticas",
    };

    if (user?.role === "cliente") {
      return [
        ...baseItems,
        statsItem,
      ];
    }

    if (user?.role === "admin") {
      return [
        ...baseItems,
        statsItem,
        {
          label: "Utilizadores",
          icon: Users,
          href: "/utilizadores",
        },
        {
          label: "Todos os Processos",
          icon: FileText,
          href: "/processos",
        },
      ];
    }

    // For staff roles (consultor, mediador, intermediario, ceo, etc.)
    if (["consultor", "mediador", "intermediario", "consultor_intermediario", "ceo"].includes(user?.role)) {
      return [
        ...baseItems,
        statsItem,
        {
          label: "Quadro Geral",
          icon: LayoutGrid,
          href: "/staff",
        },
        {
          label: "Todos os Processos",
          icon: FileText,
          href: "/processos",
        },
      ];
    }

    return baseItems;
  };

  const navItems = getNavItems();

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
        className={`fixed top-0 left-0 z-50 h-full w-64 bg-card border-r border-border transform transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="h-16 flex items-center justify-between px-6 border-b border-border">
            <div className="flex items-center gap-2">
              <Building2 className="h-6 w-6 text-primary" />
              <span className="font-bold text-lg tracking-tight">Power Real Estate & Precision</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <ScrollArea className="flex-1 py-4">
            <nav className="space-y-1 px-3">
              {navItems.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    to={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <item.icon className="h-5 w-5" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </ScrollArea>

          {/* User section */}
          <div className="p-4 border-t border-border">
            <div className="flex items-center gap-3 px-2">
              <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center">
                <User className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user?.name}</p>
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
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => navigate("/")}
                className="gap-2"
              >
                <Home className="h-4 w-4" />
                <span className="hidden sm:inline">Página Inicial</span>
              </Button>
              
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
        <main className="p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
};

export default DashboardLayout;
