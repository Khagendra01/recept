import React from 'react';
import { motion } from 'framer-motion';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAutoRefresh } from '../hooks/use-auto-refresh';
import { 
  Mail, 
  TrendingUp, 
  DollarSign, 
  Calendar, 
  Upload,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Info,
  RotateCcw
} from 'lucide-react';
import { transactionsApi, authApi, bankTransactionsApi, User } from '../lib/api';
import { useAuth } from '../lib/auth';
import { useToast } from '../hooks/use-toast';
import TransactionTable from '../components/TransactionTable';
import CSVUploader from '../components/CSVUploader';
import WelcomeMessage from '../components/WelcomeMessage';

function DashboardPage() {
  const { user, refreshUser } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  // Enable automatic data refresh
  useAutoRefresh();

  // Fetch transaction summary with auto-refresh
  const { data: summary, isFetching: fetchingSummary } = useQuery({
    queryKey: ['transaction-summary'],
    queryFn: () => transactionsApi.getTransactionSummary(),
    refetchInterval: 30000, // Refresh every 30 seconds
    refetchIntervalInBackground: true,
  });

  // Fetch recent transactions with auto-refresh
  const { data: recentTransactions, isLoading: loadingTransactions, isFetching: fetchingTransactions } = useQuery({
    queryKey: ['recent-transactions'],
    queryFn: () => transactionsApi.getRecentTransactions(15),
    refetchInterval: 30000, // Refresh every 30 seconds
    refetchIntervalInBackground: true,
  });

  // Fetch Gmail status with auto-refresh
  const { data: gmailStatus, refetch: refetchGmailStatus, isFetching: fetchingGmail } = useQuery({
    queryKey: ['gmail-status'],
    queryFn: () => authApi.getGmailStatus(),
    refetchInterval: 30000, // Refresh every 30 seconds
    refetchIntervalInBackground: true,
  });

  const handleSampleDataGeneration = async () => {
    try {
      await bankTransactionsApi.generateSampleData();
      toast({
        title: 'Sample Data Generated',
        description: 'Sample ledger transactions have been created for demonstration.',
      });
      // Invalidate and refetch all relevant queries
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['transaction-summary'] }),
        queryClient.invalidateQueries({ queryKey: ['recent-transactions'] }),
        queryClient.invalidateQueries({ queryKey: ['transactions'] }),
        refreshUser(), // Refresh user data as well
      ]);
    } catch (error: any) {
      toast({
        title: 'Sample Data Generation Failed',
        description: error.response?.data?.detail || 'Failed to generate sample data. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleRefreshData = async () => {
    try {
      toast({
        title: 'Refreshing Data',
        description: 'Updating your dashboard with the latest information.',
      });
      // Invalidate and refetch all relevant queries
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['gmail-status'] }),
        queryClient.invalidateQueries({ queryKey: ['transaction-summary'] }),
        queryClient.invalidateQueries({ queryKey: ['recent-transactions'] }),
        refreshUser(), // Refresh user data as well
      ]);
      toast({
        title: 'Data Refreshed',
        description: 'Your dashboard has been updated with the latest data.',
      });
    } catch (error) {
      toast({
        title: 'Refresh Failed',
        description: 'Failed to refresh data. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const summaryData = summary?.data || {};
  const transactions = recentTransactions?.data || [];
  const gmail = gmailStatus?.data || {};

  const stats = [
    {
      title: 'Total Transactions',
      value: summaryData.total_transactions || 0,
      icon: TrendingUp,
      color: 'bg-blue-500',
      change: `+${summaryData.month_transactions || 0} this month`,
    },
    {
      title: 'Total Amount',
      value: `$${(summaryData.total_amount || 0).toFixed(2)}`,
      icon: DollarSign,
      color: 'bg-green-500',
      change: `$${(summaryData.month_amount || 0).toFixed(2)} this month`,
    },
    {
      title: 'Emails Processed',
      value: gmail.total_emails || 0,
      icon: Mail,
      color: 'bg-purple-500',
      change: gmail.connected ? 'Connected' : 'Not connected',
    },
    {
      title: 'Last Sync',
      value: gmail.last_sync ? new Date(gmail.last_sync).toLocaleDateString() : 'Never',
      icon: Calendar,
      color: 'bg-orange-500',
      change: gmail.connected ? 'Active' : 'Inactive',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome Message */}
      <div className="flex items-center justify-between">
        <WelcomeMessage 
          user={user} 
          gmailStatus={gmail} 
          onGmailSync={refetchGmailStatus}
        />
        <div className="flex items-center space-x-2">
          {/* Auto-refresh indicator */}
          {(fetchingSummary || fetchingTransactions || fetchingGmail) && (
            <div className="flex items-center text-sm text-gray-500">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              <span>Updating...</span>
            </div>
          )}
          <button
            onClick={handleRefreshData}
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            title="Refresh dashboard data"
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="bg-white shadow rounded-lg p-6"
          >
            <div className="flex items-center">
              <div className={`h-10 w-10 ${stat.color} rounded-lg flex items-center justify-center`}>
                <stat.icon className="h-6 w-6 text-white" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    {stat.title}
                  </dt>
                  <dd className="text-lg font-semibold text-gray-900">
                    {stat.value}
                  </dd>
                  <dd className="text-sm text-gray-600">
                    {stat.change}
                  </dd>
                </dl>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Sample Data Generation Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-white shadow rounded-lg p-6"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Mail className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900">
                Sample Data Generation
              </h3>
              <p className="text-sm text-gray-500">
                Generate sample bank transactions for demonstration
              </p>
            </div>
          </div>
          <button
            onClick={handleSampleDataGeneration}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Send Sample Response
          </button>
        </div>
      </motion.div>

      {/* Recent Transactions and CSV Upload */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Transactions */}
        <div className="lg:col-span-2">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-white shadow rounded-lg"
          >
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                Recent Transactions
              </h3>
              <p className="text-sm text-gray-500">
                Your latest processed receipts
              </p>
            </div>
            <div className="p-6">
              <TransactionTable 
                transactions={transactions}
                loading={loadingTransactions}
                showPagination={false}
              />
            </div>
          </motion.div>
        </div>

        {/* CSV Upload */}
        <div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="bg-white shadow rounded-lg p-6"
          >
            <div className="flex items-center space-x-3 mb-4">
              <div className="h-10 w-10 bg-green-100 rounded-lg flex items-center justify-center">
                <Upload className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900">
                  Upload Bank Statement
                </h3>
                <p className="text-sm text-gray-500">
                  Compare with your receipts
                </p>
              </div>
            </div>
            <CSVUploader />
          </motion.div>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
