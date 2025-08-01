import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion } from 'framer-motion';
import { Upload, FileText, CheckCircle, AlertCircle, X } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { bankTransactionsApi } from '../lib/api';
import { useToast } from '../hooks/use-toast';

interface UploadResult {
  batch_id: string;
  total_transactions: number;
  successful_imports: number;
  failed_imports: number;
  errors: string[];
}

function CSVUploader() {
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const uploadMutation = useMutation({
    mutationFn: (file: File) => bankTransactionsApi.uploadCSV(file),
    onSuccess: (response) => {
      const result = response.data;
      setUploadResult(result);
      
      if (result.successful_imports > 0) {
        toast({
          title: 'Upload Successful',
          description: `Successfully imported ${result.successful_imports} transactions. Redirecting to comparison...`,
        });
        
        // Invalidate all relevant queries to ensure data is fresh
        queryClient.invalidateQueries({ queryKey: ['bank-transactions'] });
        queryClient.invalidateQueries({ queryKey: ['comparison'] });
        queryClient.invalidateQueries({ queryKey: ['transactions'] });
        queryClient.invalidateQueries({ queryKey: ['transaction-summary'] });
        
        // Set redirecting state
        setIsRedirecting(true);
        
        // Wait a moment for queries to invalidate, then redirect
        setTimeout(() => {
          navigate('/compare', { state: { fromUpload: true, uploadCount: result.successful_imports } });
        }, 1500);
      }
      
      if (result.failed_imports > 0) {
        toast({
          title: 'Partial Upload',
          description: `${result.failed_imports} transactions failed to import.`,
          variant: 'destructive',
        });
      }
    },
    onError: (error: any) => {
      toast({
        title: 'Upload Failed',
        description: error.response?.data?.detail || 'Failed to upload CSV file.',
        variant: 'destructive',
      });
    },
  });

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.csv'],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024, // 10MB
    onDrop: (files) => {
      if (files.length > 0) {
        uploadMutation.mutate(files[0]);
      }
    },
  });

  const clearResult = () => {
    setUploadResult(null);
  };

  return (
    <div className="space-y-4">
      {!uploadResult ? (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors duration-200 ${
            isDragActive
              ? 'border-blue-400 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          } ${uploadMutation.isPending ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <input {...getInputProps()} disabled={uploadMutation.isPending} />
          
          {uploadMutation.isPending ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-3"
            >
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-sm text-gray-600">Processing your file...</p>
            </motion.div>
          ) : (
            <div className="space-y-3">
              <div className="h-12 w-12 bg-gray-100 rounded-lg flex items-center justify-center mx-auto">
                <Upload className="h-6 w-6 text-gray-400" />
              </div>
              
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {isDragActive ? 'Drop your CSV file here' : 'Upload Bank Statement'}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {isDragActive ? 'Release to upload' : 'Drag & drop or click to select'}
                </p>
              </div>
              
              <p className="text-xs text-gray-400">
                CSV files up to 10MB
              </p>
            </div>
          )}
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white border rounded-lg p-4"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 bg-green-100 rounded-lg flex items-center justify-center">
                {isRedirecting ? (
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-600"></div>
                ) : (
                  <CheckCircle className="h-6 w-6 text-green-600" />
                )}
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-900">
                  {isRedirecting ? 'Redirecting to Comparison...' : 'Upload Complete'}
                </h4>
                <p className="text-xs text-gray-500">
                  {isRedirecting ? 'Preparing your data for comparison' : `Batch ID: ${uploadResult.batch_id.substring(0, 8)}...`}
                </p>
              </div>
            </div>
            {!isRedirecting && (
              <button
                onClick={clearResult}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-center">
            <div>
              <div className="text-lg font-semibold text-green-600">
                {uploadResult.successful_imports}
              </div>
              <div className="text-xs text-gray-500">Imported</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-red-600">
                {uploadResult.failed_imports}
              </div>
              <div className="text-xs text-gray-500">Failed</div>
            </div>
          </div>
          
          {uploadResult.errors.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 text-yellow-500" />
                <span className="text-sm font-medium text-gray-900">
                  Import Errors:
                </span>
              </div>
              <div className="bg-gray-50 rounded-md p-2 max-h-32 overflow-y-auto">
                {uploadResult.errors.map((error, index) => (
                  <p key={index} className="text-xs text-gray-600">
                    {error}
                  </p>
                ))}
              </div>
            </div>
          )}
          
          {!isRedirecting ? (
            <button
              onClick={clearResult}
              className="w-full mt-4 px-4 py-2 text-sm text-blue-600 border border-blue-200 rounded-md hover:bg-blue-50 transition-colors duration-200"
            >
              Upload Another File
            </button>
          ) : (
            <div className="w-full mt-4 px-4 py-2 text-sm text-blue-600 border border-blue-200 rounded-md bg-blue-50 flex items-center justify-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              Redirecting...
            </div>
          )}
        </motion.div>
      )}
      
      {/* Help Text */}
      <div className="text-xs text-gray-500 space-y-1">
        <p><strong>Supported formats:</strong> CSV files from major banks</p>
        <p><strong>Common columns:</strong> Date, Description, Amount, Balance</p>
        <p><strong>File size limit:</strong> 10MB maximum</p>
      </div>
    </div>
  );
}

export default CSVUploader;
