import cv2
import time
from typing import Optional
import logging
from ultralytics import YOLO
import numpy as np
from ffmpeg_capture import FFmpegCapture, FFmpegConfig
import asyncio
import paho.mqtt.client as mqtt
import base64
import json
from model import MQTTTopic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PoseProcessor:
    def __init__(self, model_path: str = "yolo11n-pose.pt"):
        self.running = False
        self.frame_count = 0
        logger.info(f"Loading pose model: {model_path}")
        self.model = YOLO(model_path, "pose")
        
        # Initialize MQTT client for safety alerts
        self.mqtt_client = mqtt.Client()
        try:
            # Connect to the local broker (localhost)
            self.mqtt_client.connect("127.0.0.1", 1883, 60)
            self.mqtt_client.loop_start()
            logger.info("MQTT client connected for Fall Detection alerts")
        except Exception as e:
            logger.error(f"Failed to connect MQTT for PoseProcessor: {e}")

    def _kp_person_lying(self, kps: np.ndarray, frame_shape: tuple) -> bool:
        """
        kps: (num_kpts, 2 or 3) array for one person (x,y[,score])
        frame_shape: (h, w, ...)
        Returns True if torso orientation indicates lying down.
        """
        try:
            # COCO keypoint indices: 5=left_shoulder, 6=right_shoulder, 11=left_hip, 12=right_hip
            # Guard indices if keypoint set differs
            h, w = frame_shape[0], frame_shape[1]
            # Ensure kps has at least x,y
            if kps.shape[1] < 2:
                return False
            # helper to safely read keypoint
            def kp(i):
                return None if i >= kps.shape[0] else kps[i, :2]

            ls = kp(5)
            rs = kp(6)
            lh = kp(11)
            rh = kp(12)
            pts = [p for p in (ls, rs, lh, rh) if p is not None and not np.any(np.isnan(p))]
            if len(pts) < 2:
                return False
            # compute mid-shoulder and mid-hip if available
            shoulders = [p for p in (ls, rs) if p is not None]
            hips = [p for p in (lh, rh) if p is not None]
            if not shoulders or not hips:
                return False
            mid_sh = np.mean(np.stack(shoulders), axis=0)
            mid_hp = np.mean(np.stack(hips), axis=0)
            dx = mid_sh[0] - mid_hp[0]
            dy = mid_sh[1] - mid_hp[1]
            # if horizontal (small dy relative to dx) -> lying
            if abs(dx) < 1e-6:
                return False
            ratio = abs(dy) / (abs(dx) + 1e-6)
            # Also require person not tiny in frame
            bbox_height = abs(np.max(kps[:,1]) - np.min(kps[:,1]))
            if bbox_height <= 0 or bbox_height > h:
                # fallback to width/height check later
                return False
            # lying if torso is closer to horizontal: ratio small
            return ratio < 0.5
        except Exception:
            return False

    def _result_has_boxes_as_array(self, boxes) -> Optional[np.ndarray]:
        try:
            if boxes is None:
                return None
            if hasattr(boxes, "xyxy"):
                arr = boxes.xyxy
                # may be tensor
                if hasattr(arr, "cpu"):
                    arr = arr.cpu().numpy()
                else:
                    arr = np.array(arr)
                return arr
            # fallback: try to convert directly
            return np.array(boxes)
        except Exception:
            return None

    def process(self, frame: np.ndarray) -> np.ndarray:
        try:
            # Run pose estimation and draw results on the frame
            results = self.model(frame, verbose=False)
            # Ultralytics returns a Results object or list; get the first result
            res = results[0] if isinstance(results, list) else results

            # Determine if any person is lying down
            lying_detected = False

            # 1) try using keypoints if present
            kps_obj = getattr(res, "keypoints", None)
            if kps_obj is not None:
                try:
                    # try several access patterns
                    kps_arr = None
                    if hasattr(kps_obj, "xy"):
                        kps_arr = kps_obj.xy  # numpy-like
                    elif hasattr(kps_obj, "xyxyn"):
                        kps_arr = kps_obj.xyxyn
                    else:
                        # try to coerce to numpy
                        kps_arr = np.array(kps_obj)
                    if kps_arr is not None and kps_arr.size:
                        # kps_arr shape might be (num_persons, num_kpts, 2/3)
                        if kps_arr.ndim == 3:
                            for person_kp in kps_arr:
                                if self._kp_person_lying(person_kp, frame.shape):
                                    lying_detected = True
                                    break
                        elif kps_arr.ndim == 2:
                            # single person
                            if self._kp_person_lying(kps_arr, frame.shape):
                                lying_detected = True
                except Exception:
                    # ignore and fallback to boxes
                    lying_detected = lying_detected or False

            # 2) fallback: use bounding box aspect ratio
            if not lying_detected:
                boxes = getattr(res, "boxes", None)
                arr = self._result_has_boxes_as_array(boxes)
                if arr is not None and arr.size:
                    for box in arr:
                        x1, y1, x2, y2 = box[:4]
                        w = x2 - x1
                        h = y2 - y1
                        if h <= 0:
                            continue
                        if (w / h) > 1.5 and (h < frame.shape[0] * 0.8):
                            lying_detected = True
                            break

            # if lying detected, send alert
            if lying_detected:
                logger.warning(f"Fall detected at frame {self.frame_count}! Sending alert...")
                try:
                    annotated_frame = res.plot()
                    _, buffer = cv2.imencode('.jpg', annotated_frame)
                    img_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    payload = {
                        "message": "Fall detected",
                        "image": img_base64
                    }
                    self.mqtt_client.publish(MQTTTopic.ALERT_NOTIFICATION_TOPIC.value, json.dumps(payload))
                except Exception as e:
                    logger.error(f"Failed to send MQTT alert: {e}")

            self.frame_count += 1
            # Return the original raw frame to keep the WebRTC stream clean
            return frame
        except Exception as e:
            logger.error(f"Failed to process frame: {e}")
            return frame

class PoseStreamService:
    """Optional standalone service for pose detection without MQTT."""
    def __init__(self, video_device="/dev/video0", width=640, height=480, fps=10):
        self.ffmpeg = FFmpegCapture(FFmpegConfig(
            video_device=video_device,
            width=width,
            height=height,
            fps=fps
        ))
        self.processor = PoseProcessor()
        self.running = False

    async def stream_loop(self):
        logger.info("Starting pose stream loop")
        loop = asyncio.get_running_loop()
        width = self.ffmpeg.config.width
        height = self.ffmpeg.config.height
        
        while self.running:
            frame_data = await loop.run_in_executor(None, self.ffmpeg.read_frame)
            
            if frame_data is None:
                await asyncio.sleep(0.01)
                continue

            frame = np.frombuffer(frame_data, dtype=np.uint8).reshape(
                (height, width, 3)
            )

            # Process frame
            await loop.run_in_executor(None, self.processor.process, frame)

            if self.processor.frame_count % 10 == 0:
                logger.info(f"Processed {self.processor.frame_count} frames")

    async def start(self):
        if not self.ffmpeg.start():
            return
        self.running = True
        await self.stream_loop()

    def stop(self):
        self.running = False
        self.ffmpeg.stop()

async def main():
    service = PoseStreamService()
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        service.stop()

if __name__ == "__main__":
    asyncio.run(main())