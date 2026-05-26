"use client";

import { createContext, useContext } from "react";

interface ThemeCtx {
  theme: "light";
}

const ThemeContext = createContext<ThemeCtx>({ theme: "light" });

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <ThemeContext.Provider value={{ theme: "light" }}>
      {children}
    </ThemeContext.Provider>
  );
}
