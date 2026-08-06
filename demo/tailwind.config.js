/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#2563EB',
        'primary-hover': '#1D4ED8',
        'primary-active': '#1E40AF',
        accent: '#EA580C',
        bg: '#F8FAFC',
        surface: '#FFFFFF',
        fg: '#1E293B',
        'fg-2': '#334155',
        muted: '#64748B',
        border: '#E2E8F0',
        success: '#16A34A',
        warn: '#D97706',
        danger: '#DC2626',
        info: '#2563EB'
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans SC', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace']
      }
    }
  },
  plugins: []
}
