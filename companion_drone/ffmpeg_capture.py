import subprocess
import logging
import fcntl
import os
import select
import time
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

@dataclass
class FFmpegConfig:
    video_device: str = "/dev/video0"
    width: int = 640
    height: int = 480
    fps: int = 30
    format: str = "mjpeg"

class FFmpegCapture:
    def __init__(self, config: FFmpegConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
    
    def start(self) -> bool:
        try:
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-probesize", "32",
                "-analyzeduration", "0",
                "-f", "v4l2",
                "-input_format", self.config.format,
                "-thread_queue_size", "128",
                "-video_size", f"{self.config.width}x{self.config.height}",
                "-framerate", str(self.config.fps),
                "-i", self.config.video_device,
            ]
            
            # Output settings
            cmd.extend([
                "-fflags", "nobuffer",
                "-flags", "low_delay",
                "-f", "rawvideo",
                "-pix_fmt", "bgr24",
                "-"
            ])
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
            
            # Make stdout non-blocking to prevent deadlocks
            if self.process.stdout:
                flags = fcntl.fcntl(self.process.stdout, fcntl.F_GETFL)
                fcntl.fcntl(self.process.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            
            logger.info(f"FFmpeg started: {self.config.video_device}")
            return True
        except Exception as e:
            logger.error(f"FFmpeg start failed: {e}")
            return False
    
    def read_frame(self) -> Optional[Tuple[bytes, float]]:
        """Returns a tuple of (frame_data, capture_timestamp_ns)"""
        if not self.process or self.process.poll() is not None:
            logger.warning("FFmpeg process not running")
            return None
        
        try:
            frame_size = self.config.width * self.config.height * 3
            latest_frame = None
            
            # Drain the pipe to ensure we get the most recent frame (stay live)
            while True:
                # Check if there is data available to read
                ready, _, _ = select.select([self.process.stdout], [], [], 0)
                if not ready:
                    break

                frame_data = self._read_exact(frame_size)
                if frame_data:
                    # Record time immediately after reading from pipe
                    latest_frame = (frame_data, time.time_ns())
                else:
                    break
            
            return latest_frame
        except Exception as e:
            logger.error(f"Frame read failed: {e}")
            return None

    def _read_exact(self, n: int) -> Optional[bytes]:
        """Helper to read exactly n bytes from the non-blocking pipe."""
        data = b""
        while len(data) < n:
            try:
                # Wait up to 10ms for data if we've already started reading a frame
                if len(data) > 0:
                    ready, _, _ = select.select([self.process.stdout], [], [], 0.01)
                    if not ready:
                        break
                
                chunk = self.process.stdout.read(n - len(data))
                if not chunk:
                    break
                data += chunk
            except (BlockingIOError, TypeError):
                break
        if len(data) == n:
            return data
        return None
    
    def stop(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            logger.info("FFmpeg stopped")
    
    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None
