/** @type {import('tailwindcss').Config} */

module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg:      "#0a0a0a",
        surface: "#111111",
        border:  "#222222",
        accent:  "#ffffff",
        muted:   "#555555",
        text:    "#eeeeee",
        dim:     "#888888",
        green:   "#4ade80",
        red:     "#f87171",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      borderRadius: { card: "8px", sm: "4px" },
      boxShadow:    { card: "0 1px 3px rgba(0,0,0,.8)" },
    },
  },
  plugins: [],
}