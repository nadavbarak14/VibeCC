import type { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  clickable?: boolean;
}

export function Card({
  clickable = false,
  className = "",
  ...props
}: CardProps) {
  return (
    <div
      className={`rounded-lg border border-gray-200 bg-white shadow-sm ${
        clickable
          ? "cursor-pointer transition-shadow hover:shadow-md"
          : ""
      } ${className}`}
      {...props}
    />
  );
}
