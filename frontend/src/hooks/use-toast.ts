import { useState, useCallback } from 'react';

export interface Toast {
  id: string;
  title?: string;
  description?: string;
  variant?: 'default' | 'destructive';
}

let toastIdCounter = 0;
const generateToastId = () => (++toastIdCounter).toString();

const toastListeners: Array<(toast: Toast) => void> = [];
const dismissListeners: Array<(toastId: string) => void> = [];

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = generateToastId();
    const newToast = { ...toast, id };
    setToasts((prev) => [...prev, newToast]);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
      dismissToast(id);
    }, 5000);
    
    return id;
  }, []);

  const dismissToast = useCallback((toastId: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== toastId));
  }, []);

  const toast = useCallback((toast: Omit<Toast, 'id'>) => {
    return addToast(toast);
  }, [addToast]);

  return {
    toast,
    toasts,
    dismiss: dismissToast,
  };
}
