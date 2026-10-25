/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#F7F8FA',
        surface: '#FFFFFF',
        navy: {
          DEFAULT: '#14213D',
          muted: '#3C4964',
          subtle: '#6A768F'
        },
        teal: {
          DEFAULT: '#0E7C66',
          hover: '#0A5B4B',
          light: '#E6F4F1'
        },
        amber: {
          DEFAULT: '#F2B134',
          light: '#FEF7E8'
        },
        coral: {
          DEFAULT: '#D9480F',
          light: '#FCEBE6'
        },
        border: {
          DEFAULT: '#E2E6EC',
          strong: '#CBD2DC'
        },
        lavender: {
          DEFAULT: '#A89FD8',
          light: '#F1EFFB'
        },
        ice: {
          DEFAULT: '#7EB8DA',
          light: '#EDF5FA'
        }
      },
      fontFamily: {
        heading: ['Sora', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        sans: ['DM Sans', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        subtle: '0 1px 3px 0 rgba(20, 33, 61, 0.05), 0 1px 2px -1px rgba(20, 33, 61, 0.05)',
        card: '0 4px 6px -1px rgba(20, 33, 61, 0.06), 0 2px 4px -2px rgba(20, 33, 61, 0.04)',
        elevated: '0 10px 15px -3px rgba(20, 33, 61, 0.08), 0 4px 6px -4px rgba(20, 33, 61, 0.03)',
      }
    },
  },
  plugins: [],
}
