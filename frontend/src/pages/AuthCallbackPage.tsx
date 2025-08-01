import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CheckCircle, XCircle } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { useToast } from '../hooks/use-toast';

function AuthCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const { toast } = useToast();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const [hasProcessed, setHasProcessed] = useState(false);

  useEffect(() => {
    const handleCallback = async () => {
      // Prevent multiple calls
      if (hasProcessed) return;
      setHasProcessed(true);
      
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      if (error) {
        setStatus('error');
        setMessage('Authentication was cancelled or failed.');
        toast({
          title: 'Authentication Failed',
          description: 'Please try signing in again.',
          variant: 'destructive',
        });
        
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      if (!code) {
        setStatus('error');
        setMessage('No authorization code received.');
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      try {
        await login(code, state || undefined);
        setStatus('success');
        setMessage('Successfully signed in! Redirecting to dashboard...');
        
        toast({
          title: 'Welcome!',
          description: 'You have been successfully signed in.',
        });
        
        setTimeout(() => navigate('/'), 2000);
      } catch (error) {
        console.error('Login failed:', error);
        setStatus('error');
        setMessage('Failed to complete sign in. Please try again.');
        
        toast({
          title: 'Sign In Failed',
          description: 'There was an error completing your sign in. Please try again.',
          variant: 'destructive',
        });
        
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    handleCallback();
  }, [searchParams]); // Remove login, navigate, toast from dependencies

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center">
      <div className="max-w-md mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white shadow rounded-lg p-8 text-center"
        >
          {status === 'loading' && (
            <>
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Completing Sign In...
              </h2>
              <p className="text-gray-600">
                Please wait while we authenticate your account.
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2 }}
                className="h-12 w-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4"
              >
                <CheckCircle className="h-8 w-8 text-green-600" />
              </motion.div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Sign In Successful!
              </h2>
              <p className="text-gray-600">{message}</p>
            </>
          )}

          {status === 'error' && (
            <>
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2 }}
                className="h-12 w-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4"
              >
                <XCircle className="h-8 w-8 text-red-600" />
              </motion.div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Sign In Failed
              </h2>
              <p className="text-gray-600 mb-4">{message}</p>
              <button
                onClick={() => navigate('/login')}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Try Again
              </button>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}

export default AuthCallbackPage;
