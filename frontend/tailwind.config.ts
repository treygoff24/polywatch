import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        night: {
          900: "#050608",
          800: "#090b11"
        },
        neon: {
          cyan: "#00f5ff",
          magenta: "#ff00ff",
          lime: "#76ff03"
        }
      },
      boxShadow: {
        neon: "0 0 30px rgba(0, 245, 255, 0.4)"
      },
      fontFamily: {
        display: ["'Rajdhani'", "sans-serif"],
        body: ["'Inter'", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;

