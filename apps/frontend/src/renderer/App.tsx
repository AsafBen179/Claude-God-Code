/**
 * Main Application Component
 *
 * Claude God Code - Autonomous Excellence
 *
 * Professional design following frontend_design skill guidelines:
 * - Visual hierarchy with proper spacing (4px/8px grid)
 * - Glassmorphism aesthetic with subtle animations
 * - Full accessibility (ARIA labels, keyboard navigation)
 * - Semantic HTML structure
 */

import { useState, useEffect, useCallback } from 'react';
import { useBackend } from './hooks/useBackend';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Logo,
  ConnectionStatus,
  StatusBadge,
} from './components/ui';
import { cn } from './lib/utils';

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

  const handlePing = useCallback(() => {
    ping();
  }, [ping]);

  const handleRefresh = useCallback(() => {
    getStatus();
  }, [getStatus]);

  return (
    <div className="h-full flex flex-col bg-background noise">
      {/* Header */}
      <header
        className={cn(
          'flex items-center justify-between',
          'px-6 py-4',
          'border-b border-border/50',
          'glass-strong'
        )}
        role="banner"
      >
        <Logo size="md" showTagline animated={isConnected} />

        <div className="flex items-center gap-4">
          <ConnectionStatus isConnected={isConnected} isLoading={isLoading} />
          {appVersion && (
            <span className="text-2xs text-muted-foreground font-mono">
              v{appVersion}
            </span>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main
        className="flex-1 p-6 overflow-auto"
        role="main"
        aria-label="Dashboard content"
      >
        <div className="max-w-3xl mx-auto space-y-6 stagger-children">
          {/* Error Alert */}
          {error && (
            <div
              role="alert"
              className={cn(
                'flex items-start gap-3',
                'p-4 rounded-xl',
                'bg-danger/10 border border-danger/20',
                'text-danger text-sm',
                'animate-slide-up'
              )}
            >
              <svg
                className="w-5 h-5 shrink-0 mt-0.5"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
                  clipRule="evenodd"
                />
              </svg>
              <div>
                <p className="font-medium">Connection Error</p>
                <p className="text-danger/80 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Backend Status Card */}
          <Card variant="glow" padding="lg">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle as="h2">Backend Status</CardTitle>
                <StatusBadge
                  status={isLoading ? 'pending' : isConnected ? 'connected' : 'disconnected'}
                />
              </div>
              <CardDescription>
                Python backend connection and system information
              </CardDescription>
            </CardHeader>

            <CardContent>
              <div className="space-y-1" role="list" aria-label="Status details">
                <StatusRow
                  label="Connection"
                  value={isConnected ? 'Active' : 'Inactive'}
                  valueClass={isConnected ? 'text-success' : 'text-danger'}
                />

                {status && (
                  <>
                    <StatusRow label="Version" value={status.version} />
                    <StatusRow label="Python" value={status.pythonVersion || 'Unknown'} />
                    <StatusRow
                      label="Active Sessions"
                      value={String(status.activeSessions || 0)}
                    />
                  </>
                )}

                {lastPing && (
                  <StatusRow
                    label="Last Ping"
                    value={lastPing.toLocaleTimeString()}
                    valueClass="font-mono text-xs"
                  />
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 mt-6 pt-6 border-t border-border/50">
                <Button
                  variant="primary"
                  onClick={handlePing}
                  disabled={isLoading}
                  isLoading={isLoading}
                  className="flex-1"
                  aria-describedby="ping-description"
                >
                  Ping Backend
                </Button>
                <span id="ping-description" className="sr-only">
                  Test connection to the Python backend
                </span>

                <Button
                  variant="secondary"
                  onClick={handleRefresh}
                  disabled={isLoading}
                  className="flex-1"
                  aria-describedby="refresh-description"
                >
                  Refresh Status
                </Button>
                <span id="refresh-description" className="sr-only">
                  Refresh the current backend status
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions Grid */}
          <section aria-labelledby="quick-actions-title">
            <h2 id="quick-actions-title" className="sr-only">
              Quick Actions
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <ActionCard
                title="Sessions"
                description="View active sessions"
                icon={
                  <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M10 9a3 3 0 100-6 3 3 0 000 6zM6 8a2 2 0 11-4 0 2 2 0 014 0zM1.49 15.326a.78.78 0 01-.358-.442 3 3 0 014.308-3.516 6.484 6.484 0 00-1.905 3.959c-.023.222-.014.442.025.654a4.97 4.97 0 01-2.07-.655zM16.44 15.98a4.97 4.97 0 01-2.07.654 3.5 3.5 0 01.025-.654 6.484 6.484 0 00-1.905-3.959 3 3 0 014.308 3.516.78.78 0 01-.358.442zM18 8a2 2 0 11-4 0 2 2 0 014 0zM5.304 16.19a.844.844 0 01-.277-.71 5 5 0 019.947 0 .843.843 0 01-.277.71A6.975 6.975 0 0110 18a6.974 6.974 0 01-4.696-1.81z" />
                  </svg>
                }
              />
              <ActionCard
                title="Specs"
                description="Browse specifications"
                icon={
                  <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm2.25 8.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 3a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z"
                      clipRule="evenodd"
                    />
                  </svg>
                }
              />
              <ActionCard
                title="QA"
                description="Run quality checks"
                icon={
                  <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M16.403 12.652a3 3 0 000-5.304 3 3 0 00-3.75-3.751 3 3 0 00-5.305 0 3 3 0 00-3.751 3.75 3 3 0 000 5.305 3 3 0 003.75 3.751 3 3 0 005.305 0 3 3 0 003.751-3.75zm-2.546-4.46a.75.75 0 00-1.214-.883l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                      clipRule="evenodd"
                    />
                  </svg>
                }
              />
              <ActionCard
                title="Settings"
                description="Configure options"
                icon={
                  <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z"
                      clipRule="evenodd"
                    />
                  </svg>
                }
              />
            </div>
          </section>

          {/* Footer */}
          <footer className="text-center pt-4" role="contentinfo">
            <p className="text-sm text-muted-foreground">
              Claude God Code - Autonomous AI Development
            </p>
            <p className="text-xs text-muted-foreground/60 mt-1">
              Powered by Claude
            </p>
          </footer>
        </div>
      </main>
    </div>
  );
}

interface StatusRowProps {
  label: string;
  value: string;
  valueClass?: string;
}

function StatusRow({ label, value, valueClass }: StatusRowProps) {
  return (
    <div
      className="flex justify-between items-center py-3 border-b border-border/30 last:border-0"
      role="listitem"
    >
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={cn('text-sm font-medium text-foreground', valueClass)}>
        {value}
      </span>
    </div>
  );
}

interface ActionCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick?: () => void;
}

function ActionCard({ title, description, icon, onClick }: ActionCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'card card-interactive',
        'p-4 text-left',
        'flex flex-col gap-3',
        'focus-visible:outline-none focus-visible:ring-2',
        'focus-visible:ring-ring focus-visible:ring-offset-2',
        'focus-visible:ring-offset-background'
      )}
    >
      <div
        className={cn(
          'w-10 h-10 rounded-lg',
          'bg-primary/10 text-primary',
          'flex items-center justify-center'
        )}
        aria-hidden="true"
      >
        {icon}
      </div>
      <div>
        <span className="text-sm font-medium text-foreground block">{title}</span>
        <span className="text-xs text-muted-foreground mt-0.5 block">
          {description}
        </span>
      </div>
    </button>
  );
}

export default App;
