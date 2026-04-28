/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: { 0: "#0F1419", 1: "#1A1F2B", 2: "#232A38" },
        border: { DEFAULT: "#2D3548", soft: "rgba(255,255,255,0.06)" },
        text: { 1: "#E6EAF2", 2: "#9AA4B8", 3: "#5A6680" },
        brand: { DEFAULT: "#3B82F6", 2: "#60A5FA" },
        success: "#10B981",
        warning: "#F59E0B",
        danger: "#EF4444",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: { sm: "6px", md: "10px", lg: "14px" },
      boxShadow: { 1: "0 1px 2px rgba(0,0,0,0.4)", 2: "0 4px 14px rgba(0,0,0,0.35)" },
    },
  },
  plugins: [],
};
