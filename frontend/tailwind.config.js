/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        nexus: {
          bg: "#0a0e1a",
          surface: "#10152a",
          "surface-hover": "#161d38",
          border: "#1f2540",
          text: "#e8ecf7",
          "text-muted": "#8b93b0",
          blue: "#3b82f6",
          purple: "#8b5cf6",
        },
        module: {
          agriculture: "#1a4d2e",
          "agriculture-icon": "#4ade80",
          livestock: "#5c3a1e",
          "livestock-icon": "#f0a868",
          construction: "#5c4a1e",
          "construction-icon": "#f0c868",
          legal: "#1e3a5c",
          "legal-icon": "#68a8f0",
          finance: "#3a1e5c",
          "finance-icon": "#b068f0",
          education: "#1e5c52",
          "education-icon": "#68f0d8",
          social: "#5c1e42",
          "social-icon": "#f068a8",
          video: "#1e3a5c",
          "video-icon": "#68a8f0",
          maps: "#1e4a5c",
          "maps-icon": "#68d0f0",
          marketplace: "#3a1e5c",
          "marketplace-icon": "#a868f0",
          payments: "#1e3a2e",
          "payments-icon": "#4af0a8",
        },
      },
      backgroundImage: {
        "nexus-gradient": "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
        "nexus-globe": "radial-gradient(circle at 70% 40%, rgba(59,130,246,0.25), transparent 60%)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
