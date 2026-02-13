import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Carregar variáveis de ambiente
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [react()],
    
    // Resolver alias @ para src/
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    
    // Tratar ficheiros .js como JSX (compatibilidade CRA)
    esbuild: {
      loader: 'jsx',
      include: /src\/.*\.jsx?$/,
      exclude: [],
    },
    
    // Servidor de desenvolvimento
    server: {
      port: 3000,
      host: '0.0.0.0',
      strictPort: true,
      // Hot Module Replacement
      hmr: {
        overlay: true,
      },
      // Watch options para melhor performance
      watch: {
        usePolling: true,
        interval: 100,
      },
    },
    
    // Preview server (para produção)
    preview: {
      port: 3000,
      host: '0.0.0.0',
    },
    
    // Build configuration
    build: {
      outDir: 'build',
      sourcemap: mode !== 'production',
      // Optimizações
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            'vendor-radix': [
              '@radix-ui/react-dialog',
              '@radix-ui/react-dropdown-menu',
              '@radix-ui/react-tabs',
              '@radix-ui/react-select',
              '@radix-ui/react-popover',
            ],
            'vendor-charts': ['recharts'],
          },
        },
      },
      // Tamanho máximo de chunks antes de avisar
      chunkSizeWarningLimit: 1000,
    },
    
    // Optimizações de dependências
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        'axios',
        'date-fns',
        'lucide-react',
      ],
      esbuildOptions: {
        loader: {
          '.js': 'jsx',
        },
      },
    },
    
    // Definir variáveis de ambiente que começam com REACT_APP_
    // O Vite usa VITE_ por defeito, mas vamos suportar ambos
    define: {
      // Suporte para process.env.REACT_APP_* (compatibilidade CRA)
      'process.env': Object.keys(env)
        .filter(key => key.startsWith('REACT_APP_'))
        .reduce((acc, key) => {
          acc[key] = JSON.stringify(env[key])
          return acc
        }, {}),
    },
    
    // CSS configuration
    css: {
      devSourcemap: true,
    },
    
    // Configurações de log
    logLevel: 'info',
    
    // Limpar console no HMR
    clearScreen: false,
  }
})
