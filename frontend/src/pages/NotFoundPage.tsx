import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

export function NotFoundPage() {
  const { t } = useTranslation();
  return <main className="full-page-state"><strong>404</strong><h1>{t("notFound.title")}</h1><p>{t("notFound.body")}</p><Link className="primary-button" to="/portfolio">{t("notFound.action")}</Link></main>;
}
