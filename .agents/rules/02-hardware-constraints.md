# Hardware & Execution Environment Constraints

1. **Host Environment:**
   - OS: Ubuntu 24.04 LTS
   - CPU: AMD Ryzen 9 9950X (16 physical cores, 32 execution threads)
   - GPU: AMD Radeon AI PRO R9700 (32 GB VRAM, ROCm 6.x)
   - Memory: 64 GB DDR5

2. **Remotion Worker Execution:**
   - Thread Concurrency: Default to 16 concurrent workers (`--concurrency=16`).
   - Browser Rasterizer: Headless Chromium using ANGLE/Vulkan or SwiftShader backend.
   - VRAM Allocation: Ensure individual render workers do not exceed 4 GB VRAM allocations.
   - Subprocess Management: Spawns must run asynchronously in background subprocesses with output redirected to job log files.

3. **FFmpeg Subsystem Constraints:**
   - Always verify FFmpeg 6.x+ is available.
   - Video track must use direct stream copy (`-c:v copy`) during audio multiplexing to avoid re-rendering frames.
   - Filtergraphs must use discrete labels (`[0:v]`, `[1:a]`, `[2:a]`, `[bgm_ducked]`, `[master_audio]`).
