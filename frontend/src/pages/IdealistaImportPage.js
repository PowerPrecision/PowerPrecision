/**
 * IdealistaImportPage - Importação de dados do Idealista
 * 
 * Como o Idealista bloqueia scrapers, oferecemos duas opções:
 * 1. Bookmarklet Simples - Copia dados para clipboard
 * 2. Bookmarklet Avançado - Abre o CRM automaticamente com dados
 * 3. Colar HTML - Copiar página e colar aqui
 */
import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import DashboardLayout from "../layouts/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { toast } from "sonner";
import {
  Home,
  Copy,
  Sparkles,
  Loader2,
  CheckCircle,
  ExternalLink,
  BookmarkPlus,
  ClipboardPaste,
  MapPin,
  Euro,
  Bed,
  Maximize,
  Building,
  User,
  Phone,
  Zap,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;
const CRM_URL = window.location.origin;

const IdealistaImportPage = () => {
  const [searchParams] = useSearchParams();
  const [htmlContent, setHtmlContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [extractedData, setExtractedData] = useState(null);
  const [activeTab, setActiveTab] = useState("paste"); // "paste" ou "bookmarklet"
  const [autoExtractDone, setAutoExtractDone] = useState(false);

  // Bookmarklet SIMPLES - copia dados para clipboard
  const bookmarkletSimple = `javascript:(function(){
    const data = {
      url: window.location.href,
      html: document.documentElement.outerHTML,
      title: document.title
    };
    const json = JSON.stringify(data);
    navigator.clipboard.writeText(json).then(() => {
      alert('Dados copiados! Cole no CRM para importar.');
    }).catch(() => {
      const ta = document.createElement('textarea');
      ta.value = json;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      alert('Dados copiados! Cole no CRM para importar.');
    });
  })();`;

  // Bookmarklet AVANÇADO - abre o CRM automaticamente com dados codificados
  const bookmarkletAdvanced = `javascript:(function(){
    var html=document.documentElement.outerHTML;
    var url=window.location.href;
    var encoded=btoa(unescape(encodeURIComponent(html.substring(0,50000))));
    var crmUrl='${CRM_URL}/admin/importar-idealista?auto=1&url='+encodeURIComponent(url)+'&data='+encoded;
    window.open(crmUrl,'_blank');
  })();`;

  // Auto-processar dados se vieram do bookmarklet avançado
  useEffect(() => {
    const autoProcess = searchParams.get("auto");
    const encodedData = searchParams.get("data");
    const sourceUrl = searchParams.get("url");
    
    if (autoProcess === "1" && encodedData && !autoExtractDone) {
      try {
        const decodedHtml = decodeURIComponent(escape(atob(encodedData)));
        const dataObj = {
          html: decodedHtml,
          url: sourceUrl || "idealista-bookmarklet"
        };
        setHtmlContent(JSON.stringify(dataObj));
        setAutoExtractDone(true);
        toast.info("Dados recebidos do Idealista! A processar automaticamente...");
        
        // Auto-extrair após um breve delay
        setTimeout(() => {
          handleExtractAuto(dataObj);
        }, 500);
      } catch (e) {
        console.error("Erro ao decodificar dados:", e);
        toast.error("Erro ao processar dados do bookmarklet");
      }
    }
  }, [searchParams, autoExtractDone]);

  // Função de extracção automática (para bookmarklet avançado)
  const handleExtractAuto = async (dataObj) => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_URL}/api/scraper/extract-html`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(dataObj),
      });

      if (response.ok) {
        const data = await response.json();
        setExtractedData(data);
        toast.success("Dados extraídos automaticamente!");
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao extrair dados");
      }
    } catch (error) {
      console.error("Erro:", error);
      toast.error("Erro ao processar dados");
    } finally {
      setLoading(false);
    }
  };

  const handleExtract = async () => {
    if (!htmlContent.trim()) {
      toast.error("Cole o conteúdo da página primeiro");
      return;
    }

    setLoading(true);
    setExtractedData(null);

    try {
      const token = localStorage.getItem("token");
      
      // Tentar parsear como JSON (do bookmarklet)
      let dataToSend = { html: htmlContent };
      try {
        const parsed = JSON.parse(htmlContent);
        if (parsed.html) {
          dataToSend = { html: parsed.html, url: parsed.url };
        }
      } catch {
        // Não é JSON, é HTML directo
      }

      const response = await fetch(`${API_URL}/api/scraper/extract-html`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(dataToSend),
      });

      if (response.ok) {
        const data = await response.json();
        setExtractedData(data);
        toast.success("Dados extraídos com sucesso!");
      } else {
        const error = await response.json();
        toast.error(error.detail || "Erro ao extrair dados");
      }
    } catch (error) {
      console.error("Erro:", error);
      toast.error("Erro ao processar dados");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateLead = async () => {
    if (!extractedData) return;

    try {
      const token = localStorage.getItem("token");
      
      // Mapear campos do extractedData para o formato esperado pelo PropertyLeadCreate
      // Os campos do scraper usam nomes em português, mas o modelo usa inglês
      const leadData = {
        url: extractedData.url || extractedData._source_url || `idealista-import-${Date.now()}`,
        title: extractedData.titulo || extractedData.title,
        price: extractedData.preco || extractedData.price,
        location: extractedData.localizacao || extractedData.location,
        typology: extractedData.tipologia || extractedData.typology,
        area: extractedData.area_util || extractedData.area,
        photo_url: extractedData.foto_principal || extractedData.photo_url,
        notes: `Importado do Idealista via HTML paste. Source: ${extractedData._source || 'idealista'}`,
        consultant: extractedData.agente_nome ? {
          name: extractedData.agente_nome,
          phone: extractedData.agente_telefone,
          email: extractedData.agente_email,
          agency_name: extractedData.agencia_nome,
        } : extractedData.consultant,
      };
      
      const response = await fetch(`${API_URL}/api/leads`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(leadData),
      });

      if (response.ok) {
        toast.success("Lead criado com sucesso!");
        setExtractedData(null);
        setHtmlContent("");
      } else {
        const errorData = await response.json();
        toast.error(errorData.detail || "Erro ao criar lead");
      }
    } catch (error) {
      console.error("Erro ao criar lead:", error);
      toast.error("Erro ao criar lead");
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 p-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Home className="h-6 w-6 text-primary" />
              Importar do Idealista
            </h1>
            <p className="text-muted-foreground mt-1">
              Extraia dados de imóveis do Idealista de forma simples
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Painel de Instruções */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookmarkPlus className="h-5 w-5" />
                Como Usar
              </CardTitle>
              <CardDescription>
                Escolha um dos métodos abaixo para importar dados
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Tabs */}
              <div className="flex gap-2">
                <Button
                  variant={activeTab === "paste" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setActiveTab("paste")}
                >
                  <ClipboardPaste className="h-4 w-4 mr-2" />
                  Colar Página
                </Button>
                <Button
                  variant={activeTab === "bookmarklet" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setActiveTab("bookmarklet")}
                >
                  <BookmarkPlus className="h-4 w-4 mr-2" />
                  Bookmarklet
                </Button>
              </div>

              {activeTab === "paste" ? (
                <div className="space-y-4">
                  <h3 className="font-medium">Método Simples - Colar Página</h3>
                  <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                    <li>Abra a página do imóvel no Idealista</li>
                    <li>Prima <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs">Ctrl+A</kbd> para seleccionar tudo</li>
                    <li>Prima <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs">Ctrl+C</kbd> para copiar</li>
                    <li>Cole no campo ao lado e clique "Extrair Dados"</li>
                  </ol>
                  <div className="p-3 bg-blue-50 dark:bg-blue-950 rounded-lg text-sm">
                    <p className="text-blue-700 dark:text-blue-300">
                      <strong>Dica:</strong> Funciona com qualquer página de imóvel do Idealista!
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <h3 className="font-medium">Método Rápido - Bookmarklet</h3>
                  <p className="text-sm text-muted-foreground">
                    Arraste um dos botões abaixo para a sua barra de favoritos:
                  </p>
                  
                  {/* Bookmarklet Avançado */}
                  <div className="p-4 border rounded-lg bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 border-green-200 dark:border-green-800">
                    <div className="flex items-center gap-2 mb-2">
                      <Zap className="h-4 w-4 text-green-600" />
                      <span className="font-medium text-green-700 dark:text-green-400">Recomendado - Um Clique</span>
                      <Badge variant="secondary" className="text-xs">Novo</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mb-3">
                      Abre o CRM automaticamente e extrai os dados. Não precisa colar nada!
                    </p>
                    <div className="flex justify-center">
                      <a
                        href={bookmarkletAdvanced}
                        onClick={(e) => e.preventDefault()}
                        draggable="true"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg font-medium shadow-lg hover:shadow-xl transition-shadow cursor-grab active:cursor-grabbing"
                      >
                        <Zap className="h-4 w-4" />
                        Idealista → CRM
                      </a>
                    </div>
                  </div>
                  
                  {/* Bookmarklet Simples */}
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Copy className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">Alternativo - Copiar</span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-3">
                      Copia os dados para o clipboard. Depois cole no campo ao lado.
                    </p>
                    <div className="flex justify-center">
                      <a
                        href={bookmarkletSimple}
                        onClick={(e) => e.preventDefault()}
                        draggable="true"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-primary to-primary/80 text-primary-foreground rounded-lg font-medium shadow-lg hover:shadow-xl transition-shadow cursor-grab active:cursor-grabbing"
                      >
                        <Sparkles className="h-4 w-4" />
                        Copiar Idealista
                      </a>
                    </div>
                  </div>
                  
                  <div className="p-3 bg-blue-50 dark:bg-blue-950 rounded-lg text-sm">
                    <p className="text-blue-700 dark:text-blue-300">
                      <strong>Como usar:</strong> Arraste o botão verde para os favoritos. 
                      No Idealista, clique nele e o CRM abrirá com os dados prontos!
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Painel de Input */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ClipboardPaste className="h-5 w-5" />
                Colar Conteúdo
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="html-content">Conteúdo da Página</Label>
                <Textarea
                  id="html-content"
                  placeholder="Cole aqui o conteúdo da página do Idealista (Ctrl+V)..."
                  value={htmlContent}
                  onChange={(e) => setHtmlContent(e.target.value)}
                  className="min-h-[200px] font-mono text-xs"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {htmlContent.length > 0 ? `${htmlContent.length.toLocaleString()} caracteres` : "Aguardando conteúdo..."}
                </p>
              </div>

              <Button 
                onClick={handleExtract} 
                disabled={loading || !htmlContent.trim()}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    A extrair dados...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Extrair Dados com IA
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Resultados */}
        {extractedData && (
          <Card className="border-green-200 bg-green-50/50 dark:bg-green-950/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-green-700 dark:text-green-400">
                <CheckCircle className="h-5 w-5" />
                Dados Extraídos
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Título */}
                {extractedData.titulo && (
                  <div className="col-span-full p-3 bg-white dark:bg-gray-900 rounded-lg">
                    <Label className="text-xs text-muted-foreground">Título</Label>
                    <p className="font-medium">{extractedData.titulo}</p>
                  </div>
                )}

                {/* Preço */}
                {extractedData.preco && (
                  <div className="p-3 bg-white dark:bg-gray-900 rounded-lg">
                    <Label className="text-xs text-muted-foreground flex items-center gap-1">
                      <Euro className="h-3 w-3" /> Preço
                    </Label>
                    <p className="font-bold text-lg text-green-600">
                      {typeof extractedData.preco === 'number' 
                        ? `€${extractedData.preco.toLocaleString()}`
                        : extractedData.preco}
                    </p>
                  </div>
                )}

                {/* Localização */}
                {extractedData.localizacao && (
                  <div className="p-3 bg-white dark:bg-gray-900 rounded-lg">
                    <Label className="text-xs text-muted-foreground flex items-center gap-1">
                      <MapPin className="h-3 w-3" /> Localização
                    </Label>
                    <p className="font-medium">{extractedData.localizacao}</p>
                  </div>
                )}

                {/* Tipologia */}
                {extractedData.tipologia && (
                  <div className="p-3 bg-white dark:bg-gray-900 rounded-lg">
                    <Label className="text-xs text-muted-foreground flex items-center gap-1">
                      <Bed className="h-3 w-3" /> Tipologia
                    </Label>
                    <p className="font-medium">{extractedData.tipologia}</p>
                  </div>
                )}

                {/* Área */}
                {extractedData.area_util && (
                  <div className="p-3 bg-white dark:bg-gray-900 rounded-lg">
                    <Label className="text-xs text-muted-foreground flex items-center gap-1">
                      <Maximize className="h-3 w-3" /> Área
                    </Label>
                    <p className="font-medium">{extractedData.area_util} m²</p>
                  </div>
                )}

                {/* Agente */}
                {extractedData.agente_nome && (
                  <div className="p-3 bg-white dark:bg-gray-900 rounded-lg">
                    <Label className="text-xs text-muted-foreground flex items-center gap-1">
                      <User className="h-3 w-3" /> Agente
                    </Label>
                    <p className="font-medium">{extractedData.agente_nome}</p>
                    {extractedData.agente_telefone && (
                      <p className="text-sm text-muted-foreground flex items-center gap-1">
                        <Phone className="h-3 w-3" /> {extractedData.agente_telefone}
                      </p>
                    )}
                  </div>
                )}

                {/* Características */}
                {extractedData.caracteristicas && extractedData.caracteristicas.length > 0 && (
                  <div className="col-span-full p-3 bg-white dark:bg-gray-900 rounded-lg">
                    <Label className="text-xs text-muted-foreground">Características</Label>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {extractedData.caracteristicas.map((c, i) => (
                        <Badge key={i} variant="secondary" className="text-xs">
                          {c}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Acções */}
              <div className="flex gap-3 mt-6">
                <Button onClick={handleCreateLead} className="flex-1">
                  <Building className="h-4 w-4 mr-2" />
                  Criar Lead com estes dados
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setExtractedData(null);
                    setHtmlContent("");
                  }}
                >
                  Limpar
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default IdealistaImportPage;
