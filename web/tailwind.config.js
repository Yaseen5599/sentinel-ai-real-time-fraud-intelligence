/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        canvas: '#F8FAFC',
        surface: '#FFFFFF',
        'surface-subtle': '#F1F5F9',
        'surface-border': '#E2E8F0',
        'surface-border-strong': '#CBD5E1',
        ink: {
          DEFAULT: '#0F172A',
          secondary: '#334155',
          muted: '#64748D',
          subtle: '#94A3B8',
        },
        sidebar: {
          DEFAULT: '#0A101D',
          hover: '#131B2E',
          active: '#1E293B',
          border: '#1E293B',
          ink: '#F8FAFC',
          'ink-muted': '#94A3B8',
        },
        brand: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
        },
        fraud: {
          DEFAULT: '#DC2626',
          subtle: '#FEF2F2',
          border: '#FECACA',
        },
        suspicious: {
          DEFAULT: '#D97706',
          subtle: '#FFFBEB',
          border: '#FDE68A',
        },
        legitimate: {
          DEFAULT: '#059669',
          subtle: '#ECFDF5',
          border: '#A7F3D0',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(15, 23, 42, 0.05), 0 1px 2px -1px rgba(15, 23, 42, 0.05)',
        'card-hover': '0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05)',
        elevated: '0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.04)',
      }
    },
  },
  plugins: [],
}
