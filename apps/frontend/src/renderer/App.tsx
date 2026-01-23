/**
 * Main Application Component
 *
 * Part of Claude God Code - Autonomous Excellence
 */

import { useState, useEffect } from 'react';
import { useBackend } from './hooks/useBackend';

function App() {
  const { status, isConnected, isLoading, error, lastPing, ping, getStatus } = useBackend();
  const [appVersion, setAppVersion] = useState<string>('');

  useEffect(() => {
    window.electronAPI.app.getVersion().then((response) => {
      if (response.success && response.data) {
        setAppVersion(response.data);
      }
    });
  }, []);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-god-dark-700/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-god-primary-500 to-god-accent-500 flex items-center justify-center">
            <span className="text-white font-bold text-lg">C</span>
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gradient">Claude God Code</h1>
            <p className="text-xs text-god-dark-400">Autonomous Excellence</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div
              className={`status-dot ${
                isConnected
                  ? 'status-connected'
                  : isLoading
                    ? 'status-pending'
                    : 'status-disconnected'
              }`}
            />
            <span className="text-sm text-god-dark-300">
              {isConnected ? 'Connected' : isLoading ? 'Connecting...' : 'Disconnected'}
            </span>
          </div>
          {appVersion && (
            <span className="text-xs text-god-dark-500">v{appVersion}</span>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 overflow-auto">
        <div className="max-w-2xl mx-auto space-y-6">
          {/* Status Card */}
          <div className="card p-6">
            <h2 className="text-lg font-medium text-god-dark-100 mb-4">Backend Status</h2>

            {error && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}

            <div className="space-y-3">
              <div className="flex justify-between items-center py-2 border-b border-god-dark-700/50">
                <span className="text-god-dark-400">Connection</span>
                <span
                  className={`font-medium ${isConnected ? 'text-green-400' : 'text-red-400'}`}
                >
                  {isConnected ? 'Active' : 'Inactive'}
                </span>
              </div>

              {status && (
                <>
                  <div className="flex justify-between items-center py-2 border-b border-god-dark-700/50">
                    <span className="text-god-dark-400">Version</span>
                    <span className="text-god-dark-100">{status.version}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-god-dark-700/50">
                    <span className="text-god-dark-400">Python</span>
                    <span className="text-god-dark-100">{status.pythonVersion}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-god-dark-700/50">
                    <span className="text-god-dark-400">Active Sessions</span>
                    <span className="text-god-dark-100">{status.activeSessions}</span>
                  </div>
                </>
              )}

              {lastPing && (
                <div className="flex justify-between items-center py-2">
                  <span className="text-god-dark-400">Last Ping</span>
                  <span className="text-god-dark-100">{lastPing.toLocaleTimeString()}</span>
                </div>
              )}
            </div>

            <div className="mt-6 flex gap-3">
              <button
                onClick={ping}
                disabled={isLoading}
                className="btn btn-primary flex-1"
              >
                {isLoading ? 'Pinging...' : 'Ping Backend'}
              </button>
              <button
                onClick={getStatus}
                disabled={isLoading}
                className="btn btn-secondary flex-1"
              >
                Refresh Status
              </button>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="card p-6">
            <h2 className="text-lg font-medium text-god-dark-100 mb-4">Quick Actions</h2>
            <div className="grid grid-cols-2 gap-3">
              <button className="btn btn-secondary text-left p-4 h-auto flex flex-col items-start">
                <span className="text-god-dark-100 font-medium">Sessions</span>
                <span className="text-xs text-god-dark-400 mt-1">View active sessions</span>
              </button>
              <button className="btn btn-secondary text-left p-4 h-auto flex flex-col items-start">
                <span className="text-god-dark-100 font-medium">Specs</span>
                <span className="text-xs text-god-dark-400 mt-1">Browse specifications</span>
              </button>
              <button className="btn btn-secondary text-left p-4 h-auto flex flex-col items-start">
                <span className="text-god-dark-100 font-medium">QA</span>
                <span className="text-xs text-god-dark-400 mt-1">Run quality checks</span>
              </button>
              <button className="btn btn-secondary text-left p-4 h-auto flex flex-col items-start">
                <span className="text-god-dark-100 font-medium">Settings</span>
                <span className="text-xs text-god-dark-400 mt-1">Configure options</span>
              </button>
            </div>
          </div>

          {/* Info */}
          <div className="text-center text-god-dark-500 text-sm">
            <p>Claude God Code - Autonomous AI Development</p>
            <p className="mt-1">Powered by Claude</p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
