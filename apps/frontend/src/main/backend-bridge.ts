/**
 * Backend Bridge - Python Backend Communication
 *
 * Part of Claude God Code - Autonomous Excellence
 *
 * This module handles spawning and communicating with the Python backend
 * via subprocess and IPC.
 */

import { spawn, ChildProcess, execSync } from 'child_process';
import { app } from 'electron';
import { join, dirname } from 'path';
import { existsSync } from 'fs';
import log from 'electron-log';
import type { BackendStatus, IPCResponse, SessionInfo, SpecInfo } from '../shared/types';

const logger = log.scope('backend-bridge');

export class BackendBridge {
  private pythonPath: string | null = null;
  private backendPath: string | null = null;
  private process: ChildProcess | null = null;
  private startTime: number = 0;
  private lastError: string | null = null;
  private isConnected: boolean = false;

  constructor() {
    this.detectPaths();
  }

  private detectPaths(): void {
    // Detect Python path
    this.pythonPath = this.findPython();

    // Detect backend path
    this.backendPath = this.findBackend();

    logger.info('Detected paths:', {
      python: this.pythonPath,
      backend: this.backendPath,
    });
  }

  private findPython(): string | null {
    const candidates = ['python3', 'python', 'python3.12', 'python3.11'];

    for (const candidate of candidates) {
      try {
        const result = execSync(`${candidate} --version`, {
          encoding: 'utf-8',
          timeout: 5000,
        });
        if (result.includes('Python 3')) {
          // Get full path
          const which = process.platform === 'win32' ? 'where' : 'which';
          const fullPath = execSync(`${which} ${candidate}`, {
            encoding: 'utf-8',
            timeout: 5000,
          }).replace(/\r/g, '').trim().split('\n')[0];
          return fullPath;
        }
      } catch {
        // Continue to next candidate
      }
    }

    return null;
  }

  private findBackend(): string | null {
    // In development: relative to project root
    // In production: in app resources
    const possiblePaths = [
      // Development: relative to frontend
      join(dirname(app.getAppPath()), 'backend'),
      join(app.getAppPath(), '..', 'backend'),
      join(process.cwd(), 'apps', 'backend'),
      // Production: in resources
      join(process.resourcesPath || '', 'backend'),
      join(app.getPath('exe'), '..', 'resources', 'backend'),
    ];

    for (const backendPath of possiblePaths) {
      const entryPoint = join(backendPath, 'cli', 'entry.py');
      if (existsSync(entryPoint)) {
        return backendPath;
      }
    }

    return null;
  }

  async ping(): Promise<IPCResponse<BackendStatus>> {
    if (!this.pythonPath) {
      return {
        success: false,
        error: 'Python not found. Please install Python 3.11 or higher.',
      };
    }

    if (!this.backendPath) {
      return {
        success: false,
        error: 'Backend not found. Please check installation.',
      };
    }

    try {
      // Run a simple status check via Python CLI
      const result = await this.runCommand(['--status']);

      this.isConnected = true;
      this.lastError = null;

      return {
        success: true,
        data: {
          connected: true,
          version: '0.1.0',
          pythonPath: this.pythonPath,
          uptime: this.startTime > 0 ? Date.now() - this.startTime : 0,
          activeSessionCount: 0,
        },
      };
    } catch (error) {
      this.isConnected = false;
      this.lastError = error instanceof Error ? error.message : String(error);

      return {
        success: false,
        error: this.lastError,
        data: {
          connected: false,
          version: '0.1.0',
          pythonPath: this.pythonPath || 'not found',
          uptime: 0,
          activeSessionCount: 0,
          lastError: this.lastError,
        },
      };
    }
  }

  async getStatus(): Promise<IPCResponse<BackendStatus>> {
    return this.ping();
  }

  async listSessions(): Promise<IPCResponse<SessionInfo[]>> {
    try {
      const result = await this.runCommand(['--status', '--json']);
      // Parse JSON output when available
      return {
        success: true,
        data: [],
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  async listSpecs(): Promise<IPCResponse<SpecInfo[]>> {
    try {
      const result = await this.runCommand(['--list', '--json']);
      // Parse JSON output when available
      return {
        success: true,
        data: [],
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  async startSpec(taskDescription: string): Promise<IPCResponse<{ sessionId: string }>> {
    try {
      const result = await this.runCommand(['--spec', taskDescription]);
      return {
        success: true,
        data: { sessionId: 'pending' },
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  async runQA(specName: string): Promise<IPCResponse<void>> {
    try {
      await this.runCommand(['--qa', '--spec', specName]);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  private runCommand(args: string[]): Promise<string> {
    return new Promise((resolve, reject) => {
      if (!this.pythonPath || !this.backendPath) {
        reject(new Error('Python or backend path not configured'));
        return;
      }

      const entryPoint = join(this.backendPath, 'cli', 'entry.py');
      const fullArgs = [entryPoint, ...args];

      logger.info('Running command:', this.pythonPath, fullArgs.join(' '));

      const proc = spawn(this.pythonPath, fullArgs, {
        cwd: this.backendPath,
        env: {
          ...process.env,
          PYTHONPATH: this.backendPath,
        },
      });

      let stdout = '';
      let stderr = '';

      proc.stdout?.on('data', (data) => {
        stdout += data.toString();
        logger.debug('stdout:', data.toString());
      });

      proc.stderr?.on('data', (data) => {
        stderr += data.toString();
        logger.debug('stderr:', data.toString());
      });

      proc.on('close', (code) => {
        if (code === 0) {
          resolve(stdout);
        } else {
          reject(new Error(stderr || `Process exited with code ${code}`));
        }
      });

      proc.on('error', (error) => {
        reject(error);
      });

      // Timeout after 30 seconds
      setTimeout(() => {
        proc.kill();
        reject(new Error('Command timed out'));
      }, 30000);
    });
  }

  getInfo(): { pythonPath: string | null; backendPath: string | null; connected: boolean } {
    return {
      pythonPath: this.pythonPath,
      backendPath: this.backendPath,
      connected: this.isConnected,
    };
  }

  setPythonPath(path: string): void {
    this.pythonPath = path;
    logger.info('Python path set to:', path);
  }

  setBackendPath(path: string): void {
    this.backendPath = path;
    logger.info('Backend path set to:', path);
  }
}

// Singleton instance
let bridgeInstance: BackendBridge | null = null;

export function getBackendBridge(): BackendBridge {
  if (!bridgeInstance) {
    bridgeInstance = new BackendBridge();
  }
  return bridgeInstance;
}
