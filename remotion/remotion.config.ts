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

