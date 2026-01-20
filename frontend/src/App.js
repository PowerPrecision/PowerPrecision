import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import PublicClientForm from "./pages/PublicClientForm";
import ClientDashboard from "./pages/ClientDashboard";
import ConsultorDashboard from "./pages/ConsultorDashboard";
import MediadorDashboard from "./pages/MediadorDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import ProcessDetails from "./pages/ProcessDetails";
import NewProcess from "./pages/NewProcess";
import "./App.css";

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
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

const DashboardRedirect = () => {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;

  switch (user.role) {
    case "cliente":
      return <Navigate to="/cliente" replace />;
    case "consultor":
      return <Navigate to="/consultor" replace />;
    case "mediador":
      return <Navigate to="/mediador" replace />;
    case "admin":
      return <Navigate to="/admin" replace />;
    default:
      return <Navigate to="/login" replace />;
  }
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
          <Route path="/register" element={<RegisterPage />} />
          
          <Route path="/dashboard" element={<DashboardRedirect />} />
          
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
          
          <Route
            path="/consultor"
            element={
              <ProtectedRoute allowedRoles={["consultor"]}>
                <ConsultorDashboard />
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/mediador"
            element={
              <ProtectedRoute allowedRoles={["mediador"]}>
                <MediadorDashboard />
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/processo/:id"
            element={
              <ProtectedRoute>
                <ProcessDetails />
              </ProtectedRoute>
            }
          />
          
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
