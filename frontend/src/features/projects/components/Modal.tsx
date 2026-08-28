import { X } from "lucide-react";
import type { PropsWithChildren, ReactNode } from "react";
import { useTranslation } from "react-i18next";

interface ModalProps extends PropsWithChildren {
  title: string;
  description?: string;
  open: boolean;
  onClose: () => void;
  footer?: ReactNode;
  wide?: boolean;
}

export function Modal({ title, description, open, onClose, footer, wide, children }: ModalProps) {
  const { t } = useTranslation();
  if (!open) return null;
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className={`modal-panel ${wide ? "wide" : ""}`} role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <header className="modal-header">
          <div><h2 id="modal-title">{title}</h2>{description && <p>{description}</p>}</div>
          <button className="icon-button" type="button" onClick={onClose} aria-label={t("common.closeDialog")}><X size={18} /></button>
        </header>
        <div className="modal-body">{children}</div>
        {footer && <footer className="modal-footer">{footer}</footer>}
      </section>
    </div>
  );
}
