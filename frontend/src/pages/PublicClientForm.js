import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Checkbox } from "../components/ui/checkbox";
import { Progress } from "../components/ui/progress";
import { Building2, Loader2, ArrowLeft, ArrowRight, Check, User, Briefcase, Home, Users, CreditCard, HelpCircle, Info, Save, Clock } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL + "/api";

// Chave para localStorage
const DRAFT_STORAGE_KEY = "public_client_form_draft";
const DRAFT_TIMESTAMP_KEY = "public_client_form_draft_timestamp";

// Helper component for field hints
const FieldHint = ({ children }) => (
  <p className="text-xs text-muted-foreground mt-1 flex items-start gap-1">
    <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
    <span>{children}</span>
  </p>
);

// Progress Bar Component com percentagem
const FormProgressBar = ({ currentStep, totalSteps, completedFields, totalFields }) => {
  const stepProgress = ((currentStep - 1) / totalSteps) * 100;
  const fieldProgress = totalFields > 0 ? (completedFields / totalFields) * 100 : 0;
  
  return (
    <div className="space-y-2 mb-6">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          Passo {currentStep} de {totalSteps}
        </span>
        <span className="font-medium text-teal-600">
          {Math.round(fieldProgress)}% completo
        </span>
      </div>
      <Progress value={fieldProgress} className="h-2" />
      <div className="flex justify-between">
        {Array.from({ length: totalSteps }).map((_, idx) => (
          <div 
            key={idx}
            className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-colors ${
              idx + 1 < currentStep 
                ? "bg-teal-600 text-white" 
                : idx + 1 === currentStep 
                  ? "bg-teal-100 text-teal-700 border-2 border-teal-600" 
                  : "bg-gray-100 text-gray-400"
            }`}
          >
            {idx + 1 < currentStep ? <Check className="h-4 w-4" /> : idx + 1}
          </div>
        ))}
      </div>
    </div>
  );
};

// Auto-save indicator
const AutoSaveIndicator = ({ lastSaved, isSaving }) => {
  if (isSaving) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" />
        A guardar...
      </div>
    );
  }
  
  if (lastSaved) {
    return (
      <div className="flex items-center gap-2 text-xs text-green-600">
        <Save className="h-3 w-3" />
        Rascunho guardado às {lastSaved.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}
      </div>
    );
  }
  
  return null;
};

const ESTADOS_CIVIS = [
  { value: "solteiro", label: "Solteiro/a" },
  { value: "divorciado", label: "Divorciado/a" },
  { value: "viuvo", label: "Viúvo/a" },
  { value: "casado_adquiridos", label: "Casado/a: Comunhão de Adquiridos" },
  { value: "casado_geral", label: "Casado/a: Comunhão Geral de Bens" },
  { value: "casado_separacao", label: "Casado/a: Separação de Bens" },
  { value: "outro", label: "Outro" },
];

const TIPOS_IMOVEL = [
  { value: "apartamento", label: "Apartamento" },
  { value: "moradia", label: "Moradia" },
  { value: "outro", label: "Outro" },
];

const QUARTOS = [
  { value: "T0", label: "T0" },
  { value: "T1", label: "T1" },
  { value: "T2", label: "T2" },
  { value: "T3", label: "T3" },
  { value: "T4", label: "T4" },
  { value: "T5+", label: "T5+" },
];

const CARACTERISTICAS = [
  { value: "elevador", label: "Elevador" },
  { value: "2_wcs", label: "2 ou mais WCs" },
  { value: "transportes", label: "Proximidade de transportes públicos" },
  { value: "garagem", label: "Garagem" },
  { value: "piscina", label: "Piscina" },
  { value: "varanda", label: "Varanda" },
  { value: "andar_maximo", label: "Andar máximo" },
  { value: "outro", label: "Outro" },
];

const BANCOS = [
  "ABANCA", "BBVA", "BEST", "BIG", "BPI", "CGD", "Crédito Agrícola",
  "CTT", "Millennium bcp", "Novo Banco", "Popular", "Santander Totta", "Outro"
];

const PublicClientForm = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [blockedMessage, setBlockedMessage] = useState(null);
  
  const [formData, setFormData] = useState({
    // Dados Pessoais - Titular
    name: "",
    email: "",
    nif: "",
    documento_id: "",
    naturalidade: "",
    nacionalidade: "Portuguesa",
    phone: "",
    morada_fiscal: "",
    birth_date: "",
    estado_civil: "",
    compra_tipo: "individual",
    menor_35_anos: false,  // Checkbox para apoio ao estado
    
    // Dados do 2º Titular
    titular2_name: "",
    titular2_email: "",
    titular2_nif: "",
    titular2_documento_id: "",
    titular2_naturalidade: "",
    titular2_nacionalidade: "",
    titular2_phone: "",
    titular2_morada_fiscal: "",
    titular2_birth_date: "",
    titular2_estado_civil: "",
    
    // Imóvel Pretendido
    tipo_imovel: "",
    num_quartos: "",
    localizacao: "",
    caracteristicas: [],
    outras_caracteristicas: "",
    
    // Outras Informações
    outras_informacoes: "",
    
    // Situação Financeira
    acesso_portal_financas: "",
    chave_movel_digital: "",
    renda_habitacao_atual: "",
    precisa_vender_casa: "",
    efetivo: "",
    fiador: "",
    salario_liquido: "",
    
    // Bancos com créditos ativos
    bancos_creditos: [],
    
    // Capital e Financiamento
    capital_proprio: "",
    valor_financiado: "",
    
    // Consentimento
    consent_data: false,
    consent_contact: false,
  });

  const handleSubmit = async () => {
    if (!formData.consent_data || !formData.consent_contact) {
      toast.error("Por favor, aceite os termos para continuar");
      return;
    }

    setLoading(true);
    setBlockedMessage(null);

    try {
      const response = await axios.post(`${API_URL}/public/client-registration`, {
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        process_type: "ambos",
        personal_data: {
          nif: formData.nif,
          documento_id: formData.documento_id,
          naturalidade: formData.naturalidade,
          nacionalidade: formData.nacionalidade,
          morada_fiscal: formData.morada_fiscal,
          birth_date: formData.birth_date,
          estado_civil: formData.estado_civil,
          compra_tipo: formData.compra_tipo,
          menor_35_anos: formData.menor_35_anos,
        },
        titular2_data: formData.compra_tipo === "outra_pessoa" ? {
          name: formData.titular2_name,
          email: formData.titular2_email,
          nif: formData.titular2_nif,
          documento_id: formData.titular2_documento_id,
          naturalidade: formData.titular2_naturalidade,
          nacionalidade: formData.titular2_nacionalidade,
          phone: formData.titular2_phone,
          morada_fiscal: formData.titular2_morada_fiscal,
          birth_date: formData.titular2_birth_date,
          estado_civil: formData.titular2_estado_civil,
        } : null,
        real_estate_data: {
          tipo_imovel: formData.tipo_imovel,
          num_quartos: formData.num_quartos,
          localizacao: formData.localizacao,
          caracteristicas: formData.caracteristicas,
          outras_caracteristicas: formData.outras_caracteristicas,
          outras_informacoes: formData.outras_informacoes,
        },
        financial_data: {
          acesso_portal_financas: formData.acesso_portal_financas,
          chave_movel_digital: formData.chave_movel_digital,
          renda_habitacao_atual: formData.renda_habitacao_atual ? parseFloat(formData.renda_habitacao_atual) : null,
          precisa_vender_casa: formData.precisa_vender_casa,
          efetivo: formData.efetivo,
          fiador: formData.fiador,
          monthly_income: formData.salario_liquido ? parseFloat(formData.salario_liquido) : null,
          bancos_creditos: formData.bancos_creditos,
          capital_proprio: formData.capital_proprio ? parseFloat(formData.capital_proprio) : null,
          valor_financiado: formData.valor_financiado,
        },
      });

      // Verificar se o registo foi bloqueado por duplicado
      if (response.data.blocked) {
        setBlockedMessage(response.data.message);
        toast.info(response.data.message);
      } else {
        setSubmitted(true);
        toast.success("Registo enviado com sucesso!");
      }
    } catch (error) {
      console.error("Error submitting form:", error);
      toast.error(error.response?.data?.detail || "Erro ao enviar registo");
    } finally {
      setLoading(false);
    }
  };

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const toggleCaracteristica = (value) => {
    setFormData(prev => ({
      ...prev,
      caracteristicas: prev.caracteristicas.includes(value)
        ? prev.caracteristicas.filter(c => c !== value)
        : [...prev.caracteristicas, value]
    }));
  };

  const toggleBanco = (banco) => {
    setFormData(prev => ({
      ...prev,
      bancos_creditos: prev.bancos_creditos.includes(banco)
        ? prev.bancos_creditos.filter(b => b !== banco)
        : [...prev.bancos_creditos, banco]
    }));
  };

  const renderStepIndicator = () => (
    <div className="flex items-center justify-center mb-8 flex-wrap gap-2">
      {[1, 2, 3, 4, 5, 6].map((s) => (
        <div key={s} className="flex items-center">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors
              ${step >= s ? "bg-teal-600 text-white" : "bg-gray-200 text-gray-500"}`}
          >
            {step > s ? <Check className="h-4 w-4" /> : s}
          </div>
          {s < 6 && <div className={`w-8 md:w-12 h-0.5 ${step > s ? "bg-teal-600" : "bg-gray-200"}`} />}
        </div>
      ))}
    </div>
  );

  // Step 1: Dados Pessoais - Titular
  const renderStep1 = () => (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <User className="h-10 w-10 mx-auto mb-2 text-blue-900" />
        <h2 className="text-xl font-semibold mb-2 text-blue-950">Dados Pessoais - Titular</h2>
        <p className="text-muted-foreground">Informações do titular principal</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="name">Nome completo *</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => updateField("name", e.target.value)}
            placeholder="Nome completo"
            required
            data-testid="client-name"
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="email">Email *</Label>
          <Input
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => updateField("email", e.target.value)}
            placeholder="email@exemplo.pt"
            required
            data-testid="client-email"
          />
          <FieldHint>Utilizaremos este email para comunicar consigo sobre o seu processo.</FieldHint>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="phone">Telemóvel *</Label>
          <Input
            id="phone"
            type="tel"
            value={formData.phone}
            onChange={(e) => updateField("phone", e.target.value)}
            placeholder="+351 912 345 678"
            required
            data-testid="client-phone"
          />
          <FieldHint>Número de contacto direto para agendar visitas e reuniões.</FieldHint>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="nif">NIF *</Label>
          <Input
            id="nif"
            type="text"
            value={formData.nif}
            onChange={(e) => updateField("nif", e.target.value.replace(/\D/g, ""))}
            placeholder="123456789"
            maxLength={9}
            required
            data-testid="client-nif"
          />
          <FieldHint>Número de Identificação Fiscal - 9 dígitos, encontra-se no Cartão de Cidadão.</FieldHint>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="documento_id">Cartão de Cidadão/Passaporte *</Label>
          <Input
            id="documento_id"
            value={formData.documento_id}
            onChange={(e) => updateField("documento_id", e.target.value)}
            placeholder="Número do documento"
            required
            data-testid="client-documento"
          />
          <FieldHint>Número do documento de identificação válido.</FieldHint>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="naturalidade">Naturalidade *</Label>
          <Input
            id="naturalidade"
            value={formData.naturalidade}
            onChange={(e) => updateField("naturalidade", e.target.value)}
            placeholder="Local de nascimento"
            required
            data-testid="client-naturalidade"
          />
          <FieldHint>Freguesia/concelho onde nasceu.</FieldHint>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="nacionalidade">Nacionalidade *</Label>
          <Input
            id="nacionalidade"
            value={formData.nacionalidade}
            onChange={(e) => updateField("nacionalidade", e.target.value)}
            placeholder="Portuguesa"
            required
            data-testid="client-nacionalidade"
          />
        </div>
        
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="morada_fiscal">Morada Fiscal *</Label>
          <Input
            id="morada_fiscal"
            value={formData.morada_fiscal}
            onChange={(e) => updateField("morada_fiscal", e.target.value)}
            placeholder="Rua, número, código postal, localidade"
            required
            data-testid="client-morada"
          />
          <FieldHint>Morada completa conforme registada nas Finanças.</FieldHint>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="birth_date">Data de Nascimento *</Label>
          <Input
            id="birth_date"
            type="date"
            value={formData.birth_date}
            onChange={(e) => updateField("birth_date", e.target.value)}
            required
            data-testid="client-birth-date"
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="estado_civil">Estado Civil *</Label>
          <Select value={formData.estado_civil} onValueChange={(v) => updateField("estado_civil", v)}>
            <SelectTrigger data-testid="client-estado-civil">
              <SelectValue placeholder="Selecione" />
            </SelectTrigger>
            <SelectContent>
              {ESTADOS_CIVIS.map((ec) => (
                <SelectItem key={ec.value} value={ec.value}>{ec.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FieldHint>Se casado/a, indique o regime de bens do casamento.</FieldHint>
        </div>
        
        <div className="space-y-3 md:col-span-2 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-start space-x-3">
            <Checkbox
              id="menor_35_anos"
              checked={formData.menor_35_anos}
              onCheckedChange={(checked) => updateField("menor_35_anos", checked)}
              data-testid="client-menor-35"
            />
            <div className="space-y-1">
              <Label htmlFor="menor_35_anos" className="text-sm font-medium cursor-pointer">
                Tenho menos de 35 anos e pretendo usufruir do Apoio ao Estado
              </Label>
              <p className="text-xs text-amber-700">
                Se tem menos de 35 anos, pode ser elegível para benefícios fiscais na compra da primeira habitação própria permanente (isenção/redução de IMT e Imposto de Selo).
              </p>
            </div>
          </div>
        </div>
        
        <div className="space-y-2 md:col-span-2">
          <Label>Compra individualmente ou com outra pessoa? *</Label>
          <Select value={formData.compra_tipo} onValueChange={(v) => updateField("compra_tipo", v)}>
            <SelectTrigger data-testid="client-compra-tipo">
              <SelectValue placeholder="Selecione" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="individual">Individual</SelectItem>
              <SelectItem value="outra_pessoa">Com outra pessoa</SelectItem>
            </SelectContent>
          </Select>
          <FieldHint>Se comprar com outra pessoa (cônjuge, familiar, etc.), selecione "Com outra pessoa" para preencher os dados do 2º titular no próximo passo.</FieldHint>
        </div>
      </div>
    </div>
  );

  // Step 2: Dados do 2º Titular (se aplicável)
  const renderStep2 = () => (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <Users className="h-10 w-10 mx-auto mb-2 text-primary" />
        <h2 className="text-xl font-semibold mb-2">Dados do 2º Titular</h2>
        <p className="text-muted-foreground">
          {formData.compra_tipo === "outra_pessoa" 
            ? "Preencha os dados do segundo titular" 
            : "Não aplicável - compra individual"}
        </p>
      </div>
      
      {formData.compra_tipo === "outra_pessoa" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="titular2_name">Nome completo</Label>
            <Input
              id="titular2_name"
              value={formData.titular2_name}
              onChange={(e) => updateField("titular2_name", e.target.value)}
              placeholder="Nome completo"
              data-testid="titular2-name"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="titular2_email">Email</Label>
            <Input
              id="titular2_email"
              type="email"
              value={formData.titular2_email}
              onChange={(e) => updateField("titular2_email", e.target.value)}
              placeholder="email@exemplo.pt"
              data-testid="titular2-email"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="titular2_phone">Telemóvel</Label>
            <Input
              id="titular2_phone"
              type="tel"
              value={formData.titular2_phone}
              onChange={(e) => updateField("titular2_phone", e.target.value)}
              placeholder="+351 912 345 678"
              data-testid="titular2-phone"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="titular2_nif">NIF</Label>
            <Input
              id="titular2_nif"
              type="text"
              value={formData.titular2_nif}
              onChange={(e) => updateField("titular2_nif", e.target.value.replace(/\D/g, ""))}
              placeholder="123456789"
              maxLength={9}
              data-testid="titular2-nif"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="titular2_documento_id">Cartão de Cidadão/Passaporte</Label>
            <Input
              id="titular2_documento_id"
              value={formData.titular2_documento_id}
              onChange={(e) => updateField("titular2_documento_id", e.target.value)}
              placeholder="Número do documento"
              data-testid="titular2-documento"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="titular2_naturalidade">Naturalidade</Label>
            <Input
              id="titular2_naturalidade"
              value={formData.titular2_naturalidade}
              onChange={(e) => updateField("titular2_naturalidade", e.target.value)}
              placeholder="Local de nascimento"
              data-testid="titular2-naturalidade"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="titular2_nacionalidade">Nacionalidade</Label>
            <Input
              id="titular2_nacionalidade"
              value={formData.titular2_nacionalidade}
              onChange={(e) => updateField("titular2_nacionalidade", e.target.value)}
              placeholder="Portuguesa"
              data-testid="titular2-nacionalidade"
            />
          </div>
          
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="titular2_morada_fiscal">Morada Fiscal</Label>
            <Input
              id="titular2_morada_fiscal"
              value={formData.titular2_morada_fiscal}
              onChange={(e) => updateField("titular2_morada_fiscal", e.target.value)}
              placeholder="Rua, número, código postal, localidade"
              data-testid="titular2-morada"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="titular2_birth_date">Data de Nascimento</Label>
            <Input
              id="titular2_birth_date"
              type="date"
              value={formData.titular2_birth_date}
              onChange={(e) => updateField("titular2_birth_date", e.target.value)}
              data-testid="titular2-birth-date"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="titular2_estado_civil">Estado Civil</Label>
            <Select value={formData.titular2_estado_civil} onValueChange={(v) => updateField("titular2_estado_civil", v)}>
              <SelectTrigger data-testid="titular2-estado-civil">
                <SelectValue placeholder="Selecione" />
              </SelectTrigger>
              <SelectContent>
                {ESTADOS_CIVIS.map((ec) => (
                  <SelectItem key={ec.value} value={ec.value}>{ec.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      ) : (
        <div className="text-center py-8 bg-muted/50 rounded-lg">
          <p className="text-muted-foreground">
            Selecione "Com outra pessoa" no passo anterior para preencher os dados do 2º titular.
          </p>
        </div>
      )}
    </div>
  );

  // Step 3: Imóvel Pretendido
  const renderStep3 = () => (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <Home className="h-10 w-10 mx-auto mb-2 text-primary" />
        <h2 className="text-xl font-semibold mb-2">Imóvel Pretendido</h2>
        <p className="text-muted-foreground">Características do imóvel que procura</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>O que procura? *</Label>
          <Select value={formData.tipo_imovel} onValueChange={(v) => updateField("tipo_imovel", v)}>
            <SelectTrigger data-testid="imovel-tipo">
              <SelectValue placeholder="Selecione" />
            </SelectTrigger>
            <SelectContent>
              {TIPOS_IMOVEL.map((ti) => (
                <SelectItem key={ti.value} value={ti.value}>{ti.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        <div className="space-y-2">
          <Label>Número de quartos *</Label>
          <Select value={formData.num_quartos} onValueChange={(v) => updateField("num_quartos", v)}>
            <SelectTrigger data-testid="imovel-quartos">
              <SelectValue placeholder="Selecione" />
            </SelectTrigger>
            <SelectContent>
              {QUARTOS.map((q) => (
                <SelectItem key={q.value} value={q.value}>{q.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FieldHint>T0 = Estúdio/Loft, T1 = 1 quarto, T2 = 2 quartos, etc.</FieldHint>
        </div>
        
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="localizacao">Localização/Zona(s) preferida(s) *</Label>
          <Input
            id="localizacao"
            value={formData.localizacao}
            onChange={(e) => updateField("localizacao", e.target.value)}
            placeholder="Ex: Lisboa, Cascais, Sintra"
            required
            data-testid="imovel-localizacao"
          />
          <FieldHint>Pode indicar várias zonas separadas por vírgula. Quanto mais específico, melhor podemos ajudar.</FieldHint>
        </div>
        
        <div className="space-y-3 md:col-span-2">
          <Label>Características obrigatórias (selecione apenas as imprescindíveis) *</Label>
          <FieldHint>Selecione apenas características que são absolutamente essenciais. Menos seleções = mais opções de imóveis.</FieldHint>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {CARACTERISTICAS.map((c) => (
              <div key={c.value} className="flex items-center space-x-2">
                <Checkbox
                  id={c.value}
                  checked={formData.caracteristicas.includes(c.value)}
                  onCheckedChange={() => toggleCaracteristica(c.value)}
                  data-testid={`caracteristica-${c.value}`}
                />
                <Label htmlFor={c.value} className="text-sm cursor-pointer">{c.label}</Label>
              </div>
            ))}
          </div>
        </div>
        
        {formData.caracteristicas.includes("outro") && (
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="outras_caracteristicas">Outras características</Label>
            <Input
              id="outras_caracteristicas"
              value={formData.outras_caracteristicas}
              onChange={(e) => updateField("outras_caracteristicas", e.target.value)}
              placeholder="Especifique outras características"
              data-testid="imovel-outras-caracteristicas"
            />
          </div>
        )}
        
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="outras_informacoes">Outras informações</Label>
          <Textarea
            id="outras_informacoes"
            value={formData.outras_informacoes}
            onChange={(e) => updateField("outras_informacoes", e.target.value)}
            placeholder="Informações adicionais sobre o que procura..."
            rows={3}
            data-testid="imovel-outras-info"
          />
        </div>
      </div>
    </div>
  );

  // Step 4: Situação Financeira
  const renderStep4 = () => (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <Briefcase className="h-10 w-10 mx-auto mb-2 text-amber-500" />
        <h2 className="text-xl font-semibold mb-2 text-blue-950">Situação Financeira</h2>
        <p className="text-muted-foreground">Informações sobre a sua situação financeira</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="acesso_portal_financas">Acesso Portal das Finanças *</Label>
          <Input
            id="acesso_portal_financas"
            value={formData.acesso_portal_financas}
            onChange={(e) => updateField("acesso_portal_financas", e.target.value)}
            placeholder="Senha de acesso"
            required
            data-testid="fin-portal-financas"
          />
          <FieldHint>Necessário para validação de rendimentos. Pode criar em portaldasfinancas.gov.pt</FieldHint>
        </div>
        
        <div className="space-y-2">
          <Label>Chave Móvel Digital? *</Label>
          <Select value={formData.chave_movel_digital} onValueChange={(v) => updateField("chave_movel_digital", v)}>
            <SelectTrigger data-testid="fin-chave-movel">
              <SelectValue placeholder="Selecione" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sim">Sim</SelectItem>
              <SelectItem value="nao">Não</SelectItem>
            </SelectContent>
          </Select>
          <FieldHint>A CMD facilita a assinatura digital de documentos. Pode ativar em autenticacao.gov.pt</FieldHint>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="renda_habitacao_atual">Renda da habitação atual (€)</Label>
          <Input
            id="renda_habitacao_atual"
            type="number"
            value={formData.renda_habitacao_atual}
            onChange={(e) => updateField("renda_habitacao_atual", e.target.value)}
            placeholder="0.00"
            data-testid="fin-renda-atual"
          />
          <FieldHint>Se vive em casa própria ou com familiares, deixe em branco ou coloque 0.</FieldHint>
        </div>
        
        <div className="space-y-2">
          <Label>Precisa vender a casa atual?</Label>
          <Select value={formData.precisa_vender_casa} onValueChange={(v) => updateField("precisa_vender_casa", v)}>
            <SelectTrigger data-testid="fin-vender-casa">
              <SelectValue placeholder="Selecione" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sim">Sim</SelectItem>
              <SelectItem value="nao">Não</SelectItem>
            </SelectContent>
          </Select>
          <FieldHint>Se precisa vender para ter capital de entrada ou liquidar crédito existente.</FieldHint>
        </div>
        
        <div className="space-y-2">
          <Label>Efetivo?</Label>
          <Select value={formData.efetivo} onValueChange={(v) => updateField("efetivo", v)}>
            <SelectTrigger data-testid="fin-efetivo">
              <SelectValue placeholder="Selecione" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sim">Sim</SelectItem>
              <SelectItem value="nao">Não</SelectItem>
            </SelectContent>
          </Select>
          <FieldHint>Se tem contrato de trabalho sem termo (efetivo) ou está em período experimental.</FieldHint>
        </div>
        
        <div className="space-y-2">
          <Label>Fiador (caso seja necessário)?</Label>
          <Select value={formData.fiador} onValueChange={(v) => updateField("fiador", v)}>
            <SelectTrigger data-testid="fin-fiador">
              <SelectValue placeholder="Selecione" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sim">Sim</SelectItem>
              <SelectItem value="nao">Não</SelectItem>
            </SelectContent>
          </Select>
          <FieldHint>Ter um fiador disponível pode ajudar na aprovação do crédito.</FieldHint>
        </div>
        
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="salario_liquido">Salário mensal líquido (já com descontos) * (€)</Label>
          <Input
            id="salario_liquido"
            type="number"
            value={formData.salario_liquido}
            onChange={(e) => updateField("salario_liquido", e.target.value)}
            placeholder="0.00"
            required
            data-testid="fin-salario"
          />
        </div>
      </div>
    </div>
  );

  // Step 5: Bancos e Capital
  const renderStep5 = () => (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <CreditCard className="h-10 w-10 mx-auto mb-2 text-primary" />
        <h2 className="text-xl font-semibold mb-2">Créditos e Capital</h2>
        <p className="text-muted-foreground">Informações sobre créditos e capital disponível</p>
      </div>
      
      <div className="space-y-6">
        <div className="space-y-3">
          <Label>Bancos onde tem créditos ativos *</Label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {BANCOS.map((banco) => (
              <div key={banco} className="flex items-center space-x-2">
                <Checkbox
                  id={`banco-${banco}`}
                  checked={formData.bancos_creditos.includes(banco)}
                  onCheckedChange={() => toggleBanco(banco)}
                  data-testid={`banco-${banco.toLowerCase().replace(/\s+/g, '-')}`}
                />
                <Label htmlFor={`banco-${banco}`} className="text-sm cursor-pointer">{banco}</Label>
              </div>
            ))}
          </div>
          <FieldHint>Inclui crédito habitação, automóvel, pessoal, ou cartões de crédito com saldo em dívida.</FieldHint>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="capital_proprio">Capital próprio disponível * (€)</Label>
            <Input
              id="capital_proprio"
              type="number"
              value={formData.capital_proprio}
              onChange={(e) => updateField("capital_proprio", e.target.value)}
              placeholder="0.00"
              required
              data-testid="fin-capital-proprio"
            />
            <FieldHint>Dinheiro que tem disponível para entrada + despesas (escritura, IMT, seguros).</FieldHint>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="valor_financiado">Valor a financiar * (€)</Label>
            <Input
              id="valor_financiado"
              value={formData.valor_financiado}
              onChange={(e) => updateField("valor_financiado", e.target.value)}
              placeholder="Ex: 200.000€ ou 80% do valor"
              required
              data-testid="fin-valor-financiado"
            />
            <FieldHint>Pode indicar um valor fixo ou percentagem (ex: "90% do valor do imóvel").</FieldHint>
          </div>
        </div>
      </div>
    </div>
  );

  // Step 6: Confirmação
  const renderStep6 = () => (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <Check className="h-10 w-10 mx-auto mb-2 text-primary" />
        <h2 className="text-xl font-semibold mb-2">Confirmação</h2>
        <p className="text-muted-foreground">Reveja os seus dados e confirme o registo</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Dados Pessoais</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p><strong>Nome:</strong> {formData.name}</p>
            <p><strong>Email:</strong> {formData.email}</p>
            <p><strong>Telemóvel:</strong> {formData.phone}</p>
            <p><strong>NIF:</strong> {formData.nif}</p>
            <p><strong>Estado Civil:</strong> {ESTADOS_CIVIS.find(e => e.value === formData.estado_civil)?.label || "-"}</p>
          </CardContent>
        </Card>
        
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Imóvel Pretendido</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p><strong>Tipo:</strong> {TIPOS_IMOVEL.find(t => t.value === formData.tipo_imovel)?.label || "-"}</p>
            <p><strong>Quartos:</strong> {formData.num_quartos || "-"}</p>
            <p><strong>Localização:</strong> {formData.localizacao || "-"}</p>
            <p><strong>Características:</strong> {formData.caracteristicas.length > 0 ? formData.caracteristicas.join(", ") : "-"}</p>
          </CardContent>
        </Card>
        
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Situação Financeira</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p><strong>Salário líquido:</strong> {formData.salario_liquido ? `€${formData.salario_liquido}` : "-"}</p>
            <p><strong>Capital próprio:</strong> {formData.capital_proprio ? `€${formData.capital_proprio}` : "-"}</p>
            <p><strong>Valor a financiar:</strong> {formData.valor_financiado || "-"}</p>
            <p><strong>Efetivo:</strong> {formData.efetivo === "sim" ? "Sim" : formData.efetivo === "nao" ? "Não" : "-"}</p>
          </CardContent>
        </Card>
        
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Créditos Ativos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>{formData.bancos_creditos.length > 0 ? formData.bancos_creditos.join(", ") : "Nenhum banco selecionado"}</p>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4 pt-4 border-t">
        <div className="flex items-start space-x-3">
          <Checkbox
            id="consent_data"
            checked={formData.consent_data}
            onCheckedChange={(checked) => updateField("consent_data", checked)}
            data-testid="consent-data"
          />
          <Label htmlFor="consent_data" className="text-sm leading-relaxed cursor-pointer">
            Autorizo o tratamento dos meus dados pessoais para análise do meu pedido de crédito/imobiliário, nos termos do RGPD. *
          </Label>
        </div>
        <div className="flex items-start space-x-3">
          <Checkbox
            id="consent_contact"
            checked={formData.consent_contact}
            onCheckedChange={(checked) => updateField("consent_contact", checked)}
            data-testid="consent-contact"
          />
          <Label htmlFor="consent_contact" className="text-sm leading-relaxed cursor-pointer">
            Aceito ser contactado pela equipa para dar seguimento ao meu processo. *
          </Label>
        </div>
      </div>
    </div>
  );

  const renderSuccessMessage = () => (
    <div className="text-center py-12">
      <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <Check className="h-8 w-8 text-green-600" />
      </div>
      <h2 className="text-2xl font-semibold mb-2">Registo Enviado com Sucesso!</h2>
      <p className="text-muted-foreground mb-6">
        Obrigado pelo seu interesse. A nossa equipa irá analisar o seu pedido e entrará em contacto consigo brevemente.
      </p>
      <Button onClick={() => window.location.reload()}>Novo Registo</Button>
    </div>
  );

  const renderBlockedMessage = () => (
    <div className="text-center py-12">
      <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <Info className="h-8 w-8 text-amber-600" />
      </div>
      <h2 className="text-2xl font-semibold mb-2 text-amber-800">Processo Já Existente</h2>
      <p className="text-muted-foreground mb-6 max-w-md mx-auto">
        {blockedMessage}
      </p>
      <div className="space-y-3">
        <p className="text-sm text-gray-500">
          Caso tenha dúvidas, pode contactar-nos diretamente:
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <a 
            href="mailto:geral@precisioncredito.pt" 
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-md hover:bg-teal-700 transition-colors"
          >
            <HelpCircle className="h-4 w-4" />
            Contactar Precision
          </a>
          <a 
            href="mailto:geral@powerealestate.pt" 
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-md hover:bg-amber-600 transition-colors"
          >
            <HelpCircle className="h-4 w-4" />
            Contactar Power RE
          </a>
        </div>
      </div>
    </div>
  );

  const canProceed = () => {
    switch (step) {
      case 1:
        return formData.name && formData.email && formData.phone && formData.nif && 
               formData.documento_id && formData.naturalidade && formData.nacionalidade &&
               formData.morada_fiscal && formData.birth_date && formData.estado_civil;
      case 2:
        return true; // Always can proceed (2nd titular is optional)
      case 3:
        return formData.tipo_imovel && formData.num_quartos && formData.localizacao;
      case 4:
        return formData.acesso_portal_financas && formData.chave_movel_digital && formData.salario_liquido;
      case 5:
        return formData.capital_proprio && formData.valor_financiado;
      case 6:
        return formData.consent_data && formData.consent_contact;
      default:
        return true;
    }
  };

  if (submitted || blockedMessage) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-amber-50">
        {/* Header com cores da marca */}
        <header className="border-b bg-blue-950 text-white">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center gap-3">
              <Building2 className="h-8 w-8 text-amber-400" />
              <div>
                <h1 className="text-xl font-bold">Power Real Estate</h1>
                <p className="text-sm text-amber-400">& Precision Crédito</p>
              </div>
            </div>
          </div>
        </header>
        <main className="container mx-auto px-4 py-8">
          <Card className="max-w-4xl mx-auto border-blue-200 shadow-lg">
            <CardContent className="pt-6">
              {blockedMessage ? renderBlockedMessage() : renderSuccessMessage()}
            </CardContent>
          </Card>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-amber-50">
      {/* Header com cores da marca - Azul Power Real Estate + Dourado Precision */}
      <header className="border-b bg-blue-950 text-white shadow-md">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Building2 className="h-8 w-8 text-amber-400" />
              <div>
                <h1 className="text-xl font-bold text-white">Power Real Estate</h1>
                <p className="text-sm text-amber-400">& Precision Crédito</p>
              </div>
            </div>
            <a 
              href="/login" 
              className="flex items-center gap-2 text-sm text-amber-400 hover:text-amber-300 font-medium transition-colors"
            >
              <User className="h-4 w-4" />
              <span className="hidden sm:inline">Acesso Colaborador</span>
              <span className="sm:hidden">Login</span>
            </a>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <Card className="max-w-4xl mx-auto border-blue-200 shadow-lg">
          <CardHeader className="text-center bg-gradient-to-r from-blue-900 to-blue-800 text-white rounded-t-lg">
            <CardTitle className="text-white text-2xl">Formulário de Registo</CardTitle>
            <CardDescription className="text-blue-100">
              Preencha os seus dados para iniciar o processo de análise de crédito habitação
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            {renderStepIndicator()}
            
            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && renderStep3()}
            {step === 4 && renderStep4()}
            {step === 5 && renderStep5()}
            {step === 6 && renderStep6()}

            <div className="flex justify-between mt-8 pt-6 border-t border-blue-100">
              <Button
                variant="outline"
                onClick={() => setStep(Math.max(1, step - 1))}
                disabled={step === 1}
                className="border-blue-300 text-blue-900 hover:bg-blue-50"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Voltar
              </Button>
              
              {step < 6 ? (
                <Button
                  onClick={() => setStep(Math.min(6, step + 1))}
                  disabled={!canProceed()}
                  className="bg-teal-600 hover:bg-teal-700 text-white"
                >
                  Próximo
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={loading || !canProceed()}
                  className="bg-amber-500 hover:bg-amber-600 text-white"
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      A enviar...
                    </>
                  ) : (
                    <>
                      <Check className="mr-2 h-4 w-4" />
                      Submeter
                    </>
                  )}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
        
        {/* Footer com informação das empresas */}
        <div className="max-w-4xl mx-auto mt-8 text-center text-sm text-gray-600">
          <p>
            <span className="font-semibold text-blue-900">Power Real Estate</span> - Consultoria Imobiliária | 
            <span className="font-semibold text-amber-600 ml-1">Precision Crédito</span> - Intermediação de Crédito
          </p>
        </div>
      </main>
    </div>
  );
};

export default PublicClientForm;
