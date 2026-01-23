/**
 * Electron Main Process Entry Point
 *
 * Part of Claude God Code - Autonomous Excellence
 *
 * This is the main entry point for the Electron application.
 * It initializes the window, sets up IPC handlers, and manages
 * communication with the Python backend.
 */

import { app, BrowserWindow, shell, nativeImage, screen } from 'electron';
import { join } from 'path';
import { existsSync } from 'fs';
import { electronApp, optimizer, is } from '@electron-toolkit/utils';
import log from 'electron-log';
import { setupIpcHandlers } from './ipc-handlers';
import { getBackendBridge } from './backend-bridge';

// Configure logging
log.transports.file.level = 'info';
log.transports.console.level = is.dev ? 'debug' : 'info';
const logger = log.scope('main');

// Window sizing constants
const WINDOW_PREFERRED_WIDTH = 1400;
const WINDOW_PREFERRED_HEIGHT = 900;
const WINDOW_MIN_WIDTH = 800;
const WINDOW_MIN_HEIGHT = 500;
const WINDOW_SCREEN_MARGIN = 20;
const DEFAULT_SCREEN_WIDTH = 1920;
const DEFAULT_SCREEN_HEIGHT = 1080;

// Keep a global reference of the window object
let mainWindow: BrowserWindow | null = null;

function getIconPath(): string {
  const resourcesPath = is.dev
    ? join(__dirname, '../../resources')
    : process.resourcesPath;

  let iconName: string;
  if (process.platform === 'darwin') {
    iconName = is.dev ? 'icon.png' : 'icon.icns';
  } else if (process.platform === 'win32') {
    iconName = 'icon.ico';
  } else {
    iconName = 'icon.png';
  }

  const iconPath = join(resourcesPath, iconName);
  return existsSync(iconPath) ? iconPath : '';
}

function createWindow(): void {
  // Get the primary display's work area
  let workAreaSize: { width: number; height: number };
  try {
    const display = screen.getPrimaryDisplay();
    if (
      display?.workAreaSize?.width > 0 &&
      display?.workAreaSize?.height > 0
    ) {
      workAreaSize = display.workAreaSize;
    } else {
      workAreaSize = { width: DEFAULT_SCREEN_WIDTH, height: DEFAULT_SCREEN_HEIGHT };
    }
  } catch (error) {
    logger.error('Failed to get primary display:', error);
    workAreaSize = { width: DEFAULT_SCREEN_WIDTH, height: DEFAULT_SCREEN_HEIGHT };
  }

  // Calculate window dimensions
  const availableWidth = workAreaSize.width - WINDOW_SCREEN_MARGIN;
  const availableHeight = workAreaSize.height - WINDOW_SCREEN_MARGIN;
  const width = Math.min(WINDOW_PREFERRED_WIDTH, availableWidth);
  const height = Math.min(WINDOW_PREFERRED_HEIGHT, availableHeight);
  const minWidth = Math.min(WINDOW_MIN_WIDTH, width);
  const minHeight = Math.min(WINDOW_MIN_HEIGHT, height);

  // Create the browser window
  mainWindow = new BrowserWindow({
    width,
    height,
    minWidth,
    minHeight,
    show: false,
    autoHideMenuBar: true,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    trafficLightPosition: { x: 15, y: 10 },
    icon: getIconPath(),
    backgroundColor: '#0f172a', // god-dark-900
    webPreferences: {
      preload: join(__dirname, '../preload/index.mjs'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Show window when ready
  mainWindow.on('ready-to-show', () => {
    mainWindow?.show();
    logger.info('Window shown');
  });

  // Handle external links
  const ALLOWED_URL_SCHEMES = ['http:', 'https:', 'mailto:'];
  mainWindow.webContents.setWindowOpenHandler((details) => {
    try {
      const url = new URL(details.url);
      if (ALLOWED_URL_SCHEMES.includes(url.protocol)) {
        shell.openExternal(details.url).catch((error) => {
          logger.warn('Failed to open external URL:', details.url, error);
        });
      }
    } catch {
      logger.warn('Blocked invalid URL:', details.url);
    }
    return { action: 'deny' };
  });

  // Load the renderer
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL']);
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'));
  }

  // Open DevTools in development
  if (is.dev) {
    mainWindow.webContents.openDevTools({ mode: 'right' });
  }

  // Clean up on close
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Set app name
app.setName('Claude God Code');
if (process.platform === 'darwin') {
  app.name = 'Claude God Code';
}

// Fix Windows GPU cache issues
if (process.platform === 'win32') {
  app.commandLine.appendSwitch('disable-gpu-shader-disk-cache');
  app.commandLine.appendSwitch('disable-gpu-program-cache');
}

// Initialize the application
app.whenReady().then(() => {
  // Set app user model id for Windows
  electronApp.setAppUserModelId('com.claudegodcode.ui');

  // Default open or close DevTools by F12 in development
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window);
  });

  // Setup IPC handlers
  setupIpcHandlers(() => mainWindow);

  // Initialize backend bridge
  const bridge = getBackendBridge();
  const info = bridge.getInfo();
  logger.info('Backend bridge initialized:', info);

  // Create window
  createWindow();

  // Set dock icon on macOS
  if (process.platform === 'darwin') {
    const iconPath = getIconPath();
    if (iconPath) {
      try {
        const icon = nativeImage.createFromPath(iconPath);
        if (!icon.isEmpty()) {
          app.dock?.setIcon(icon);
        }
      } catch (e) {
        logger.warn('Could not set dock icon:', e);
      }
    }
  }

  // macOS: re-create window when dock icon is clicked
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });

  logger.info('Claude God Code started');
  logger.info('Version:', app.getVersion());
  logger.info('Platform:', process.platform);
  logger.info('Development mode:', is.dev);
});

// Quit when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Cleanup before quit
app.on('before-quit', async () => {
  logger.info('Application quitting...');
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception:', error);
});

process.on('unhandledRejection', (reason) => {
  logger.error('Unhandled rejection:', reason);
});
