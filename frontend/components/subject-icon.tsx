type SubjectIconProps = {
  icon: string | null | undefined;
  label: string;
  className?: string;
};


const ICON_MAP: Record<string, string> = {
  calculator: "🧮",
  book: "📖",
  language: "🗣️",
  flask: "🧪",
};


export function SubjectIcon({ icon, label, className }: SubjectIconProps) {
  const symbol = (icon && ICON_MAP[icon]) || "•";

  return (
    <span aria-label={label} className={className} role="img">
      {symbol}
    </span>
  );
}