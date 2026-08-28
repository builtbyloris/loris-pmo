import { BrainCircuit, FolderKanban, Settings } from "lucide-react";
import { useTranslation } from "react-i18next";

type Area = "projects" | "copilot" | "settings";
const icons = { projects: FolderKanban, copilot: BrainCircuit, settings: Settings };

export function PlaceholderPage({ area }: { area: Area }) {
  const { t } = useTranslation();
  const Icon = icons[area];
  return (
    <div className="placeholder-page">
      <div className="placeholder-icon"><Icon size={30} /></div>
      <p className="eyebrow">{t("placeholder.eyebrow")}</p>
      <h1>{t(`placeholder.${area}Title`)}</h1>
      <p>{t(`placeholder.${area}Body`)}</p>
    </div>
  );
}
