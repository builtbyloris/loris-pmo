import { useTranslation } from "react-i18next";

export function FullPageLoader() {
  const { t } = useTranslation();
  return (
    <div className="full-page-state" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{t("common.loading")}</span>
    </div>
  );
}
