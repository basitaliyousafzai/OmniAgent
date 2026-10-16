/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}"
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ide: {
          bg: "#111217",
          sidebar: "#181920",
          surface: "#1f2029",
          border: "#2b2d3a",
          accent: "#6366f1",
          hover: "#2a2c3a",
          highlight: "#383a4d"
        }
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};
