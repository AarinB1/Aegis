import Link from "next/link";
import { ComponentPropsWithoutRef, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

type CommonProps = {
  variant?: ButtonVariant;
  children: ReactNode;
  className?: string;
};

type AnchorProps = CommonProps & {
  href: string;
} & Omit<ComponentPropsWithoutRef<"a">, "href" | "children" | "className">;

type ButtonProps = CommonProps &
  Omit<ComponentPropsWithoutRef<"button">, "children" | "className">;

const base =
  "inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium tracking-tight transition-colors duration-200 ease-damped focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-paper";

const styles: Record<ButtonVariant, string> = {
  primary: "bg-accent text-paper hover:bg-accent-hover",
  secondary:
    "bg-transparent text-ink ring-1 ring-inset ring-hairline hover:bg-surface",
  ghost: "bg-transparent text-ink hover:text-accent",
};

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button className={`${base} ${styles[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function LinkButton({
  variant = "primary",
  className = "",
  children,
  href,
  ...props
}: AnchorProps) {
  const isExternal = /^https?:\/\//.test(href);
  if (isExternal) {
    return (
      <a
        href={href}
        className={`${base} ${styles[variant]} ${className}`}
        target={props.target ?? "_blank"}
        rel={props.rel ?? "noreferrer"}
        {...props}
      >
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={`${base} ${styles[variant]} ${className}`}>
      {children}
    </Link>
  );
}
