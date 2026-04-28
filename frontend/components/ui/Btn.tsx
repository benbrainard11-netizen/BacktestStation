import Link from "next/link";
import * as React from "react";

import { cn } from "@/lib/utils";

export type BtnVariant = "primary" | "default" | "ghost";

interface CommonProps {
  variant?: BtnVariant;
  className?: string;
  children: React.ReactNode;
}

type ButtonProps = CommonProps &
  React.ButtonHTMLAttributes<HTMLButtonElement> & { href?: undefined };
type AnchorProps = CommonProps & {
  href: string;
  /** When set, the link opens in a new tab. */
  external?: boolean;
};

type BtnProps = ButtonProps | AnchorProps;

const VARIANTS: Record<BtnVariant, string> = {
  primary:
    "bg-text text-bg border border-text hover:bg-text-dim hover:border-text-dim",
  default:
    "bg-surface text-text border border-border hover:bg-surface-alt",
  ghost:
    "bg-transparent text-text-dim border border-transparent hover:text-text",
};

const BASE =
  "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] leading-none transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-50 disabled:cursor-not-allowed";

/**
 * Direction A button. Three variants: primary (filled with text color so
 * it inverts), default (surface + border), ghost (transparent until hover).
 * Renders as <a> when `href` is given, otherwise <button>.
 */
export default function Btn(props: BtnProps) {
  const variant = props.variant ?? "default";
  const cls = cn(BASE, VARIANTS[variant], props.className);
  if ("href" in props && props.href) {
    const { href, external, children, className: _className, variant: _variant, ...rest } =
      props as AnchorProps & { className?: string };
    void _className;
    void _variant;
    if (external) {
      return (
        <a
          href={href}
          className={cls}
          target="_blank"
          rel="noopener noreferrer"
          {...(rest as React.AnchorHTMLAttributes<HTMLAnchorElement>)}
        >
          {children}
        </a>
      );
    }
    return (
      <Link href={href} className={cls}>
        {children}
      </Link>
    );
  }
  const { children, className: _className, variant: _variant, ...rest } =
    props as ButtonProps;
  void _className;
  void _variant;
  return (
    <button className={cls} {...rest}>
      {children}
    </button>
  );
}
