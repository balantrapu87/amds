/**
 * Remotion Configuration file.
 * Optimizes Chromium flags for hardware acceleration, ANGLE WebGL canvas, and parallel frame rendering.
 */
import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setChromiumOpenGlRenderer('angle');
Config.setChromiumMultiProcessOnLinux(true);
Config.setConcurrency(16);

// Hardware acceleration and WebGL flags for headless Chromium on Linux
Config.setChromiumFlags([
  '--enable-webgl',
  '--ignore-gpu-blocklist',
  '--enable-gpu-rasterization',
  '--enable-zero-copy',
  '--no-sandbox',
  '--disable-setuid-sandbox',
  '--disable-dev-shm-usage',
]);
