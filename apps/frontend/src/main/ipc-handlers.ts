/**
 * IPC Handlers for Main Process
 *
 * Part of Claude God Code - Autonomous Excellence
 *
 * This module sets up IPC handlers that bridge the React UI
 * with the Python backend.
 */

import { ipcMain, BrowserWindow, dialog, shell, app } from 'electron';
import log from 'electron-log';
import { getBackendBridge } from './backend-bridge';
import type { AppSettings } from '../shared/types';

const logger = log.scope('ipc-handlers');

export function setupIpcHandlers(getMainWindow: () => BrowserWindow | null): void {
  const bridge = getBackendBridge();

  // Backend status and ping
  ipcMain.handle('backend:ping', async () => {
    logger.info('Received backend:ping');
    return bridge.ping();
  });

  ipcMain.handle('backend:status', async () => {
    logger.info('Received backend:status');
    return bridge.getStatus();
  });

  ipcMain.handle('backend:info', async () => {
    logger.info('Received backend:info');
    return {
      success: true,
      data: bridge.getInfo(),
    };
  });

  // Session management
  ipcMain.handle('session:list', async () => {
    logger.info('Received session:list');
    return bridge.listSessions();
  });

  ipcMain.handle('session:start', async (_event, taskDescription: string) => {
    logger.info('Received session:start:', taskDescription);
    return bridge.startSpec(taskDescription);
  });

  // Spec management
  ipcMain.handle('spec:list', async () => {
    logger.info('Received spec:list');
    return bridge.listSpecs();
  });

  // QA operations
  ipcMain.handle('qa:run', async (_event, specName: string) => {
    logger.info('Received qa:run:', specName);
    return bridge.runQA(specName);
  });

  // Settings
  ipcMain.handle('settings:get', async () => {
    logger.info('Received settings:get');
    // Return default settings for now
    const settings: AppSettings = {
      theme: 'dark',
      autoFixEnabled: false,
      maxQAIterations: 50,
    };
    return { success: true, data: settings };
  });

  ipcMain.handle('settings:set', async (_event, settings: Partial<AppSettings>) => {
    logger.info('Received settings:set:', settings);

    if (settings.pythonPath) {
      bridge.setPythonPath(settings.pythonPath);
    }
    if (settings.backendPath) {
      bridge.setBackendPath(settings.backendPath);
    }

    return { success: true };
  });

  // Dialog handlers
  ipcMain.handle('dialog:openDirectory', async () => {
    const mainWindow = getMainWindow();
    if (!mainWindow) {
      return { success: false, error: 'No main window' };
    }

    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory'],
    });

    return {
      success: !result.canceled,
      data: result.filePaths[0],
    };
  });

  ipcMain.handle('dialog:openFile', async (_event, options?: { filters?: { name: string; extensions: string[] }[] }) => {
    const mainWindow = getMainWindow();
    if (!mainWindow) {
      return { success: false, error: 'No main window' };
    }

    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile'],
      filters: options?.filters,
    });

    return {
      success: !result.canceled,
      data: result.filePaths[0],
    };
  });

  // Shell operations
  ipcMain.handle('shell:openExternal', async (_event, url: string) => {
    logger.info('Opening external URL:', url);
    await shell.openExternal(url);
    return { success: true };
  });

  ipcMain.handle('shell:openPath', async (_event, path: string) => {
    logger.info('Opening path:', path);
    await shell.openPath(path);
    return { success: true };
  });

  // App info
  ipcMain.handle('app:getVersion', async () => {
    return { success: true, data: app.getVersion() };
  });

  ipcMain.handle('app:getPaths', async () => {
    return {
      success: true,
      data: {
        userData: app.getPath('userData'),
        appPath: app.getAppPath(),
        temp: app.getPath('temp'),
      },
    };
  });

  logger.info('IPC handlers registered');
}
