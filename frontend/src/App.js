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
          
          <Route path="/dashboard" element={<DashboardRedirect />} />
          
          {/* Cliente Dashboard */}
          <Route
            path="/cliente"
            element={
              <ProtectedRoute allowedRoles={["cliente"]}>
                <ClientDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cliente/novo-processo"
            element={
              <ProtectedRoute allowedRoles={["cliente"]}>
                <NewProcess />
              </ProtectedRoute>
            }
          />
          
          {/* Staff Dashboard (Consultor, Mediador, Consultor/Mediador, CEO) */}
          <Route
            path="/staff"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <StaffDashboard />
              </ProtectedRoute>
            }
          />
          
          {/* Legacy routes - redirect to staff dashboard */}
          <Route
            path="/consultor"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <Navigate to="/staff" replace />
              </ProtectedRoute>
            }
          />
          <Route
            path="/mediador"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <Navigate to="/staff" replace />
              </ProtectedRoute>
            }
          />
          <Route
            path="/intermediario"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <Navigate to="/staff" replace />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ceo"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <Navigate to="/staff" replace />
              </ProtectedRoute>
            }
          />
          <Route
            path="/consultor_intermediario"
            element={
              <ProtectedRoute allowedRoles={STAFF_ROLES}>
                <Navigate to="/staff" replace />
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
          
          {/* Statistics Page - All authenticated users */}
          <Route
            path="/estatisticas"
            element={
              <ProtectedRoute>
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
              <ProtectedRoute allowedRoles={[...STAFF_ROLES, "admin"]}>
                <ProcessesPage />
              </ProtectedRoute>
            }
          />
          
          {/* Process Details - Any authenticated user */}
          <Route
            path="/processo/:id"
            element={
              <ProtectedRoute>
                <ProcessDetails />
              </ProtectedRoute>
            }
          />
          <Route
            path="/process/:id"
            element={
              <ProtectedRoute>
                <ProcessDetails />
              </ProtectedRoute>
            }
          />
          
          {/* Settings Page - All authenticated users */}
          <Route
            path="/definicoes"
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        <ImpersonateBanner />
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
