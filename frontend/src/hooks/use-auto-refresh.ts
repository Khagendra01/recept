import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export function useAutoRefresh() {
  const queryClient = useQueryClient();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastRefreshRef = useRef<number>(Date.now());

  useEffect(() => {
    // Set up automatic refresh every 30 seconds
    intervalRef.current = setInterval(() => {
      const now = Date.now();
      const timeSinceLastRefresh = now - lastRefreshRef.current;
      
      // Only refresh if it's been at least 25 seconds since last refresh
      if (timeSinceLastRefresh >= 25000) {
        // Invalidate all dashboard-related queries
        queryClient.invalidateQueries({ queryKey: ['transaction-summary'] });
        queryClient.invalidateQueries({ queryKey: ['recent-transactions'] });
        queryClient.invalidateQueries({ queryKey: ['gmail-status'] });
        queryClient.invalidateQueries({ queryKey: ['comparison'] });
        queryClient.invalidateQueries({ queryKey: ['email-stats'] });
        lastRefreshRef.current = now;
      }
    }, 30000); // 30 seconds

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [queryClient]);

  // Also refresh when window becomes visible (user comes back to tab)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // User came back to the tab, refresh data
        queryClient.invalidateQueries({ queryKey: ['transaction-summary'] });
        queryClient.invalidateQueries({ queryKey: ['recent-transactions'] });
        queryClient.invalidateQueries({ queryKey: ['gmail-status'] });
        queryClient.invalidateQueries({ queryKey: ['comparison'] });
        queryClient.invalidateQueries({ queryKey: ['email-stats'] });
        lastRefreshRef.current = Date.now();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [queryClient]);
} 