import { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden ${className}`}>
      {children}
    </div>
  );
}

export function CardHead({ title, action, icon }: { title: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
      <div className="flex items-center gap-2">
        {icon && <div className="text-gray-400 flex items-center justify-center">{icon}</div>}
        <h3 className="font-semibold text-gray-800">{title}</h3>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
