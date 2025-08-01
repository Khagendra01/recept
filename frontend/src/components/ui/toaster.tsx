import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { useToast } from '../../hooks/use-toast';

export function Toaster() {
  const { toasts, dismiss } = useToast();

  const getIcon = (variant?: string) => {
    switch (variant) {
      case 'destructive':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      default:
        return <Info className="h-5 w-5 text-blue-500" />;
    }
  };

  const getBorderColor = (variant?: string) => {
    switch (variant) {
      case 'destructive':
        return 'border-red-200';
      case 'success':
        return 'border-green-200';
      default:
        return 'border-blue-200';
    }
  };

  return (
    <div className="fixed top-0 right-0 z-50 w-full max-w-sm p-4 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: -50, scale: 0.3 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -50, scale: 0.5 }}
            transition={{ duration: 0.2 }}
            className={`mb-4 bg-white rounded-lg border shadow-lg pointer-events-auto ${getBorderColor(toast.variant)}`}
          >
            <div className="p-4">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  {getIcon(toast.variant)}
                </div>
                <div className="flex-1 min-w-0">
                  {toast.title && (
                    <p className="text-sm font-medium text-gray-900">
                      {toast.title}
                    </p>
                  )}
                  {toast.description && (
                    <p className="text-sm text-gray-600 mt-1">
                      {toast.description}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => dismiss(toast.id)}
                  className="flex-shrink-0 text-gray-400 hover:text-gray-500 focus:outline-none"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
