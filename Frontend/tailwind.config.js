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
          50: '#fdfcfb',
          100: '#fcfbf9',
          200: '#f7f5f0',
          300: '#ede8df',
          DEFAULT: '#fcfbf9',
        },
        charcoal: {
          900: '#171717',
          800: '#212121',
          700: '#2b2b2b',
          DEFAULT: '#171717',
        },
        indigo: {
          brand: '#4338ca',
          hover: '#3730a3',
          light: '#e0e7ff',
          muted: '#6366f1',
        },
        border: {
          light: '#e5e5e5',
          dark: '#2e2e2e',
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
