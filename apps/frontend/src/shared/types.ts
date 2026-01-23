/**
 * Shared types for Claude God Code Frontend
 *
 * Part of Claude God Code - Autonomous Excellence
 */

export interface BackendStatus {
  connected: boolean;
  version: string;
  pythonPath: string;
  uptime: number;
  activeSessionCount: number;
  lastError?: string;
}

export interface SessionInfo {
  sessionId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused';
  phase: string;
  taskDescription: string;
  startedAt?: string;
  completedAt?: string;
  durationSeconds: number;
}

export interface SpecInfo {
  name: string;
  path: string;
  status: string;
  qaSession: number;
  issuesCount: number;
}

export interface ImpactReport {
  severity: 'none' | 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  affectedFiles: string[];
  affectedServices: string[];
  breakingChanges: BreakingChange[];
  testCoverageGaps: string[];
  rollbackComplexity: string;
  recommendedMitigations: string[];
}

export interface BreakingChange {
  changeType: string;
  location: string;
  description: string;
  affectedConsumers: string[];
  migrationRequired: boolean;
  suggestedFix?: string;
}

export interface QAStatus {
  status: 'pending' | 'approved' | 'rejected' | 'fixes_applied' | 'error';
  qaSession: number;
  issuesFound: QAIssue[];
  currentIteration: number;
  isApproved: boolean;
}

export interface QAIssue {
  title: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  location?: string;
  fixRequired?: string;
}

export interface AppSettings {
  pythonPath?: string;
  backendPath?: string;
  theme: 'light' | 'dark' | 'system';
  autoFixEnabled: boolean;
  maxQAIterations: number;
}

export type IPCChannel =
  | 'backend:status'
  | 'backend:ping'
  | 'session:list'
  | 'session:start'
  | 'session:status'
  | 'spec:list'
  | 'spec:create'
  | 'qa:run'
  | 'qa:status'
  | 'settings:get'
  | 'settings:set';

export interface IPCResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}
