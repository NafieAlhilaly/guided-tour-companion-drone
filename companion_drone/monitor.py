import cv2
import base64
import json
import time
import asyncio
from typing import Optional
import paho.mqtt.client as mqtt
from dataclasses import dataclass
import logging
from ultralytics import YOLO
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PoseStreamConfig:
    device_path: str = "/dev/video0"
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic: str = "drone/camera/pose"
    fps: int = 10
    width: Optional[int] = None
    height: Optional[int] = None
    model_path: str = "yolo11n-pose.pt"

class PoseStreamService:
    def __init__(self, config: PoseStreamConfig):
        self.config = config
        self.mqtt_client: Optional[mqtt.Client] = None
        self.capture: Optional[cv2.VideoCapture] = None
        self.running = False
        self.frame_count = 0
        self.model = YOLO(self.config.model_path, "pose")

    def setup_mqtt(self) -> bool:
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_disconnect = self._on_disconnect
            logger.info(f"Connecting to MQTT broker at {self.config.mqtt_broker}:{self.config.mqtt_port}")
            self.mqtt_client.connect(self.config.mqtt_broker, self.config.mqtt_port, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Failed to setup MQTT: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker")
        else:
            logger.error(f"Failed to connect to MQTT broker with code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT broker with code: {rc}")

    def setup_camera(self) -> bool:
        try:
            logger.info(f"Opening video device: {self.config.device_path}")
            self.capture = cv2.VideoCapture(self.config.device_path)
            if not self.capture.isOpened():
                logger.error(f"Failed to open video device: {self.config.device_path}")
                return False
            if self.config.width and self.config.height:
                self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
                self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            self.capture.set(cv2.CAP_PROP_FPS, self.config.fps)
            actual_width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.capture.get(cv2.CAP_PROP_FPS)
            logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps} FPS")
            return True
        except Exception as e:
            logger.error(f"Failed to setup camera: {e}")
            return False

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

    def publish_alert(self, alert_payload: dict) -> bool:
        try:
            if not self.mqtt_client or not self.mqtt_client.is_connected():
                logger.warning("MQTT client not connected, skipping alert")
                return False
            payload_json = json.dumps(alert_payload)
            result = self.mqtt_client.publish("notification/alert", payload_json, qos=1)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.warning(f"Failed to publish alert: {result.rc}")
                return False
            logger.info("Published lying-down alert")
            return True
        except Exception as e:
            logger.error(f"Failed to publish alert: {e}")
            return False

    def process_frame(self, frame) -> Optional[dict]:
        try:
            # Run pose estimation and draw results on the frame
            results = self.model(frame)
            # Ultralytics returns a Results object or list; get the first result
            res = results[0] if isinstance(results, list) else results
            # annotated image
            annotated_frame = res.plot()

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
                alert_payload = {
                    "alert": "lying_down",
                    "timestamp": time.time(),
                    "frame_id": f"frame_{self.frame_count}",
                    "device": self.config.device_path
                }
                # publish alert (non-blocking)
                try:
                    self.publish_alert(alert_payload)
                except Exception:
                    logger.exception("Failed publishing alert")

            # Encode the annotated frame as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), getattr(self.config, "image_quality", 90)]
            ret, buffer = cv2.imencode(".jpg", annotated_frame, encode_param)
            if not ret:
                logger.error("Failed to encode frame as JPEG")
                return None
            image_base64 = base64.b64encode(buffer).decode("utf-8")
            timestamp = time.time()
            payload = {
                "image": image_base64,
                "timestamp": timestamp,
                "width": annotated_frame.shape[1],
                "height": annotated_frame.shape[0],
                "frame_id": f"frame_{self.frame_count}",
                "encoding": "jpeg",
                "quality": getattr(self.config, "image_quality", 90),
                "device": self.config.device_path,
            }
            self.frame_count += 1
            return payload
        except Exception as e:
            logger.error(f"Failed to process frame: {e}")
            return None

    def publish_pose(self, payload: dict) -> bool:
        try:
            if not self.mqtt_client or not self.mqtt_client.is_connected():
                logger.warning("MQTT client not connected, skipping pose")
                return False
            payload_json = json.dumps(payload)
            result = self.mqtt_client.publish(
                self.config.mqtt_topic,
                payload_json,
                qos=0
            )
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.warning(f"Failed to publish pose: {result.rc}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to publish pose: {e}")
            return False

    async def stream_loop(self):
        logger.info("Starting pose stream loop")
        frame_interval = 1.0 / self.config.fps
        while self.running:
            start_time = time.time()
            ret, frame = self.capture.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                await asyncio.sleep(frame_interval)
                continue
            payload = self.process_frame(frame)
            if payload:
                self.publish_pose(payload)
                if self.frame_count % 10 == 0:
                    logger.info(f"Processed {self.frame_count} frames")
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            await asyncio.sleep(sleep_time)

    async def start(self):
        logger.info("Starting Pose Stream Service")
        if not self.setup_mqtt():
            logger.error("Failed to setup MQTT, cannot start service")
            return
        if not self.setup_camera():
            logger.error("Failed to setup camera, cannot start service")
            return
        self.running = True
        await self.stream_loop()

    def stop(self):
        logger.info("Stopping Pose Stream Service")
        self.running = False
        if self.capture:
            self.capture.release()
            logger.info("Camera released")
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT disconnected")

async def main():
    config = PoseStreamConfig(
        device_path="/dev/video0",
        mqtt_broker="localhost",
        mqtt_port=1883,
        mqtt_topic="drone/camera/pose",
        fps=10,
        width=640,
        height=480,
        model_path="yolo11n-pose.pt"
    )
    service = PoseStreamService(config)
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        service.stop()

if __name__ == "__main__":
    asyncio.run(main())