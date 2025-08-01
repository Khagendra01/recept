import React from 'react';
import { motion } from 'framer-motion';
import { Calendar, DollarSign, Tag, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';
import { TransactionMatch } from '../lib/api';

interface ComparisonTableProps {
  matches: TransactionMatch[];
  viewType: 'matched' | 'ledger_only' | 'bank_only';
}

function ComparisonTable({ matches, viewType }: ComparisonTableProps) {
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  const formatAmount = (amount?: number, currency = 'USD') => {
    if (amount === undefined || amount === null) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(Math.abs(amount));
  };

  const getConfidenceColor = (confidence?: number) => {
    if (!confidence) return 'text-gray-500';
    if (confidence >= 0.9) return 'text-green-600';
    if (confidence >= 0.7) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceIcon = (confidence?: number) => {
    if (!confidence) return null;
    if (confidence >= 0.9) return <CheckCircle className="h-4 w-4 text-green-600" />;
    if (confidence >= 0.7) return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
    return <AlertTriangle className="h-4 w-4 text-red-600" />;
  };

  const getCategoryColor = (category?: string) => {
    const colors: Record<string, string> = {
      food: 'bg-orange-100 text-orange-800',
      travel: 'bg-blue-100 text-blue-800',
      shopping: 'bg-purple-100 text-purple-800',
      gas: 'bg-yellow-100 text-yellow-800',
      entertainment: 'bg-pink-100 text-pink-800',
      healthcare: 'bg-red-100 text-red-800',
      utilities: 'bg-green-100 text-green-800',
      other: 'bg-gray-100 text-gray-800',
    };
    return colors[category?.toLowerCase() || 'other'] || colors.other;
  };

  if (matches.length === 0) {
    const emptyMessages = {
      matched: 'No matched transactions found. Upload a bank statement CSV to see matches.',
      ledger_only: 'All receipt transactions have been matched with bank records.',
      bank_only: 'All bank transactions have been matched with receipts.',
    };

    return (
      <div className="text-center py-12">
        <TrendingUp className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No {viewType.replace('_', ' ')} transactions
        </h3>
        <p className="text-gray-500">
          {emptyMessages[viewType]}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Mobile view */}
      <div className="block sm:hidden space-y-4">
        {matches.map((match, index) => {
          const ledger = match.ledger_transaction;
          const bank = match.bank_transaction;
          
          return (
            <motion.div
              key={`${ledger?.id || ''}-${bank?.id || ''}-${index}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm"
            >
              {viewType === 'matched' && ledger && bank && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-gray-900">Matched Transaction</h4>
                    <div className="flex items-center space-x-1">
                      {getConfidenceIcon(match.confidence)}
                      <span className={`text-sm ${getConfidenceColor(match.confidence)}`}>
                        {match.confidence ? `${(match.confidence * 100).toFixed(0)}%` : 'N/A'}
                      </span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="font-medium text-gray-700">Receipt</p>
                      <p className="text-gray-900">{ledger.merchant_name || 'Unknown'}</p>
                      <p className="text-gray-500">{formatDate(ledger.transaction_date)}</p>
                      <p className="font-semibold">{formatAmount(ledger.amount)}</p>
                    </div>
                    <div>
                      <p className="font-medium text-gray-700">Bank</p>
                      <p className="text-gray-900">{bank.merchant_name || bank.description || 'Unknown'}</p>
                      <p className="text-gray-500">{formatDate(bank.date)}</p>
                      <p className="font-semibold">{formatAmount(bank.amount)}</p>
                    </div>
                  </div>
                </div>
              )}
              
              {viewType === 'ledger_only' && ledger && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Receipt Only</h4>
                  <p className="text-gray-900">{ledger.merchant_name || 'Unknown Merchant'}</p>
                  <p className="text-gray-500">{formatDate(ledger.transaction_date)}</p>
                  <p className="font-semibold">{formatAmount(ledger.amount)}</p>
                  {ledger.category && (
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium mt-2 ${getCategoryColor(ledger.category)}`}>
                      {ledger.category}
                    </span>
                  )}
                </div>
              )}
              
              {viewType === 'bank_only' && bank && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Bank Only</h4>
                  <p className="text-gray-900">{bank.merchant_name || bank.description || 'Unknown'}</p>
                  <p className="text-gray-500">{formatDate(bank.date)}</p>
                  <p className="font-semibold">{formatAmount(bank.amount)}</p>
                  {bank.category && (
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium mt-2 ${getCategoryColor(bank.category)}`}>
                      {bank.category}
                    </span>
                  )}
                </div>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Desktop view */}
      <div className="hidden sm:block overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
        <table className="min-w-full divide-y divide-gray-300">
          <thead className="bg-gray-50">
            <tr>
              {viewType === 'matched' && (
                <>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Confidence
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Receipt Transaction
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Bank Transaction
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount Difference
                  </th>
                </>
              )}
              
              {(viewType === 'ledger_only' || viewType === 'bank_only') && (
                <>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center space-x-1">
                      <Calendar className="h-4 w-4" />
                      <span>Date</span>
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Merchant/Description
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center space-x-1">
                      <DollarSign className="h-4 w-4" />
                      <span>Amount</span>
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center space-x-1">
                      <Tag className="h-4 w-4" />
                      <span>Category</span>
                    </div>
                  </th>
                </>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {matches.map((match, index) => {
              const ledger = match.ledger_transaction;
              const bank = match.bank_transaction;
              
              return (
                <motion.tr
                  key={`${ledger?.id || ''}-${bank?.id || ''}-${index}`}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="hover:bg-gray-50"
                >
                  {viewType === 'matched' && ledger && bank && (
                    <>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          {getConfidenceIcon(match.confidence)}
                          <span className={`text-sm font-medium ${getConfidenceColor(match.confidence)}`}>
                            {match.confidence ? `${(match.confidence * 100).toFixed(0)}%` : 'N/A'}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">
                          {ledger.merchant_name || 'Unknown Merchant'}
                        </div>
                        <div className="text-sm text-gray-500">
                          {formatDate(ledger.transaction_date)} • {formatAmount(ledger.amount)}
                        </div>
                        {ledger.category && (
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium mt-1 ${getCategoryColor(ledger.category)}`}>
                            {ledger.category}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">
                          {bank.merchant_name || bank.description || 'Unknown'}
                        </div>
                        <div className="text-sm text-gray-500">
                          {formatDate(bank.date)} • {formatAmount(bank.amount)}
                        </div>
                        {bank.category && (
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium mt-1 ${getCategoryColor(bank.category)}`}>
                            {bank.category}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        {ledger.amount && bank.amount && (
                          <span className={`${
                            Math.abs(ledger.amount - Math.abs(bank.amount)) < 0.01
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}>
                            {Math.abs(ledger.amount - Math.abs(bank.amount)) < 0.01
                              ? 'Perfect match'
                              : `$${Math.abs(ledger.amount - Math.abs(bank.amount)).toFixed(2)}`}
                          </span>
                        )}
                      </td>
                    </>
                  )}
                  
                  {viewType === 'ledger_only' && ledger && (
                    <>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatDate(ledger.transaction_date)}
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">
                          {ledger.merchant_name || 'Unknown Merchant'}
                        </div>
                        {ledger.description && (
                          <div className="text-sm text-gray-500 truncate max-w-xs">
                            {ledger.description}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                        {formatAmount(ledger.amount, ledger.currency)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {ledger.category ? (
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getCategoryColor(ledger.category)}`}>
                            {ledger.category}
                          </span>
                        ) : (
                          <span className="text-sm text-gray-400">N/A</span>
                        )}
                      </td>
                    </>
                  )}
                  
                  {viewType === 'bank_only' && bank && (
                    <>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatDate(bank.date)}
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">
                          {bank.merchant_name || 'Unknown'}
                        </div>
                        {bank.description && (
                          <div className="text-sm text-gray-500 truncate max-w-xs">
                            {bank.description}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                        {formatAmount(bank.amount)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {bank.category ? (
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getCategoryColor(bank.category)}`}>
                            {bank.category}
                          </span>
                        ) : (
                          <span className="text-sm text-gray-400">N/A</span>
                        )}
                      </td>
                    </>
                  )}
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ComparisonTable;
