import { useEffect, useState, useCallback } from 'react';

export interface ToastMessage {
  id: number;
  text: string;
  type: 'success' | 'error' | 'info';
}

let nextId = 0;
const toastListeners = new Set<(toasts: ToastMessage[]) => void>();
let current: ToastMessage[] = [];

function notify() {
  for (const fn of toastListeners) fn([...current]);
}

export function toast(text: string, type: ToastMessage['type'] = 'info') {
  const msg: ToastMessage = { id: nextId++, text, type };
  current = [...current, msg];
  notify();
  setTimeout(() => {
    current = current.filter((t) => t.id !== msg.id);
    notify();
  }, 3000);
}

export function toastSuccess(text: string) { toast(text, 'success'); }
export function toastError(text: string) { toast(text, 'error'); }

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const dismiss = useCallback((id: number) => {
    current = current.filter((t) => t.id !== id);
    notify();
  }, []);

  useEffect(() => {
    toastListeners.add(setToasts);
    return () => { toastListeners.delete(setToasts); };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`} onClick={() => dismiss(t.id)}>
          {t.text}
        </div>
      ))}
    </div>
  );
}
