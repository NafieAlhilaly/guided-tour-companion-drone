import cv2
import base64
import json
import time
import asyncio
from typing import Optional
import paho.mqtt.client as mqtt
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class VideoStreamConfig:
    """Configuration for video streaming service"""
    device_path: str = "/dev/video0"
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic: str = "drone/camera/image"
    image_quality: int = 80
    image_scale: float = 0.5
    fps: int = 30
    width: Optional[int] = None
    height: Optional[int] = None


class VideoStreamService:
    """Service to stream video from Linux video device to MQTT"""
    
    def __init__(self, config: VideoStreamConfig):
        self.config = config
        self.mqtt_client: Optional[mqtt.Client] = None
        self.capture: Optional[cv2.VideoCapture] = None
        self.running = False
        self.frame_count = 0
        
    def setup_mqtt(self) -> bool:
        """Setup MQTT client connection"""
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
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
        else:
            logger.error(f"Failed to connect to MQTT broker with code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.warning(f"Disconnected from MQTT broker with code: {rc}")
    
    def setup_camera(self) -> bool:
        """Setup video capture device"""
        try:
            logger.info(f"Opening video device: {self.config.device_path}")
            self.capture = cv2.VideoCapture(self.config.device_path)
            
            if not self.capture.isOpened():
                logger.error(f"Failed to open video device: {self.config.device_path}")
                return False
            
            # Set resolution if specified
            if self.config.width and self.config.height:
                self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
                self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            
            # Set FPS
            self.capture.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            # Get actual camera properties
            actual_width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.capture.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps} FPS")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup camera: {e}")
            return False
    
    def process_frame(self, frame) -> Optional[dict]:
        """Process frame and create MQTT payload"""
        try:
            # Resize if scale factor is set
            if self.config.image_scale != 1.0:
                new_width = int(frame.shape[1] * self.config.image_scale)
                new_height = int(frame.shape[0] * self.config.image_scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # Encode to JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.config.image_quality]
            _, encoded_image = cv2.imencode('.jpg', frame, encode_param)
            
            # Convert to base64 for transmission
            image_base64 = base64.b64encode(encoded_image).decode('utf-8')
            
            # Create payload with metadata
            timestamp = time.time()
            payload = {
                'image': image_base64,
                'timestamp': timestamp,
                'width': frame.shape[1],
                'height': frame.shape[0],
                'frame_id': f"frame_{self.frame_count}",
                'encoding': 'jpeg',
                'quality': self.config.image_quality,
                'device': self.config.device_path
            }
            
            self.frame_count += 1
            return payload
            
        except Exception as e:
            logger.error(f"Failed to process frame: {e}")
            return None
    
    def publish_frame(self, payload: dict) -> bool:
        """Publish frame payload to MQTT"""
        try:
            if not self.mqtt_client or not self.mqtt_client.is_connected():
                logger.warning("MQTT client not connected, skipping frame")
                return False
            
            # Convert payload to JSON
            payload_json = json.dumps(payload)
            
            # Publish to MQTT topic
            result = self.mqtt_client.publish(
                self.config.mqtt_topic,
                payload_json,
                qos=0  # Use QoS 0 for video streaming (speed over reliability)
            )
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.warning(f"Failed to publish frame: {result.rc}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish frame: {e}")
            return False
    
    async def stream_loop(self):
        """Main streaming loop"""
        logger.info("Starting video stream loop")
        frame_interval = 1.0 / self.config.fps
        
        while self.running:
            start_time = time.time()
            
            # Capture frame
            ret, frame = self.capture.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                await asyncio.sleep(frame_interval)
                continue
            
            # Process frame
            payload = self.process_frame(frame)
            if payload:
                # Publish frame
                self.publish_frame(payload)
                
                # Log every 100 frames
                if self.frame_count % 100 == 0:
                    logger.info(f"Streamed {self.frame_count} frames")
            
            # Maintain frame rate
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            await asyncio.sleep(sleep_time)
    
    async def start(self):
        """Start the video streaming service"""
        logger.info("Starting Video Stream Service")
        
        # Setup MQTT
        if not self.setup_mqtt():
            logger.error("Failed to setup MQTT, cannot start service")
            return
        
        # Setup camera
        if not self.setup_camera():
            logger.error("Failed to setup camera, cannot start service")
            return
        
        # Start streaming
        self.running = True
        await self.stream_loop()
    
    def stop(self):
        """Stop the video streaming service"""
        logger.info("Stopping Video Stream Service")
        self.running = False
        
        # Release camera
        if self.capture:
            self.capture.release()
            logger.info("Camera released")
        
        # Disconnect MQTT
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT disconnected")


async def main():
    """Main entry point for video streaming service"""
    # Configuration
    config = VideoStreamConfig(
        device_path="/dev/video0",  # Change to your video device
        mqtt_broker="localhost",
        mqtt_port=1883,
        mqtt_topic="drone/camera/image",
        image_quality=80,
        image_scale=0.5,  # Scale down to 50% for bandwidth
        fps=30,
        width=1280,  # Optional: set desired resolution
        height=720
    )
    
    # Create and start service
    service = VideoStreamService(config)
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        service.stop()


if __name__ == "__main__":
    asyncio.run(main())