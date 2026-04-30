import { env } from '$env/dynamic/private';
import { json } from '@sveltejs/kit';
import { execFile } from 'node:child_process';
import path from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

export async function GET() {
  const studioRoot = process.cwd();
  const repoRoot = path.resolve(studioRoot, '..');
  const backendRoot = path.join(repoRoot, 'backend');
  const python = env.BACKEND_PYTHON || path.join(backendRoot, '.venv312/bin/python');
  const emulatorUrl = env.EMULATOR_URL || 'http://localhost:4100';
  const namespace = env.STUDIO_NAMESPACE || 'payments';

  try {
    const { stdout } = await execFileAsync(
      python,
      ['-m', 'sre_cli', 'assess', '--api-server', emulatorUrl, '--namespace', namespace, '--output', 'json'],
      {
        cwd: backendRoot,
        env: {
          ...process.env,
          CONVERSATIONS_PATH: process.env.CONVERSATIONS_PATH || '/tmp/bookish-octo-robot-conversations'
        },
        timeout: 20_000,
        maxBuffer: 1024 * 1024
      }
    );

    return json({
      source: emulatorUrl,
      namespace,
      assessment: JSON.parse(stdout)
    });
  } catch (error) {
    return json(
      {
        source: emulatorUrl,
        namespace,
        error: error instanceof Error ? error.message : 'Unable to run assessment'
      },
      { status: 502 }
    );
  }
}
