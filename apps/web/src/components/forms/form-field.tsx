import { cloneElement, useId, type ReactElement } from "react";

type ControlProps = { id?: string; required?: boolean; "aria-describedby"?: string; "aria-invalid"?: boolean };

export function FormField({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: ReactElement<ControlProps> }) {
  const generated = useId();
  const id = children.props.id || generated;
  const description = [children.props["aria-describedby"], hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ") || undefined;
  return <div className="premium-field">
    <label htmlFor={id}>{label}{children.props.required && <span aria-hidden="true"> *</span>}</label>
    {cloneElement(children, { id, "aria-describedby": description, "aria-invalid": error ? true : children.props["aria-invalid"] })}
    {hint && <small id={`${id}-hint`}>{hint}</small>}
    {error && <p id={`${id}-error`} role="alert">{error}</p>}
  </div>;
}
