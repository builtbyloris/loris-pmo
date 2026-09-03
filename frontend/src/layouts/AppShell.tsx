import { BrainCircuit, BriefcaseBusiness, FolderKanban, LogOut, Menu, Settings, X } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router-dom";

import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { ThemeToggle } from "../components/ThemeToggle";
import { NotificationsMenu } from "../features/collaboration/components/NotificationsMenu";
import { useAuth } from "../features/auth/AuthContext";

const navigation = [
  { path: "/portfolio", key: "portfolio", icon: BriefcaseBusiness },
  { path: "/projects", key: "projects", icon: FolderKanban },
  { path: "/copilot", key: "copilot", icon: BrainCircuit },
  { path: "/settings", key: "settings", icon: Settings },
] as const;

export function AppShell() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="app-shell">
      <button
        type="button"
        className={`mobile-backdrop ${menuOpen ? "visible" : ""}`}
        onClick={() => setMenuOpen(false)}
        aria-label={t("common.close")}
      />
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-mark" aria-hidden="true">L</div>
          <div>
            <strong>{t("brand.name")}</strong>
            <span>{t("brand.tagline")}</span>
          </div>
          <button className="sidebar-close" onClick={() => setMenuOpen(false)} type="button">
            <X size={19} />
            <span className="sr-only">{t("common.close")}</span>
          </button>
        </div>
        <nav className="sidebar-nav" aria-label={t("common.primaryNavigation")}>
          {navigation.map(({ path, key, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) => (isActive ? "active" : undefined)}
            >
              <Icon size={19} aria-hidden="true" />
              <span>{t(`nav.${key}`)}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-status">
          <span className="status-dot" />
          <span>{t("common.foundationVersion")}</span>
        </div>
      </aside>

      <div className="app-column">
        <header className="topbar">
          <button className="icon-button mobile-menu" type="button" onClick={() => setMenuOpen(true)}>
            <Menu size={20} />
            <span className="sr-only">{t("common.menu")}</span>
          </button>
          <div className="topbar-spacer" />
          <NotificationsMenu />
          <LanguageSwitcher />
          <ThemeToggle />
          <div className="account-chip" title={user?.email}>
            <span>{user?.email.slice(0, 1).toUpperCase()}</span>
            <p>{user?.display_name ?? user?.email}</p>
          </div>
          <button className="icon-button" type="button" onClick={() => void logout()}>
            <LogOut size={18} />
            <span className="sr-only">{t("common.logout")}</span>
          </button>
        </header>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
