/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // This line is the key: it tells Tailwind to look in all .html and .ts files inside the 'src' folder.
    "./src/**/*.{html,ts}", 
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};