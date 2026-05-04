export function Progress({ value, tone = "brand" }: { value: number; tone?: "brand" | "success" | "warning" | "danger" }) {
  const safeValue = Math.min(Math.max(value, 0), 100);
  
  const bgMap = {
    brand: "bg-blue-600",
    success: "bg-emerald-600",
    warning: "bg-orange-500",
    danger: "bg-rose-500"
  };

  return (
    <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
      <div 
        className={`${bgMap[tone]} h-2.5 rounded-full transition-all duration-500 ease-out`}
        style={{ width: `${safeValue}%` }}
      />
    </div>
  );
}
