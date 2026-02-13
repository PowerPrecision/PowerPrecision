/**
 * Skeleton Loaders - Componentes de loading elegantes
 * Para melhor UX durante carregamento de dados
 */
import { Skeleton } from "../components/ui/skeleton";

// Skeleton para cards de processo/cliente
export const ProcessCardSkeleton = () => (
  <div className="bg-card border rounded-lg p-4 space-y-3">
    <div className="flex items-start justify-between">
      <Skeleton className="h-5 w-[200px]" />
      <Skeleton className="h-5 w-[60px]" />
    </div>
    <div className="space-y-2">
      <Skeleton className="h-4 w-[150px]" />
      <Skeleton className="h-4 w-[180px]" />
    </div>
    <div className="flex gap-2">
      <Skeleton className="h-6 w-[80px]" />
      <Skeleton className="h-6 w-[60px]" />
    </div>
  </div>
);

// Skeleton para linhas de tabela
export const TableRowSkeleton = ({ columns = 5 }) => (
  <tr className="border-b">
    {Array.from({ length: columns }).map((_, i) => (
      <td key={i} className="p-4">
        <Skeleton className="h-4 w-full max-w-[150px]" />
      </td>
    ))}
  </tr>
);

// Skeleton para tabela completa
export const TableSkeleton = ({ rows = 5, columns = 5 }) => (
  <div className="rounded-md border">
    <table className="w-full">
      <thead>
        <tr className="border-b bg-muted/50">
          {Array.from({ length: columns }).map((_, i) => (
            <th key={i} className="p-4 text-left">
              <Skeleton className="h-4 w-[100px]" />
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: rows }).map((_, i) => (
          <TableRowSkeleton key={i} columns={columns} />
        ))}
      </tbody>
    </table>
  </div>
);

// Skeleton para dashboard stats
export const StatsCardSkeleton = () => (
  <div className="bg-card border rounded-lg p-4 space-y-2">
    <Skeleton className="h-4 w-[100px]" />
    <Skeleton className="h-8 w-[60px]" />
    <Skeleton className="h-3 w-[80px]" />
  </div>
);

// Skeleton para grid de stats
export const StatsGridSkeleton = ({ count = 4 }) => (
  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
    {Array.from({ length: count }).map((_, i) => (
      <StatsCardSkeleton key={i} />
    ))}
  </div>
);

// Skeleton para lista de processos
export const ProcessListSkeleton = ({ count = 6 }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {Array.from({ length: count }).map((_, i) => (
      <ProcessCardSkeleton key={i} />
    ))}
  </div>
);

// Skeleton para detalhes de processo
export const ProcessDetailsSkeleton = () => (
  <div className="space-y-6">
    {/* Header */}
    <div className="flex items-start justify-between">
      <div className="space-y-2">
        <Skeleton className="h-8 w-[250px]" />
        <Skeleton className="h-4 w-[180px]" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-10 w-[100px]" />
        <Skeleton className="h-10 w-[100px]" />
      </div>
    </div>
    
    {/* Stats */}
    <StatsGridSkeleton count={4} />
    
    {/* Content */}
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-4">
        <Skeleton className="h-[300px] w-full rounded-lg" />
      </div>
      <div className="space-y-4">
        <Skeleton className="h-[150px] w-full rounded-lg" />
        <Skeleton className="h-[150px] w-full rounded-lg" />
      </div>
    </div>
  </div>
);

// Skeleton para sidebar/navigation
export const SidebarSkeleton = () => (
  <div className="w-64 p-4 space-y-4">
    <Skeleton className="h-10 w-full" />
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </div>
  </div>
);

// Skeleton para form fields
export const FormFieldSkeleton = () => (
  <div className="space-y-2">
    <Skeleton className="h-4 w-[100px]" />
    <Skeleton className="h-10 w-full" />
  </div>
);

// Skeleton para formulário completo
export const FormSkeleton = ({ fields = 4 }) => (
  <div className="space-y-4">
    {Array.from({ length: fields }).map((_, i) => (
      <FormFieldSkeleton key={i} />
    ))}
    <Skeleton className="h-10 w-[120px]" />
  </div>
);

export default {
  ProcessCardSkeleton,
  TableRowSkeleton,
  TableSkeleton,
  StatsCardSkeleton,
  StatsGridSkeleton,
  ProcessListSkeleton,
  ProcessDetailsSkeleton,
  SidebarSkeleton,
  FormFieldSkeleton,
  FormSkeleton,
};
