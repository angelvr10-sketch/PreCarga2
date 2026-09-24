/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        success: {
          DEFAULT: 'hsl(var(--success))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        warning: {
          DEFAULT: 'hsl(var(--warning))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        sidebar: {
          DEFAULT: 'hsl(var(--sidebar-background))',
          foreground: 'hsl(var(--sidebar-foreground))',
          primary: 'hsl(var(--sidebar-primary))',
          'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
          accent: 'hsl(var(--sidebar-accent))',
          'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
          border: 'hsl(var(--sidebar-border))',
          ring: 'hsl(var(--sidebar-ring))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        fluent: '8px',
      },
      boxShadow: {
        'fluent-1': '0 2px 4px rgba(0,0,0,0.18), 0 0 2px rgba(0,0,0,0.10)',
        'fluent-2': '0 4px 8px rgba(0,0,0,0.22), 0 0 2px rgba(0,0,0,0.12)',
        'fluent-3': '0 8px 16px rgba(0,0,0,0.26), 0 0 2px rgba(0,0,0,0.14)',
        'fluent-4': '0 16px 32px rgba(0,0,0,0.32), 0 0 2px rgba(0,0,0,0.16)',
        'fluent-dialog': '0 32px 64px rgba(0,0,0,0.45), 0 0 1px rgba(0,0,0,0.20)',
        'fluent-focus': '0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring))',
      },
      keyframes: {
        'fluent-pop': {
          from: { opacity: '0', transform: 'translateY(-4px) scale(0.98)' },
          to: { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        'fluent-fade': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
      },
      animation: {
        'fluent-pop': 'fluent-pop 180ms cubic-bezier(0.1, 0.9, 0.2, 1)',
        'fluent-fade': 'fluent-fade 160ms ease-out',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
