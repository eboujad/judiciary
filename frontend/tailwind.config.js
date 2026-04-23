/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Judiciary dark-theme design system (from judiciary_efiling.html)
        bg:       '#0f1117',
        surface:  '#181c27',
        surface2: '#1e2436',
        gold:     '#d4a84b',
        'gold-dim':    'rgba(212,168,75,0.15)',
        'gold-border': 'rgba(212,168,75,0.3)',
        teal:     '#3ecfcf',
        'teal-dim':    'rgba(62,207,207,0.1)',
        red:      '#e05c5c',
        'red-dim':     'rgba(224,92,92,0.1)',
        green:    '#4eca8b',
        'green-dim':   'rgba(78,202,139,0.1)',
        blue:     '#5b8af5',
        'blue-dim':    'rgba(91,138,245,0.1)',
        amber:    '#f0a744',
        'amber-dim':   'rgba(240,167,68,0.1)',
        muted:    '#6b7280',
        ink:      '#e8eaf0',
        border:   'rgba(255,255,255,0.07)',
        border2:  'rgba(255,255,255,0.12)',
      },
      fontFamily: {
        serif: ['"DM Serif Display"', 'serif'],
        mono:  ['"DM Mono"', 'monospace'],
        sans:  ['"DM Sans"', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '8px',
      },
    },
  },
  plugins: [],
}
