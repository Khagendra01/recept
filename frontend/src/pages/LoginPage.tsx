import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Shield, Zap, BarChart3 } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { authApi } from '../lib/api';
import { useToast } from '../hooks/use-toast';

function LoginPage() {
  const { isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleGoogleLogin = async () => {
    setLoading(true);
    try {
      const response = await authApi.getGoogleAuthUrl();
      const { authorization_url } = response.data;
      window.location.href = authorization_url;
    } catch (error) {
      console.error('Failed to get Google auth URL:', error);
      toast({
        title: 'Error',
        description: 'Failed to initialize Google login. Please try again.',
        variant: 'destructive',
      });
      setLoading(false);
    }
  };

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const features = [
    {
      icon: Mail,
      title: 'Gmail Integration',
      description: 'Automatically fetch and process receipt emails from your Gmail account.',
    },
    {
      icon: Zap,
      title: 'AI-Powered Extraction',
      description: 'Advanced AI extracts transaction data from PDF receipts with high accuracy.',
    },
    {
      icon: BarChart3,
      title: 'Smart Comparison',
      description: 'Compare ledger transactions with bank statements to identify discrepancies.',
    },
    {
      icon: Shield,
      title: 'Secure & Private',
      description: 'Your data is encrypted and processed securely with privacy in mind.',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <div className="flex min-h-screen">
        {/* Left side - Hero */}
        <div className="flex-1 flex flex-col justify-center px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="max-w-md mx-auto w-full"
          >
            {/* Logo */}
            <div className="flex items-center justify-center mb-8">
              <div className="h-12 w-12 bg-blue-600 rounded-xl flex items-center justify-center">
                <Mail className="h-7 w-7 text-white" />
              </div>
              <h1 className="ml-3 text-2xl font-bold text-gray-900">
                Receipt Processing
              </h1>
            </div>

            {/* Heading */}
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                Automate Your Receipt Processing
              </h2>
              <p className="text-lg text-gray-600">
                Transform your email receipts into organized financial data with AI-powered extraction and smart bank statement comparison.
              </p>
            </div>

            {/* Google Login Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleGoogleLogin}
              disabled={loading}
              className="w-full flex items-center justify-center px-4 py-3 border border-gray-300 rounded-lg shadow-sm bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-900"></div>
              ) : (
                <>
                  <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    />
                  </svg>
                  Continue with Google
                </>
              )}
            </motion.button>

            <p className="mt-4 text-sm text-gray-500 text-center">
              By signing in, you agree to our terms of service and privacy policy.
            </p>
          </motion.div>
        </div>

        {/* Right side - Features */}
        <div className="hidden lg:flex lg:flex-1 lg:flex-col lg:justify-center lg:px-8">
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="max-w-lg mx-auto"
          >
            <h3 className="text-2xl font-bold text-gray-900 mb-8">
              Why Choose Our Platform?
            </h3>
            
            <div className="space-y-6">
              {features.map((feature, index) => (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.4 + index * 0.1 }}
                  className="flex items-start space-x-4"
                >
                  <div className="flex-shrink-0">
                    <div className="h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <feature.icon className="h-6 w-6 text-blue-600" />
                    </div>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold text-gray-900 mb-1">
                      {feature.title}
                    </h4>
                    <p className="text-gray-600">
                      {feature.description}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
