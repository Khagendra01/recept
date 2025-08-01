import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { useLocation } from 'react-router-dom';
import { useAutoRefresh } from '../hooks/use-auto-refresh';
import { 
  CheckCircle, 
  AlertTriangle, 
  XCircle,
  TrendingUp,
  DollarSign,
  BarChart3,
  RefreshCw
} from 'lucide-react';
import { bankTransactionsApi, TransactionMatch } from '../lib/api';
import ComparisonTable from '../components/ComparisonTable';
import { useToast } from '../hooks/use-toast';
import { useQueryClient } from '@tanstack/react-query';

type ComparisonView = 'matched' | 'ledger_only' | 'bank_only';

function ComparePage() {
  // Enable automatic data refresh
  useAutoRefresh();
  
  const [activeView, setActiveView] = useState<ComparisonView>('matched');
  const location = useLocation();
  const fromUpload = location.state?.fromUpload;
  const uploadCount = location.state?.uploadCount;
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch comparison data with auto-refresh and better synchronization
  const { data: comparisonData, isLoading, refetch, isFetching: fetchingComparison } = useQuery({
    queryKey: ['comparison'],
    queryFn: () => bankTransactionsApi.compareTransactions(),
    refetchInterval: 30000, // Refresh every 30 seconds
    refetchIntervalInBackground: true,
    staleTime: 0, // Always consider data stale to ensure fresh data
    refetchOnMount: true, // Always refetch when component mounts
    refetchOnWindowFocus: true, // Refetch when window gains focus
  });

  // Force refetch when component mounts to ensure fresh data after CSV upload
  useEffect(() => {
    refetch();
  }, [refetch]);

  // Clear location state after showing welcome message
  useEffect(() => {
    if (fromUpload) {
      // Clear the state after 5 seconds
      const timer = setTimeout(() => {
        window.history.replaceState({}, document.title);
      }, 5000);
      
      return () => clearTimeout(timer);
    }
  }, [fromUpload]);

  const handleSampleComparison = async () => {
    try {
      await bankTransactionsApi.generateSampleComparison();
      toast({
        title: 'Sample Comparison Generated',
        description: 'Sample comparison data has been created with 8-10 transactions where 3 should match.',
      });
      // Refetch the comparison data and related queries
      await Promise.all([
        refetch(),
        queryClient.invalidateQueries({ queryKey: ['transaction-summary'] }),
        queryClient.invalidateQueries({ queryKey: ['recent-transactions'] }),
        queryClient.invalidateQueries({ queryKey: ['transactions'] }),
      ]);
    } catch (error: any) {
      toast({
        title: 'Sample Comparison Failed',
        description: error.response?.data?.detail || 'Failed to generate sample comparison data. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const comparison = comparisonData?.data || {
    matched: [],
    ledger_only: [],
    bank_only: [],
    summary: {
      total_ledger: 0,
      total_bank: 0,
      matched_count: 0,
      ledger_only_count: 0,
      bank_only_count: 0,
      match_percentage: 0,
    },
  };

  const summary = comparison.summary;

  const viewTabs = [
    {
      id: 'matched' as const,
      name: 'Matched',
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      count: summary.matched_count,
    },
    {
      id: 'ledger_only' as const,
      name: 'Ledger Only',
      icon: AlertTriangle,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
      count: summary.ledger_only_count,
    },
    {
      id: 'bank_only' as const,
      name: 'Bank Only',
      icon: XCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      count: summary.bank_only_count,
    },
  ];

  const getCurrentData = (): TransactionMatch[] => {
    switch (activeView) {
      case 'matched':
        return comparison.matched;
      case 'ledger_only':
        return comparison.ledger_only;
      case 'bank_only':
        return comparison.bank_only;
      default:
        return [];
    }
  };

  const statsCards = [
    {
      title: 'Match Rate',
      value: `${summary.match_percentage.toFixed(1)}%`,
      icon: TrendingUp,
      color: 'bg-blue-500',
    },
    {
      title: 'Ledger Transactions',
      value: summary.total_ledger,
      icon: BarChart3,
      color: 'bg-purple-500',
    },
    {
      title: 'Bank Transactions',
      value: summary.total_bank,
      icon: DollarSign,
      color: 'bg-green-500',
    },
    {
      title: 'Perfect Matches',
      value: summary.matched_count,
      icon: CheckCircle,
      color: 'bg-emerald-500',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome Message from Upload */}
      {fromUpload && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-green-50 border border-green-200 rounded-lg p-4"
        >
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-green-800">
                CSV Upload Successful!
              </h3>
              <p className="text-sm text-green-700">
                {uploadCount} transactions were imported. The comparison data is being updated...
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Transaction Comparison</h1>
          <p className="text-gray-500 mt-1">
            Compare your ledger transactions with bank statement data
          </p>
        </div>
        <button
          onClick={handleSampleComparison}
          disabled={isLoading}
          className="mt-4 sm:mt-0 inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Send Sample Compare
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statsCards.map((stat, index) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="bg-white overflow-hidden shadow rounded-lg"
          >
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className={`h-10 w-10 rounded-lg ${stat.color} flex items-center justify-center`}>
                    <stat.icon className="h-6 w-6 text-white" />
                  </div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      {stat.title}
                    </dt>
                    <dd className="text-lg font-semibold text-gray-900">
                      {stat.value}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Tabs Navigation */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6" aria-label="Tabs">
            {viewTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveView(tab.id)}
                className={`group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm ${
                  activeView === tab.id
                    ? `border-blue-500 ${tab.color}`
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <tab.icon
                  className={`mr-2 h-5 w-5 ${
                    activeView === tab.id ? tab.color : 'text-gray-400 group-hover:text-gray-500'
                  }`}
                />
                {tab.name}
                {tab.count > 0 && (
                  <span
                    className={`ml-2 py-0.5 px-2.5 rounded-full text-xs font-medium ${
                      activeView === tab.id
                        ? 'bg-blue-100 text-blue-600'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {isLoading || fetchingComparison ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-500">
                {isLoading ? 'Loading comparison data...' : 'Refreshing comparison data...'}
              </p>
              {fetchingComparison && (
                <p className="text-xs text-gray-400 mt-2">
                  Syncing with latest data...
                </p>
              )}
            </div>
          ) : (
            <ComparisonTable
              matches={getCurrentData()}
              viewType={activeView}
            />
          )}
        </div>
      </div>

      {/* Help Text */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className="h-6 w-6 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-blue-600 text-sm font-bold">?</span>
            </div>
          </div>
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">How Transaction Matching Works:</p>
            <ul className="space-y-1 text-blue-700">
              <li>• <strong>Matched:</strong> Transactions found in both your receipts and bank statement</li>
              <li>• <strong>Ledger Only:</strong> Receipts with no corresponding bank transaction</li>
              <li>• <strong>Bank Only:</strong> Bank transactions with no matching receipt</li>
            </ul>
            <p className="mt-2 text-blue-700">
              Upload your bank statement CSV to see a complete comparison.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ComparePage;
