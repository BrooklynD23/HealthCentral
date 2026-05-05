/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['Fraunces Variable', 'Georgia', 'serif'],
        body: ['Source Sans 3 Variable', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      colors: {
        surface: {
          DEFAULT: '#FAFAF8',
          elevated: '#FFFFFF',
          muted: '#F5F5F3',
          sunken: '#EEEDEB',
        },
        ink: {
          DEFAULT: '#1F1F1F',
          secondary: '#6B6B6B',
          tertiary: '#9A9A9A',
          disabled: '#BFBFBF',
        },
        accent: {
          DEFAULT: '#2D7D6F',
          subtle: '#E8F4F2',
          hover: '#256B5F',
          pressed: '#1E5A50',
        },
        status: {
          caution: '#D4A574',
          'caution-subtle': '#FDF6EF',
          attention: '#C9857A',
          'attention-subtle': '#FDF2F0',
          verified: '#7BA387',
          'verified-subtle': '#F0F7F2',
          info: '#6B8CAE',
          'info-subtle': '#F0F4F8',
          critical: '#C9857A',
          'critical-subtle': '#FDF2F0',
        },
        // Dark mode colors
        dark: {
          surface: {
            DEFAULT: '#1A1A1A',
            elevated: '#242424',
            muted: '#2E2E2E',
          },
          ink: {
            DEFAULT: '#F5F5F5',
            secondary: '#A0A0A0',
            tertiary: '#6B6B6B',
          },
        },
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.6' }],
        'lg': ['1.125rem', { lineHeight: '1.6' }],
        'xl': ['1.25rem', { lineHeight: '1.4' }],
        '2xl': ['1.5rem', { lineHeight: '1.3' }],
        '3xl': ['1.875rem', { lineHeight: '1.2' }],
        '4xl': ['2.25rem', { lineHeight: '1.1' }],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
      boxShadow: {
        'soft': '0 2px 8px rgba(0, 0, 0, 0.04)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.06)',
        'elevated': '0 8px 32px rgba(0, 0, 0, 0.08)',
        'focus': '0 0 0 3px rgba(45, 125, 111, 0.3)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'shimmer': 'shimmer 1.4s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(400%)' },
        },
      },
      transitionDuration: {
        '250': '250ms',
        '350': '350ms',
      },
    },
  },
  plugins: [],
}
