import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

type Theme = "light" | "dark";

function initialTheme(): Theme {
  return localStorage.getItem("loris-theme") === "light" ? "light" : "dark";
}

export function ThemeToggle() {
  const { t } = useTranslation();
  const [theme, setTheme] = useState<Theme>(initialTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("loris-theme", theme);
  }, [theme]);
  const nextTheme = theme === "dark" ? "light" : "dark";
  return (
    <button
      className="icon-button"
      type="button"
      onClick={() => setTheme(nextTheme)}
      aria-label={t(nextTheme === "light" ? "common.useLightTheme" : "common.useDarkTheme")}
    >
      {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
