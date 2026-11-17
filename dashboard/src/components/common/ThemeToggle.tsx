import React from 'react';
import { useTheme } from '../../context/ThemeContext';
import { Sun, Moon } from 'lucide-react';

export const ThemeToggle: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      title={isDark ? 'Beralih ke Mode Terang' : 'Beralih ke Mode Gelap'}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full p-0.5 border transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500/40 ${
        isDark
          ? 'bg-slate-800 border-slate-700'
          : 'bg-slate-200 border-slate-300'
      } ${className}`}
      role="switch"
      aria-checked={isDark}
    >
      <span className="sr-only">Beralih Tema Tampilan</span>
      <span
        className={`pointer-events-none flex h-5 w-5 transform items-center justify-center rounded-full shadow-sm transition-transform duration-200 ease-in-out ${
          isDark
            ? 'translate-x-5 bg-slate-950 text-blue-400 border border-slate-800'
            : 'translate-x-0 bg-white text-amber-500 border border-slate-200'
        }`}
      >
        {isDark ? (
          <Moon className="h-3 w-3 text-blue-400 fill-blue-400/20" />
        ) : (
          <Sun className="h-3 w-3 text-amber-500 fill-amber-500/20" />
        )}
      </span>
    </button>
  );
};
