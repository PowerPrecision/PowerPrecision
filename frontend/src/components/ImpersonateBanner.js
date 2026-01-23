/**
 * ====================================================================
 * BANNER DE IMPERSONATE - CREDITOIMO
 * ====================================================================
 * Mostra um banner fixo no topo quando o admin está a ver o sistema
 * como outro utilizador.
 * ====================================================================
 */

import { useAuth } from "../contexts/AuthContext";
import { Button } from "./ui/button";
import { Eye, X, User } from "lucide-react";
import { toast } from "sonner";

const ImpersonateBanner = () => {
  const { user, isImpersonating, originalAdminName, stopImpersonating } = useAuth();

  if (!isImpersonating) {
    return null;
  }

  const handleStopImpersonating = async () => {
    try {
      await stopImpersonating();
      toast.success("Voltou à sua conta de administrador");
    } catch (error) {
      toast.error("Erro ao terminar sessão de visualização");
    }
  };

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-amber-500 text-amber-950 py-2 px-4 shadow-md">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Eye className="h-5 w-5" />
          <span className="font-medium">
            A ver como: <strong>{user?.name}</strong> ({user?.role})
          </span>
          <span className="text-amber-800 text-sm">
            • Sessão iniciada por {originalAdminName}
          </span>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={handleStopImpersonating}
          className="bg-white hover:bg-amber-50 text-amber-900 border-amber-600"
        >
          <X className="h-4 w-4 mr-1" />
          Terminar Visualização
        </Button>
      </div>
    </div>
  );
};

export default ImpersonateBanner;
