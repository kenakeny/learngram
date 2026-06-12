import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      borderRadius: {
        lg: "12px",
        md: "10px",
        sm: "8px",
      },
      animation: {
        "fade-pulse": "fade-pulse 2s ease-in-out infinite",
      },
      keyframes: {
        "fade-pulse": {
          "0%, 100%": { opacity: "0.2" },
          "50%": { opacity: "0.5" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
