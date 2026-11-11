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
        dark: {
          950: '#080c14',
          900: '#0d131f',
          850: '#111827',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
        },
        accent: {
          blue: '#3b82f6',
          green: '#10b981',
          red: '#ef4444',
          amber: '#f59e0b',
          purple: '#8b5cf6',
        }
      },
    },
  },
  plugins: [],
}
