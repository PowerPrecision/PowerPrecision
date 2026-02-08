import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import ImpersonateBanner from "./components/ImpersonateBanner";
import LoginPage from "./pages/LoginPage";
import PublicClientForm from "./pages/PublicClientForm";
import StaffDashboard from "./pages/StaffDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import ProcessDetails from "./pages/ProcessDetails";
import StatisticsPage from "./pages/StatisticsPage";
import UsersManagementPage from "./pages/UsersManagementPage";
import ProcessesPage from "./pages/ProcessesPage";
import SettingsPage from "./pages/SettingsPage";
import FilteredProcessList from "./pages/FilteredProcessList";
import PendingItemsList from "./pages/PendingItemsList";
import SystemConfigPage from "./pages/SystemConfigPage";
import PropertiesPage from "./pages/PropertiesPage";
import ClientsPage from "./pages/ClientsPage";
import "./App.css";

// Staff roles that can access the Kanban dashboard
const STAFF_ROLES = ["consultor", "mediador", "intermediario", "diretor", "administrativo", "ceo", "admin"];

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/staff" replace />;
  }

  return children;
};

const DashboardRedirect = () => {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;

  // Admin vai para /admin, todos os outros staff vão para /staff
  if (user.role === "admin") {
    return <Navigate to="/admin" replace />;
  }
  return <Navigate to="/staff" replace />;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public client registration form - no auth required */}
          <Route path="/" element={<PublicClientForm />} />
          <Route path="/registo" element={<PublicClientForm />} />
          
          {/* Staff login */}
          <Route path="/login" element={<LoginPage />} />
          
          {/* Dashboard redirect */}
          <Route path="/dashboard" element={<DashboardRedirect />} />
          
          {/* Staff Dashboard (Consultor, Mediador, Diretor, Administrativo, CEO) */}
          <Route
            path="/staff"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <StaffDashboard />
              </ProtectedRoute>
            }
          />
          
          {/* Admin Dashboard - Full access */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          
          {/* Statistics Page - Staff and Admin */}
          <Route
            path="/estatisticas"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <StatisticsPage />
              </ProtectedRoute>
            }
          />
          
          {/* Users Management Page - Admin only */}
          <Route
            path="/utilizadores"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <UsersManagementPage />
              </ProtectedRoute>
            }
          />
          
          {/* Processes Page - Staff and Admin */}
          <Route
            path="/processos"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <ProcessesPage />
              </ProtectedRoute>
            }
          />
          
          {/* Properties Page - Staff and Admin */}
          <Route
            path="/imoveis"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <PropertiesPage />
              </ProtectedRoute>
            }
          />
          
          {/* Clients Page - Staff and Admin */}
          <Route
            path="/clientes"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <ClientsPage />
              </ProtectedRoute>
            }
          />
          
          {/* Process Details - Staff and Admin */}
          <Route
            path="/processo/:id"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <ProcessDetails />
              </ProtectedRoute>
            }
          />
          <Route
            path="/process/:id"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <ProcessDetails />
              </ProtectedRoute>
            }
          />
          
          {/* Settings Page - Staff and Admin */}
          <Route
            path="/definicoes"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          
          {/* System Configuration - Admin only */}
          <Route
            path="/configuracoes"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <SystemConfigPage />
              </ProtectedRoute>
            }
          />
          
          {/* Filtered Process List - Staff and Admin */}
          <Route
            path="/processos-filtrados"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <FilteredProcessList />
              </ProtectedRoute>
            }
          />
          
          {/* Pending Items List - Staff and Admin */}
          <Route
            path="/pendentes"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <PendingItemsList />
              </ProtectedRoute>
            }
          />
          
          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
        <ImpersonateBanner />
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
