import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

type Theme = 'dark' | 'light';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem('tilik_theme') || localStorage.getItem('cyber_patrol_theme');
    if (saved === 'light' || saved === 'dark') {
      return saved;
    }
    return 'dark';
  });

  const applyThemeClasses = useCallback((newTheme: Theme) => {
    const root = document.documentElement;
    // Enable synchronized smooth CSS transitions across all elements
    root.classList.add('theme-transitioning');

    if (newTheme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.remove('dark');
      root.classList.add('light');
    }
    localStorage.setItem('tilik_theme', newTheme);
    localStorage.setItem('cyber_patrol_theme', newTheme);

    // Clean up transition class after animation finishes so regular interactions are instant
    const timer = setTimeout(() => {
      root.classList.remove('theme-transitioning');
    }, 360);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    applyThemeClasses(theme);
  }, [theme, applyThemeClasses]);

  const setTheme = useCallback((newTheme: Theme) => {
    if (newTheme === theme) return;

    if ('startViewTransition' in document && typeof (document as any).startViewTransition === 'function') {
      (document as any).startViewTransition(() => {
        setThemeState(newTheme);
      });
    } else {
      setThemeState(newTheme);
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
  }, [theme, setTheme]);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
