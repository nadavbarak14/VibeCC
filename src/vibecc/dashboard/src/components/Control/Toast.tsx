import { useEffect } from "react";

export interface ToastMessage {
  id: string;
  text: string;
  type: "success" | "error";
}

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: ToastMessage;
  onDismiss: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 4000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  const bgColor = toast.type === "success" ? "bg-green-600" : "bg-red-600";

  return (
    <div
      data-testid={`toast-${toast.id}`}
      className={`${bgColor} rounded-lg px-4 py-3 text-sm font-medium text-white shadow-lg`}
    >
      {toast.text}
    </div>
  );
}

export function ToastContainer({ toasts, onDismiss }: ToastProps) {
  if (toasts.length === 0) return null;

  return (
    <div
      data-testid="toast-container"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2"
    >
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          toast={toast}
          onDismiss={() => onDismiss(toast.id)}
        />
      ))}
    </div>
  );
}
