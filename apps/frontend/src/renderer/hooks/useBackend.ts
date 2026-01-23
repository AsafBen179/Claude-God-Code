/**
 * Backend Communication Hook
 *
 * Part of Claude God Code - Autonomous Excellence
 */

import { useState, useEffect, useCallback } from 'react';
import type { BackendStatus } from '../../shared/types';

interface BackendState {
  status: BackendStatus | null;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  lastPing: Date | null;
}

export function useBackend() {
  const [state, setState] = useState<BackendState>({
    status: null,
    isConnected: false,
    isLoading: false,
    error: null,
    lastPing: null,
  });

  const ping = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await window.electronAPI.backend.ping();

      if (response.success && response.data) {
        setState({
          status: response.data,
          isConnected: response.data.connected,
          isLoading: false,
          error: null,
          lastPing: new Date(),
        });
        return response.data;
      } else {
        setState((prev) => ({
          ...prev,
          isConnected: false,
          isLoading: false,
          error: response.error || 'Failed to ping backend',
        }));
        return null;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setState((prev) => ({
        ...prev,
        isConnected: false,
        isLoading: false,
        error: message,
      }));
      return null;
    }
  }, []);

  const getStatus = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await window.electronAPI.backend.status();

      if (response.success && response.data) {
        setState((prev) => ({
          ...prev,
          status: response.data,
          isConnected: response.data.connected,
          isLoading: false,
          error: null,
        }));
        return response.data;
      } else {
        setState((prev) => ({
          ...prev,
          isConnected: false,
          isLoading: false,
          error: response.error || 'Failed to get status',
        }));
        return null;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setState((prev) => ({
        ...prev,
        isConnected: false,
        isLoading: false,
        error: message,
      }));
      return null;
    }
  }, []);

  // Initial ping on mount
  useEffect(() => {
    ping();
  }, [ping]);

  return {
    ...state,
    ping,
    getStatus,
  };
}
