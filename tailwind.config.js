/** @type {import('tailwindcss').Config} */
// Palette direction: breath · wind · freshness · newness.
// Cyan now carries the primary brand identity (breath / spirit), with the
// gold accent marking dawn light. Neutrals stay cool mist; the deep cyan
// replaces the old deep green for surfaces, text and gradients.
const brand = {
  50: '#ecfeff',
  100: '#cffafe',
  200: '#a5f3fc',
  300: '#67e8f9',
  400: '#22d3ee',
  500: '#06b6d4',
  600: '#0891b2',
  700: '#0e7490',
  800: '#155e75',
  900: '#164e63',
  950: '#083344',
};

module.exports = {
  // The app toggles `data-theme="dark"` on <html>; make `dark:` utilities follow
  // that attribute instead of prefers-color-scheme so they agree with the toggle.
  darkMode: ['selector', '[data-theme="dark"]'],
  content: ['./templates/**/*.html', './static/js/**/*.js'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Manrope', 'DM Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand,
        // Existing templates use these utility families for the primary
        // interface colour, so map them onto the RUACH identity.
        indigo: brand,
        emerald: brand,
        violet: {
          50: '#eef7fa',
          100: '#d9edf4',
          200: '#b5dcea',
          300: '#84c3da',
          400: '#4ea5c4',
          500: '#2e89ab',
          600: '#246e8f',
          700: '#205a75',
          800: '#1e4a61',
          900: '#173646',
          950: '#0c202e',
        },
        amber: {
          50: '#fdf9eb',
          100: '#fbf0c8',
          200: '#f6df8d',
          300: '#efc94e',
          400: '#e4b52a',
          500: '#D4AF37',
          600: '#b58c1b',
          700: '#8f6a14',
          800: '#6f5013',
          900: '#5a4113',
          950: '#34240a',
        },
        gold: {
          50: '#fdf9eb',
          100: '#fbf0c8',
          200: '#f6df8d',
          300: '#efc94e',
          400: '#e4b52a',
          500: '#D4AF37',
          600: '#b58c1b',
          700: '#8f6a14',
          800: '#6f5013',
          900: '#5a4113',
          950: '#34240a',
        },
        slate: {
          50: '#f3f8f8',
          100: '#e7f0f0',
          200: '#d3e3e3',
          300: '#b4cccd',
          400: '#8babb0',
          500: '#5d7c84',
          600: '#4b666d',
          700: '#3a5158',
          800: '#2a3d43',
          900: '#1b2b30',
          950: '#0e1a1e',
        },
      },
    },
  },
  plugins: [],
};
