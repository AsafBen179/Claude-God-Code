/**
 * Preload Script - Context Bridge
 *
 * Part of Claude God Code - Autonomous Excellence
 *
 * This script runs in the preload context and exposes a safe API
 * to the renderer process via contextBridge.
 */

import { contextBridge, ipcRenderer } from 'electron';
import type {
  BackendStatus,
  SessionInfo,
  SpecInfo,
  AppSettings,
  IPCResponse,
} from '../shared/types';

// API exposed to renderer
const electronAPI = {
  // Backend operations
  backend: {
    ping: (): Promise<IPCResponse<BackendStatus>> =>
      ipcRenderer.invoke('backend:ping'),

    status: (): Promise<IPCResponse<BackendStatus>> =>
      ipcRenderer.invoke('backend:status'),

    info: (): Promise<IPCResponse<{ pythonPath: string | null; backendPath: string | null; connected: boolean }>> =>
      ipcRenderer.invoke('backend:info'),
  },

  // Session operations
  session: {
    list: (): Promise<IPCResponse<SessionInfo[]>> =>
      ipcRenderer.invoke('session:list'),

    start: (taskDescription: string): Promise<IPCResponse<{ sessionId: string }>> =>
      ipcRenderer.invoke('session:start', taskDescription),
  },

  // Spec operations
  spec: {
    list: (): Promise<IPCResponse<SpecInfo[]>> =>
      ipcRenderer.invoke('spec:list'),
  },

  // QA operations
  qa: {
    run: (specName: string): Promise<IPCResponse<void>> =>
      ipcRenderer.invoke('qa:run', specName),
  },

  // Settings
  settings: {
    get: (): Promise<IPCResponse<AppSettings>> =>
      ipcRenderer.invoke('settings:get'),

    set: (settings: Partial<AppSettings>): Promise<IPCResponse<void>> =>
      ipcRenderer.invoke('settings:set', settings),
  },

  // Dialogs
  dialog: {
    openDirectory: (): Promise<IPCResponse<string>> =>
      ipcRenderer.invoke('dialog:openDirectory'),

    openFile: (options?: { filters?: { name: string; extensions: string[] }[] }): Promise<IPCResponse<string>> =>
      ipcRenderer.invoke('dialog:openFile', options),
  },

  // Shell operations
  shell: {
    openExternal: (url: string): Promise<IPCResponse<void>> =>
      ipcRenderer.invoke('shell:openExternal', url),

    openPath: (path: string): Promise<IPCResponse<void>> =>
      ipcRenderer.invoke('shell:openPath', path),
  },

  // App info
  app: {
    getVersion: (): Promise<IPCResponse<string>> =>
      ipcRenderer.invoke('app:getVersion'),

    getPaths: (): Promise<IPCResponse<{ userData: string; appPath: string; temp: string }>> =>
      ipcRenderer.invoke('app:getPaths'),
  },

  // Event subscriptions
  on: (channel: string, callback: (...args: unknown[]) => void): (() => void) => {
    const subscription = (_event: Electron.IpcRendererEvent, ...args: unknown[]) => callback(...args);
    ipcRenderer.on(channel, subscription);
    return () => {
      ipcRenderer.removeListener(channel, subscription);
    };
  },

  // One-time event listener
  once: (channel: string, callback: (...args: unknown[]) => void): void => {
    ipcRenderer.once(channel, (_event, ...args) => callback(...args));
  },
};

// Expose to renderer
contextBridge.exposeInMainWorld('electronAPI', electronAPI);

// TypeScript type for window.electronAPI
export type ElectronAPI = typeof electronAPI;

// Declare global type
declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}
