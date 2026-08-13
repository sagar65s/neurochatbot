import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          bg: "#0F1115",
          surface: "#171A21",
          surface2: "#1E222B",
          border: "#272B35",
          text: "#E8EAED",
          muted: "#8B92A3",
        },
        paper: {
          bg: "#FAFAFB",
          surface: "#FFFFFF",
          surface2: "#F0F1F4",
          border: "#E3E5EA",
          text: "#1A1C22",
          muted: "#6B7280",
        },
        accent: {
          DEFAULT: "#5B6EF8",
          hover: "#4C5CE0",
        },
        provider: {
          gemini: "#5B8DEF",
          openrouter: "#B084F5",
          groq: "#F5A623",
          stub: "#6B7280",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "8px",
      },
    },
  },
  plugins: [],
};

export default config;
