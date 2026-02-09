import { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const AuthContext = createContext(null);

const API_URL = process.env.REACT_APP_BACKEND_URL + "/api";

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);
  const [isImpersonating, setIsImpersonating] = useState(false);
  const [originalAdminName, setOriginalAdminName] = useState(null);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API_URL}/auth/me`);
      const userData = response.data;
      setUser(userData);
      
      // Verificar se está em modo impersonate
      if (userData.is_impersonated) {
        setIsImpersonating(true);
        setOriginalAdminName(userData.impersonated_by_name);
      } else {
        setIsImpersonating(false);
        setOriginalAdminName(null);
      }
    } catch (error) {
      console.error("Error fetching user:", error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await axios.post(`${API_URL}/auth/login`, {
      email,
      password,
    });
    const { access_token, user: userData } = response.data;
    localStorage.setItem("token", access_token);
    axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
    setToken(access_token);
    setUser(userData);
    setIsImpersonating(false);
    setOriginalAdminName(null);
    return userData;
  };

  const register = async (name, email, password, phone) => {
    const response = await axios.post(`${API_URL}/auth/register`, {
      name,
      email,
      password,
      phone,
    });
    const { access_token, user: userData } = response.data;
    localStorage.setItem("token", access_token);
    axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
    setToken(access_token);
    setUser(userData);
    return userData;
  };

  const logout = () => {
    localStorage.removeItem("token");
    delete axios.defaults.headers.common["Authorization"];
    setToken(null);
    setUser(null);
    setIsImpersonating(false);
    setOriginalAdminName(null);
  };

  // Impersonate - ver como outro utilizador
  const impersonate = async (userId) => {
    try {
      const response = await axios.post(`${API_URL}/admin/impersonate/${userId}`);
      const { access_token, user: userData } = response.data;
      
      // Guardar token original para poder voltar
      localStorage.setItem("originalToken", localStorage.getItem("token"));
      localStorage.setItem("token", access_token);
      
      axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
      setToken(access_token);
      setUser(userData);
      setIsImpersonating(true);
      setOriginalAdminName(userData.impersonated_by);
      
      return userData;
    } catch (error) {
      console.error("Error impersonating:", error);
      throw error;
    }
  };

  // Terminar impersonate e voltar à conta original
  const stopImpersonating = async () => {
    try {
      const response = await axios.post(`${API_URL}/admin/stop-impersonate`);
      const data = response.data;
      
      if (!data || !data.access_token) {
        throw new Error("Resposta inválida do servidor");
      }
      
      const { access_token, user: userData } = data;
      
      // Restaurar token original
      localStorage.removeItem("originalToken");
      localStorage.setItem("token", access_token);
      
      axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
      setToken(access_token);
      setUser(userData);
      setIsImpersonating(false);
      setOriginalAdminName(null);
      
      // Forçar reload da página para limpar estado
      window.location.href = "/admin";
      
      return userData;
    } catch (error) {
      console.error("Error stopping impersonate:", error);
      // Fallback: limpar estado local e redirecionar para login
      localStorage.removeItem("token");
      localStorage.removeItem("originalToken");
      setToken(null);
      setUser(null);
      setIsImpersonating(false);
      setOriginalAdminName(null);
      window.location.href = "/login";
      throw error;
    }
  };

  return (
    <AuthContext.Provider
      value={{ 
        user, 
        token, 
        loading, 
        login, 
        register, 
        logout,
        isImpersonating,
        originalAdminName,
        impersonate,
        stopImpersonating
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
