import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { api } from '@/lib/api';

interface DuplicateGroup {
  group_id: string;
  transactions_count: number;
  ai_confidence: number;
  ai_reasoning: string;
  merged_transaction_id: number;
}

interface DuplicateSummary {
  total_transactions: number;
  duplicate_groups_found: number;
  transactions_merged: number;
  transactions_deleted: number;
  groups_processed: DuplicateGroup[];
}

interface MergedTransaction {
  id: number;
  description: string;
  amount: number;
  date: string;
  category: string;
  merchant_name: string;
}

interface DuplicateDetectionResult {
  message: string;
  summary: DuplicateSummary;
  merged_transactions: MergedTransaction[];
}

interface ComparisonResult {
  summary: {
    total_ledger: number;
    total_bank: number;
    matched_count: number;
    ledger_only_count: number;
    bank_only_count: number;
    match_percentage: number;
    duplicates_merged: number;
  };
  matched: Array<{
    ledger_transaction: any;
    bank_transaction: any;
    match_type: string;
    confidence: number;
  }>;
  ledger_only: any[];
  bank_only: any[];
}

export function DuplicateDetection() {
  const [isDetecting, setIsDetecting] = useState(false);
  const [isMatching, setIsMatching] = useState(false);
  const [duplicateResult, setDuplicateResult] = useState<DuplicateDetectionResult | null>(null);
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDetectDuplicates = async () => {
    setIsDetecting(true);
    setError(null);
    
    try {
      const response = await api.post('/bank-transactions/detect-duplicates');
      setDuplicateResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to detect duplicates');
    } finally {
      setIsDetecting(false);
    }
  };

  const handleImprovedMatching = async () => {
    setIsMatching(true);
    setError(null);
    
    try {
      const response = await api.get('/bank-transactions/compare-improved');
      setComparisonResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to perform improved matching');
    } finally {
      setIsMatching(false);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800';
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Duplicate Detection & AI Matching</h2>
          <p className="text-muted-foreground">
            Detect and merge duplicate transactions using AI-powered analysis
          </p>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              Duplicate Detection
            </CardTitle>
            <CardDescription>
              Find and merge duplicate transactions using AI analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button 
              onClick={handleDetectDuplicates} 
              disabled={isDetecting}
              className="w-full"
            >
              {isDetecting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Detecting Duplicates...
                </>
              ) : (
                'Detect Duplicates'
              )}
            </Button>

            {duplicateResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {duplicateResult.summary.total_transactions}
                    </div>
                    <div className="text-sm text-muted-foreground">Total Transactions</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {duplicateResult.summary.transactions_merged}
                    </div>
                    <div className="text-sm text-muted-foreground">Merged</div>
                  </div>
                </div>

                {duplicateResult.summary.groups_processed.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-semibold">AI Analysis Results:</h4>
                    {duplicateResult.summary.groups_processed.map((group) => (
                      <div key={group.group_id} className="border rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium">Group {group.group_id}</span>
                          <Badge className={getConfidenceColor(group.ai_confidence)}>
                            {group.ai_confidence.toFixed(2)} confidence
                          </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground mb-2">
                          {group.transactions_count} transactions
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {group.ai_reasoning}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="h-5 w-5" />
              AI-Enhanced Matching
            </CardTitle>
            <CardDescription>
              Compare transactions with improved AI-powered matching
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button 
              onClick={handleImprovedMatching} 
              disabled={isMatching}
              className="w-full"
            >
              {isMatching ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Matching Transactions...
                </>
              ) : (
                'Run AI Matching'
              )}
            </Button>

            {comparisonResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {comparisonResult.summary.matched_count}
                    </div>
                    <div className="text-sm text-muted-foreground">Matched</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {comparisonResult.summary.match_percentage.toFixed(1)}%
                    </div>
                    <div className="text-sm text-muted-foreground">Match Rate</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Match Progress</span>
                    <span className="text-sm font-medium">
                      {comparisonResult.summary.matched_count} / {comparisonResult.summary.total_ledger + comparisonResult.summary.total_bank}
                    </span>
                  </div>
                  <Progress 
                    value={comparisonResult.summary.match_percentage} 
                    className="h-2"
                  />
                </div>

                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div className="text-lg font-semibold text-blue-600">
                      {comparisonResult.summary.total_ledger}
                    </div>
                    <div className="text-xs text-muted-foreground">Ledger</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold text-orange-600">
                      {comparisonResult.summary.total_bank}
                    </div>
                    <div className="text-xs text-muted-foreground">Bank</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold text-green-600">
                      {comparisonResult.summary.duplicates_merged}
                    </div>
                    <div className="text-xs text-muted-foreground">Merged</div>
                  </div>
                </div>

                {comparisonResult.matched.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-semibold">Top Matches:</h4>
                    {comparisonResult.matched.slice(0, 3).map((match, index) => (
                      <div key={index} className="border rounded-lg p-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">
                            {match.ledger_transaction?.merchant_name || 'Unknown'} ↔ {match.bank_transaction?.description || 'Unknown'}
                          </span>
                          <Badge className={getConfidenceColor(match.confidence)}>
                            {(match.confidence * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          ${match.ledger_transaction?.amount} ↔ ${match.bank_transaction?.amount}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {duplicateResult?.merged_transactions && duplicateResult.merged_transactions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Merged Transactions</CardTitle>
            <CardDescription>
              Transactions that were successfully merged
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {duplicateResult.merged_transactions.map((tx) => (
                <div key={tx.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div>
                    <div className="font-medium">{tx.description}</div>
                    <div className="text-sm text-muted-foreground">
                      {tx.merchant_name} • {tx.category}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold">${tx.amount}</div>
                    <div className="text-sm text-muted-foreground">
                      {new Date(tx.date).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
} 