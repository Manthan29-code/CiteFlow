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
        cream: {
          50: 'rgb(var(--cream-50-rgb) / <alpha-value>)',
          100: 'rgb(var(--cream-100-rgb) / <alpha-value>)',
          200: 'rgb(var(--cream-200-rgb) / <alpha-value>)',
          300: 'rgb(var(--cream-300-rgb) / <alpha-value>)',
          DEFAULT: 'rgb(var(--cream-default-rgb) / <alpha-value>)',
        },
        charcoal: {
          900: 'rgb(var(--charcoal-900-rgb) / <alpha-value>)',
          800: 'rgb(var(--charcoal-800-rgb) / <alpha-value>)',
          700: 'rgb(var(--charcoal-700-rgb) / <alpha-value>)',
          DEFAULT: 'rgb(var(--charcoal-900-rgb) / <alpha-value>)',
        },
        indigo: {
          brand: '#4338ca',
          hover: '#3730a3',
          light: '#e0e7ff',
          muted: '#6366f1',
        },
        border: {
          light: 'rgb(var(--border-light-rgb) / <alpha-value>)',
          dark: 'rgb(var(--border-dark-rgb) / <alpha-value>)',
        }
      },
      fontFamily: {
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        sans: ['"Inter"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      letterSpacing: {
        'ultra-wide': '0.3em',
        'super-wide': '0.4em',
      },
      transitionTimingFunction: {
        'premium': 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
      boxShadow: {
        'indigo-soft': '0 10px 25px -5px rgba(67, 56, 202, 0.1), 0 8px 10px -6px rgba(67, 56, 202, 0.1)',
        'pulse-indigo': '0 0 20px rgba(67, 56, 202, 0.25)',
        'premium': '0 20px 40px -15px rgba(0, 0, 0, 0.07)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'mesh-drift': 'meshDrift 30s linear infinite',
      },
      keyframes: {
        meshDrift: {
          '0%': { transform: 'rotate(0deg) scale(1)' },
          '50%': { transform: 'rotate(180deg) scale(1.15)' },
          '100%': { transform: 'rotate(360deg) scale(1)' },
        }
      }
    },
  },
  plugins: [],
}
