import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0A0B0F',
        surface: '#13151B',
        elevated: '#1E2028',
        border: '#2A2D38',
        text: {
          DEFAULT: '#E6E8EE',
          muted: '#8B8FA8',
          faint: '#4A4E63',
        },
        accent: {
          DEFAULT: '#7C5CFF',
          hover: '#9070FF',
          dim: 'rgba(124,92,255,0.15)',
        },
        success: '#22C55E',
        warn: '#F59E0B',
        danger: '#EF4444',
        'chart-growth': '#7C5CFF',
        'chart-sales': '#3B82F6',
        'chart-data': '#06B6D4',
        'chart-outreach': '#22C55E',
        'chart-content': '#F59E0B',
        'chart-meta': '#EC4899',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Fira Code', 'monospace'],
      },
      fontSize: {
        hero: ['48px', { lineHeight: '1', letterSpacing: '-0.02em' }],
      },
      animation: {
        'pulse-slow': 'pulse 2s ease-in-out infinite',
        'pulse-fast': 'pulse 0.5s ease-in-out infinite',
        'spin-slow': 'spin 4s linear infinite',
      },
    },
  },
  plugins: [],
};

export default config;
