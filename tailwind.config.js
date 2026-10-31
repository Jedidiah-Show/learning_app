/** @type {import('tailwindcss').Config} */
// Palette direction: breath · wind · freshness · newness.
// Greens shift toward sea-glass teal, neutrals shift from warm beige to cool
// mist, the ML-pathway violet becomes sky-wind blue. The root identity
// (#083D2E) and the gold accent stay: RUACH is still the deep breath, dawn
// light still gilds it.
const brand = {
  50: '#edf8f5',
  100: '#d5f0e8',
  200: '#aae1d3',
  300: '#76ccb9',
  400: '#46b59c',
  500: '#2fa38a',
  600: '#218571',
  700: '#1b6a5b',
  800: '#17534a',
  900: '#083D2E',
  950: '#062a24',
};

module.exports = {
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
        emerald: {
          50: '#ecf8f6',
          100: '#d2f1ea',
          200: '#a7e2d5',
          300: '#72cfba',
          400: '#43b89e',
          500: '#2fa38a',
          600: '#218571',
          700: '#1b6a5b',
          800: '#1d5750',
          900: '#154339',
          950: '#08251f',
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
