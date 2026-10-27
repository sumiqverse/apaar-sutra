/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        figma: {
          primary: '#000000',
          canvas: '#FFFFFF',
          lime: '#D4FF5B',
          lilac: '#E5D4FF',
          cream: '#FFF5EA',
          mint: '#D2F8E7',
          pink: '#FFD6E8',
          coral: '#FF8577',
          navy: '#0C1033',
          magenta: '#FF2F7C',
          hairline: '#E5E5E5',
          'hairline-soft': '#F0F0F0',
          'surface-soft': '#F5F5F5',
          success: '#0FA958',
        },
        brand: {
          50: '#f0f7ff',
          100: '#e0effe',
          500: '#0284c7',
          600: '#0369a1',
          700: '#075985',
          800: '#0c4a6e',
          900: '#082f49',
        },
        aicte: {
          navy: '#0f172a',
          saffron: '#ea580c',
          green: '#15803d',
        }
      },
      borderRadius: {
        'pill': '50px',
        'block': '24px',
      },
      fontFamily: {
        sans: ['Inter', 'figmaSans', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'figmaMono', 'SF Mono', 'Menlo', 'monospace'],
      },
      letterSpacing: {
        'display-xl': '-1.72px',
        'display-lg': '-0.96px',
        'subhead': '-0.26px',
        'eyebrow': '0.54px',
      }
    },
  },
  plugins: [],
}
