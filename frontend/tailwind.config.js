/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#050508",
          900: "#0a0a12",
          800: "#10101e",
          700: "#181828",
          600: "#22223a",
          500: "#2e2e50",
        },
        acid: {
          DEFAULT: "#00ff88",
          dim: "#00cc6a",
          muted: "#00ff8820",
        },
        plasma: {
          DEFAULT: "#7c3aed",
          light: "#a855f7",
          muted: "#7c3aed20",
        },
        signal: {
          DEFAULT: "#f59e0b",
          muted: "#f59e0b20",
        },
        danger: "#ef4444",
        frost: {
          DEFAULT: "#e2e8f0",
          dim: "#94a3b8",
          muted: "#e2e8f010",
        },
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "'Fira Code'", "monospace"],
        display: ["'Space Mono'", "monospace"],
        body: ["'IBM Plex Sans'", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "slide-up": "slideUp 0.3s ease-out",
        "fade-in": "fadeIn 0.4s ease-out",
        "scan": "scan 2s linear infinite",
      },
      keyframes: {
        slideUp: {
          "0%": { opacity: 0, transform: "translateY(12px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        fadeIn: {
          "0%": { opacity: 0 },
          "100%": { opacity: 1 },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
      },
      boxShadow: {
        acid: "0 0 20px rgba(0,255,136,0.15), 0 0 60px rgba(0,255,136,0.05)",
        plasma: "0 0 20px rgba(124,58,237,0.2), 0 0 60px rgba(124,58,237,0.08)",
        glass: "0 4px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
      },
    },
  },
  plugins: [],
};
