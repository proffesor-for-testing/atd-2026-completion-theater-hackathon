import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { DatabaseSync } from 'node:sqlite';

export const APP_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');

let interpreter: string | undefined;

/** The real python executable, so killing the child kills the server (not just a `py` launcher). */
function python(): string {
  if (interpreter) return interpreter;
  const candidates: [string, string[]][] = process.env.PYTHON
    ? [[process.env.PYTHON, []]]
    : process.platform === 'win32' ? [['py', ['-3']], ['python', []]] : [['python3', []], ['python', []]];
  for (const [cmd, args] of candidates) {
    const probe = spawnSync(cmd, [...args, '-c', 'import sys; print(sys.executable)'], { encoding: 'utf8' });
    if (probe.status === 0 && probe.stdout.trim()) return (interpreter = probe.stdout.trim());
  }
  throw new Error('No Python 3.11+ found. Set PYTHON to its full path.');
}

async function freePort(): Promise<number> {
  return new Promise((resolvePort, reject) => {
    const server = createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      if (address && typeof address === 'object') {
        const port = address.port;
        server.close(() => resolvePort(port));
      } else reject(new Error('Could not allocate a port'));
    });
  });
}

export interface StoredRow {
  id: string;
  session_id: string;
  attendee_alias: string;
  request_key: string;
  status: string;
}

/**
 * One app process with its own fixture directory. Reset happens once, explicitly, at
 * creation; restart() stops the process and starts a new one on the SAME directory
 * without resetting — the AC-07 sequence.
 */
export class AppServer {
  readonly dataDir: string;
  port = 0;
  pid = 0;
  log = '';
  private child?: ChildProcess;

  private constructor(dataDir: string) {
    this.dataDir = dataDir;
  }

  static async create(): Promise<AppServer> {
    const dataDir = join(mkdtempSync(join(tmpdir(), 'seat-desk-')), 'state');
    const server = new AppServer(dataDir);
    const reset = spawnSync(python(), ['app.py', '--reset'], {
      cwd: APP_DIR, env: { ...process.env, DATA_DIR: dataDir }, encoding: 'utf8',
    });
    if (reset.status !== 0) throw new Error(`--reset failed (${reset.status}): ${reset.stderr}`);
    await server.start();
    return server;
  }

  get baseURL(): string {
    return `http://127.0.0.1:${this.port}`;
  }

  /** Starts on the same port as before when restarting, so open pages and clients stay valid. */
  async start(): Promise<void> {
    if (!this.port) this.port = await freePort();
    const child = spawn(python(), ['app.py'], {
      cwd: APP_DIR,
      env: { ...process.env, DATA_DIR: this.dataDir, PORT: String(this.port), PYTHONUNBUFFERED: '1' },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    this.child = child;
    this.pid = child.pid ?? 0;
    child.stdout?.on('data', (chunk) => (this.log += chunk));
    child.stderr?.on('data', (chunk) => (this.log += chunk));
    const deadline = Date.now() + 15_000;
    while (Date.now() < deadline) {
      if (child.exitCode !== null) throw new Error(`App exited (${child.exitCode}) before ready:\n${this.log}`);
      try {
        const response = await fetch(`${this.baseURL}/sessions`);
        if (response.status === 200) return;
      } catch {
        // not listening yet
      }
      await new Promise((r) => setTimeout(r, 100));
    }
    throw new Error(`App not ready within 15s:\n${this.log}`);
  }

  async stop(): Promise<void> {
    const child = this.child;
    if (!child || child.exitCode !== null) return;
    const exited = new Promise((r) => child.once('exit', r));
    child.kill();
    await exited;
    this.child = undefined;
  }

  async restart(): Promise<void> {
    await this.stop();
    await this.start();
  }

  /** Read the SQLite file directly — independent of the API under test (Ghost Database check). */
  rows(): StoredRow[] {
    const db = new DatabaseSync(join(this.dataDir, 'seats.db'), { readOnly: true });
    try {
      return db
        .prepare('SELECT id, session_id, attendee_alias, request_key, status FROM reservations ORDER BY created_at')
        .all() as unknown as StoredRow[];
    } finally {
      db.close();
    }
  }

  async dispose(): Promise<void> {
    await this.stop();
    rmSync(dirname(this.dataDir), { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
  }
}
