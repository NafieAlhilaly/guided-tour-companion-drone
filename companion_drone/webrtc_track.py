import logging
import numpy as np
import av
import asyncio
import time
from aiortc import VideoStreamTrack
from ffmpeg_capture import FFmpegCapture

logger = logging.getLogger(__name__)

class CameraVideoTrack(VideoStreamTrack):
    def __init__(self, ffmpeg_capture: FFmpegCapture):
        super().__init__()
        self.ffmpeg_capture = ffmpeg_capture
        self.frame_count = 0
        self._last_frame = None
        self.latest_ingress_timestamp = 0
    
    async def recv(self) -> av.VideoFrame:
        pts, time_base = await self.next_timestamp()
        
        # Read frame in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.ffmpeg_capture.read_frame)
        
        if result is None:
            # Return last frame if available, else black frame
            if self._last_frame is not None:
                frame = self._last_frame
            else:
                h, w = self.ffmpeg_capture.config.height, self.ffmpeg_capture.config.width
                black = np.zeros((h, w, 3), dtype=np.uint8)
                frame = av.VideoFrame.from_ndarray(black, format="bgr24")
            frame.pts, frame.time_base = pts, time_base
            return frame

        frame_data, ingress_time_ns = result
        self.latest_ingress_timestamp = ingress_time_ns
        
        # Calculate overhead of the executor/scheduling
        scheduling_delay = (time.time_ns() - ingress_time_ns) / 1e6
        
        h = self.ffmpeg_capture.config.height
        w = self.ffmpeg_capture.config.width
        
        try:
            frame_array = np.frombuffer(frame_data, dtype=np.uint8).reshape((h, w, 3))
            frame = av.VideoFrame.from_ndarray(frame_array, format="bgr24")
        except Exception as e:
            logger.error(f"Frame conversion error: {e}")
            h, w = self.ffmpeg_capture.config.height, self.ffmpeg_capture.config.width
            black = np.zeros((h, w, 3), dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(black, format="bgr24")
        
        frame.pts, frame.time_base = pts, time_base
        self._last_frame = frame

        # Processing delay (Conversion)
        total_internal_delay = (time.time_ns() - ingress_time_ns) / 1e6
        
        self.frame_count += 1
        if self.frame_count % 30 == 0:
            logger.info(f"Frame {self.frame_count} | Scheduling: {scheduling_delay:.2f}ms | Total Internal: {total_internal_delay:.2f}ms")
        
        return frame
