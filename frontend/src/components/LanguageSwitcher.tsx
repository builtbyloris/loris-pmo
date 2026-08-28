import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const language = i18n.resolvedLanguage === "it" ? "it" : "en";
  return (
    <div className="select-control">
      <Languages size={17} aria-hidden="true" />
      <select aria-label={t("common.language")} value={language} onChange={(event) => void i18n.changeLanguage(event.target.value)}>
        <option value="en">EN</option>
        <option value="it">IT</option>
      </select>
    </div>
  );
}
