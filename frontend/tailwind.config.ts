import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#05070d",
          900: "#0a0e18",
          850: "#0f1522",
          800: "#141b2b",
          700: "#1c2540",
          600: "#28345a",
        },
        accent: {
          400: "#5eead4",
          500: "#2dd4bf",
          600: "#0d9488",
        },
        signal: {
          red: "#f87171",
          amber: "#fbbf24",
          green: "#4ade80",
          blue: "#60a5fa",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
