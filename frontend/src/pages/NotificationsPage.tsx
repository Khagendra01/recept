import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { useAutoRefresh } from '../hooks/use-auto-refresh';
import { 
  Search, 
  Filter, 
  Calendar,
  Tag,
  DollarSign,
  Mail,
  CheckCircle,
  Clock,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';
import { transactionsApi, emailsApi } from '../lib/api';
import TransactionTable from '../components/TransactionTable';

interface Filters {
  search: string;
  category: string;
  dateFrom: string;
  dateTo: string;
  amountMin: string;
  amountMax: string;
}

function NotificationsPage() {
  // Enable automatic data refresh
  useAutoRefresh();
  
  const [filters, setFilters] = useState<Filters>({
    search: '',
    category: '',
    dateFrom: '',
    dateTo: '',
    amountMin: '',
    amountMax: '',
  });
  const [showFilters, setShowFilters] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  // Fetch transactions with filters and auto-refresh
  const { data: transactionsData, isLoading: loadingTransactions, refetch, isFetching: fetchingTransactions } = useQuery({
    queryKey: ['transactions', filters, currentPage],
    queryFn: () => transactionsApi.getTransactions({
      skip: (currentPage - 1) * itemsPerPage,
      limit: itemsPerPage,
      search: filters.search || undefined,
      category: filters.category || undefined,
      date_from: filters.dateFrom || undefined,
      date_to: filters.dateTo || undefined,
    }),
    refetchInterval: 30000, // Refresh every 30 seconds
    refetchIntervalInBackground: true,
  });

  // Fetch categories for filter dropdown
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => transactionsApi.getCategories(),
    refetchInterval: 60000, // Refresh every minute
    refetchIntervalInBackground: true,
  });

  // Fetch email stats with auto-refresh
  const { data: emailStats, isFetching: fetchingStats } = useQuery({
    queryKey: ['email-stats'],
    queryFn: () => emailsApi.getEmailStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
    refetchIntervalInBackground: true,
  });

  const transactions = transactionsData?.data?.transactions || [];
  const totalTransactions = transactionsData?.data?.total || 0;
  const totalPages = Math.ceil(totalTransactions / itemsPerPage);
  const categories = categoriesData?.data || [];
  const stats = emailStats?.data || {};

  const handleFilterChange = (key: keyof Filters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1); // Reset to first page when filters change
  };

  const clearFilters = () => {
    setFilters({
      search: '',
      category: '',
      dateFrom: '',
      dateTo: '',
      amountMin: '',
      amountMax: '',
    });
    setCurrentPage(1);
  };

  const statsCards = [
    {
      title: 'Total Emails',
      value: stats.total_emails || 0,
      icon: Mail,
      color: 'bg-blue-500',
    },
    {
      title: 'With Receipts',
      value: stats.emails_with_receipts || 0,
      icon: CheckCircle,
      color: 'bg-green-500',
    },
    {
      title: 'Processed',
      value: stats.processed_emails || 0,
      icon: CheckCircle,
      color: 'bg-purple-500',
    },
    {
      title: 'Pending',
      value: stats.pending_emails || 0,
      icon: Clock,
      color: 'bg-yellow-500',
    },
    {
      title: 'Failed',
      value: stats.failed_emails || 0,
      icon: AlertTriangle,
      color: 'bg-red-500',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">All Notifications</h1>
          <p className="text-gray-500 mt-1">
            View and search all your processed transactions
          </p>
        </div>
        <div className="mt-4 sm:mt-0 flex space-x-3">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </button>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
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
                  <div className={`h-8 w-8 rounded-lg ${stat.color} flex items-center justify-center`}>
                    <stat.icon className="h-5 w-5 text-white" />
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

      {/* Search and Filters */}
      <div className="bg-white shadow rounded-lg p-6">
        {/* Search Bar */}
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            placeholder="Search transactions by merchant, description, or email..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Advanced Filters */}
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4 pt-4 border-t border-gray-200"
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {/* Category Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category
                </label>
                <select
                  value={filters.category}
                  onChange={(e) => handleFilterChange('category', e.target.value)}
                  className="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All categories</option>
                  {categories.map(category => (
                    <option key={category} value={category}>
                      {category.charAt(0).toUpperCase() + category.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date From */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Date From
                </label>
                <input
                  type="date"
                  value={filters.dateFrom}
                  onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
                  className="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Date To */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Date To
                </label>
                <input
                  type="date"
                  value={filters.dateTo}
                  onChange={(e) => handleFilterChange('dateTo', e.target.value)}
                  className="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Clear Filters */}
              <div className="flex items-end">
                <button
                  onClick={clearFilters}
                  className="w-full px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                >
                  Clear Filters
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-700">
          Showing <span className="font-medium">{(currentPage - 1) * itemsPerPage + 1}</span> to{' '}
          <span className="font-medium">
            {Math.min(currentPage * itemsPerPage, totalTransactions)}
          </span>{' '}
          of <span className="font-medium">{totalTransactions}</span> transactions
        </p>
      </div>

      {/* Transactions Table */}
      <div className="bg-white shadow rounded-lg">
        <TransactionTable
          transactions={transactions}
          loading={loadingTransactions}
          showPagination={false}
        />
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6 rounded-lg">
          <div className="flex flex-1 justify-between sm:hidden">
            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
          <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-700">
                Page <span className="font-medium">{currentPage}</span> of{' '}
                <span className="font-medium">{totalPages}</span>
              </p>
            </div>
            <div>
              <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="relative inline-flex items-center rounded-l-md border border-gray-300 bg-white px-2 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 focus:z-20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                
                {/* Page numbers */}
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const pageNum = i + 1;
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`relative inline-flex items-center border px-4 py-2 text-sm font-medium focus:z-20 ${
                        currentPage === pageNum
                          ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                          : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="relative inline-flex items-center rounded-r-md border border-gray-300 bg-white px-2 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50 focus:z-20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </nav>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationsPage;
