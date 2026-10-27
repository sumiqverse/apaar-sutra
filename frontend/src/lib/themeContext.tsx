import React, { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>("light");

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("dark");
    localStorage.removeItem("apaar-theme");
  }, []);

  const toggleTheme = () => {
    // DESIGN.md specifies monochrome white canvas with oversized pastel blocks; no dark theme
    setThemeState("light");
  };

  const setTheme = (_t: Theme) => {
    setThemeState("light");
  };

  return (
    <ThemeContext.Provider value={{ theme: "light", toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};
