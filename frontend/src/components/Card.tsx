import { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`card ${className}`}>{children}</div>;
}

export function CardHead({
  title,
  icon,
  right,
}: {
  title: string;
  icon?: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-5">
      <div className="card-title">
        {icon && <span className="text-text-2">{icon}</span>}
        {title}
      </div>
      {right}
    </div>
  );
}
