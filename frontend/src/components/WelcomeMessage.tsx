import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, AlertTriangle, Info } from 'lucide-react';
import { User } from '../lib/api';
import { authApi } from '../lib/api';
import { useToast } from '../hooks/use-toast';

interface WelcomeMessageProps {
  user: User | null;
  gmailStatus: any;
  onGmailSync?: () => void;
}

function WelcomeMessage({ user, gmailStatus, onGmailSync }: WelcomeMessageProps) {
  const { toast } = useToast();

  const handleConnectGmail = async () => {
    try {
      await authApi.triggerGmailSync();
      toast({
        title: 'Gmail Sync Started',
        description: 'We are fetching your latest emails. This may take a few moments.',
      });
      // Trigger parent component to refetch Gmail status
      if (onGmailSync) {
        onGmailSync();
      }
    } catch (error: any) {
      // Check if the error is about Gmail not being connected
      if (error.response?.status === 400 && 
          error.response?.data?.detail?.includes('Gmail not connected')) {
        // Redirect to Google OAuth to get Gmail access
        try {
          const response = await authApi.getGoogleAuthUrl();
          const { authorization_url } = response.data;
          window.location.href = authorization_url;
        } catch (authError) {
          toast({
            title: 'Authentication Failed',
            description: 'Failed to start Gmail authentication. Please try again.',
            variant: 'destructive',
          });
        }
      } else {
        toast({
          title: 'Sync Failed',
          description: error.response?.data?.detail || 'Failed to start Gmail sync. Please try again.',
          variant: 'destructive',
        });
      }
    }
  };

  const getStatusMessage = () => {
    if (!gmailStatus.connected) {
      return {
        type: 'warning',
        icon: AlertTriangle,
        title: 'Gmail Not Connected',
        message: 'Please complete the Gmail integration to start processing your receipt emails.',
        action: 'Connect Gmail',
        onClick: handleConnectGmail,
      };
    }

    if (gmailStatus.total_emails === 0) {
      return {
        type: 'info',
        icon: Info,
        title: 'Getting Started',
        message: 'We\'re fetching your emails. New receipts will be processed automatically.',
        action: null,
        onClick: null,
      };
    }

    if (gmailStatus.total_transactions > 0) {
      return {
        type: 'success',
        icon: CheckCircle,
        title: 'All Set!',
        message: `We've processed ${gmailStatus.total_transactions} transactions from your emails.`,
        action: null,
        onClick: null,
      };
    }

    return {
      type: 'info',
      icon: Info,
      title: 'Processing Emails',
      message: 'We\'re analyzing your emails for receipts. Check back in a few minutes.',
      action: null,
      onClick: null,
    };
  };

  const status = getStatusMessage();

  const getBackgroundColor = () => {
    switch (status.type) {
      case 'success':
        return 'bg-green-50 border-green-200';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200';
      case 'info':
      default:
        return 'bg-blue-50 border-blue-200';
    }
  };

  const getIconColor = () => {
    switch (status.type) {
      case 'success':
        return 'text-green-600';
      case 'warning':
        return 'text-yellow-600';
      case 'info':
      default:
        return 'text-blue-600';
    }
  };

  const getTextColor = () => {
    switch (status.type) {
      case 'success':
        return 'text-green-800';
      case 'warning':
        return 'text-yellow-800';
      case 'info':
      default:
        return 'text-blue-800';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-lg border p-6 ${getBackgroundColor()}`}
    >
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0">
          <status.icon className={`h-6 w-6 ${getIconColor()}`} />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <div>
              <h2 className={`text-xl font-semibold ${getTextColor()}`}>
                Welcome back, {user?.name || user?.email?.split('@')[0] || 'User'}!
              </h2>
              <h3 className={`text-lg font-medium ${getTextColor()} mt-1`}>
                {status.title}
              </h3>
              <p className={`text-sm ${getTextColor()} mt-1 opacity-90`}>
                {status.message}
              </p>
            </div>
            {status.action && status.onClick && (
              <button 
                onClick={status.onClick}
                className="px-4 py-2 bg-white text-blue-600 rounded-md font-medium hover:bg-gray-50 transition-colors duration-200"
              >
                {status.action}
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default WelcomeMessage;
