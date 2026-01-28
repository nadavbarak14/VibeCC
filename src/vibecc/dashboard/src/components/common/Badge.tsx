interface BadgeProps {
  label: string;
  color: "green" | "gray" | "yellow" | "red";
}

const colorStyles: Record<BadgeProps["color"], string> = {
  green: "bg-green-100 text-green-800",
  gray: "bg-gray-100 text-gray-800",
  yellow: "bg-yellow-100 text-yellow-800",
  red: "bg-red-100 text-red-800",
};

export function Badge({ label, color }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colorStyles[color]}`}
    >
      {label}
    </span>
  );
}
