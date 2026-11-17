/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        cyber: {
          950: '#090d16',
          900: '#0e1422',
          850: '#121a2c',
          800: '#172238',
          700: '#21304e',
          accent: '#2563eb',
          accentHover: '#1d4ed8',
          neon: '#10b981',
          danger: '#ef4444',
          warning: '#f59e0b',
          sapphire: '#1e40af',
          ice: '#38bdf8',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
