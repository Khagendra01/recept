import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { CheckCircle, AlertCircle, Clock, ExternalLink } from 'lucide-react';
import { EmailNotification } from '../lib/api';

interface NotificationDropdownProps {
  notifications: EmailNotification[];
  onClose: () => void;
}

function NotificationDropdown({ notifications, onClose }: NotificationDropdownProps) {
  const getStatusIcon = (status: string, hasReceipts: boolean) => {
    if (!hasReceipts) return <Clock className="h-4 w-4 text-gray-400" />;
    
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'processing':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusText = (status: string, hasReceipts: boolean) => {
    if (!hasReceipts) return 'No receipts';
    
    switch (status) {
      case 'completed':
        return 'Processed';
      case 'failed':
        return 'Failed';
      case 'processing':
        return 'Processing';
      default:
        return 'Pending';
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="absolute right-0 mt-2 w-96 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50"
    >
      <div className="py-1">
        <div className="px-4 py-2 text-sm font-medium text-gray-900 border-b border-gray-200">
          Recent Notifications
        </div>
        
        <div className="max-h-96 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="px-4 py-3 text-sm text-gray-500 text-center">
              No new notifications
            </div>
          ) : (
            notifications.map((notification) => (
              <div
                key={notification.id}
                className="px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-1">
                    {getStatusIcon(notification.processing_status, notification.has_pdf_receipts)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {notification.subject || 'No subject'}
                      </p>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        notification.processing_status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : notification.processing_status === 'failed'
                          ? 'bg-red-100 text-red-800'
                          : notification.processing_status === 'processing'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {getStatusText(notification.processing_status, notification.has_pdf_receipts)}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-600 truncate">
                      From: {notification.sender || 'Unknown sender'}
                    </p>
                    
                    {notification.snippet && (
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                        {notification.snippet}
                      </p>
                    )}
                    
                    <p className="text-xs text-gray-400 mt-1">
                      {formatDate(notification.received_date)}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
        
        <div className="px-4 py-2 border-t border-gray-200">
          <Link
            to="/notifications"
            onClick={onClose}
            className="flex items-center justify-center w-full text-sm text-blue-600 hover:text-blue-500"
          >
            View all notifications
            <ExternalLink className="h-4 w-4 ml-1" />
          </Link>
        </div>
      </div>
    </motion.div>
  );
}

export default NotificationDropdown;
