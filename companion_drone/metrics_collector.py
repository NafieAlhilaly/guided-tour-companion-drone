import psutil
import paho.mqtt.client as mqtt
import json
import time
import logging
import signal
from model import MQTTTopic

# Configuration - Update these to match your MQTT broker setup
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
PUBLISH_INTERVAL = 2  # Seconds between updates

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MetricsCollector")

class MetricsCollector:
    def __init__(self):
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.running = True

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("Connected to MQTT broker successfully")
        else:
            logger.error(f"Failed to connect, return code {reason_code}")

    def get_os_metrics(self):
        """Gathers system utilization metrics."""
        return {
            "cpu_utilization": psutil.cpu_percent(interval=None),
            "memory_utilization": psutil.virtual_memory().percent,
            "disk_utilization": psutil.disk_usage('/').percent,
            "timestamp": int(time.time() * 1000)  # Epoch in milliseconds for Flutter
        }

    def stop(self, *args):
        logger.info("Shutting down metrics collector...")
        self.running = False

    def run(self):
        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        try:
            self.client.on_connect = self.on_connect
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()

            # Initial call to initialize cpu_percent
            psutil.cpu_percent(interval=None)

            logger.info(f"Starting metrics broadcast on topic: {MQTTTopic.OS_METRICS_TOPIC.value}")

            while self.running:
                metrics = self.get_os_metrics()
                payload = json.dumps(metrics)
                print(f"Publishing OS metrics: {payload}")
                self.client.publish(MQTTTopic.OS_METRICS_TOPIC.value, payload)
                time.sleep(PUBLISH_INTERVAL)

        except Exception as e:
            logger.error(f"Collector loop error: {e}")
        finally:
            self.client.loop_stop()
            self.client.disconnect()

if __name__ == "__main__":
    collector = MetricsCollector()
    collector.run()