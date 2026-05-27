import asyncio
import os
import logging
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

from ffmpeg_capture import FFmpegCapture, FFmpegConfig
from webrtc_track import CameraVideoTrack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PLAYER_HTML="""<!DOCTYPE html>
                <html>
                <head>
                    <title>WebRTC Video Stream</title>
                    <style>
                        body { font-family: Arial; max-width: 800px; margin: 40px auto; }
                        #video { width: 100%; border: 1px solid #ccc; background: #000; }
                        .controls { margin: 20px 0; }
                        button { padding: 10px 20px; font-size: 16px; cursor: pointer; }
                        #status { padding: 10px; margin: 10px 0; border-radius: 4px; font-weight: bold; }
                        .connected { background: #d4edda; color: #155724; }
                        .disconnected { background: #f8d7da; color: #721c24; }
                        .stats { margin-top: 20px; padding: 10px; background: #f0f0f0; border-radius: 4px; font-family: monospace; font-size: 12px; }
                    </style>
                </head>
                <body>
                    <h1>Drone WebRTC Stream</h1>
                    
                    <video id="video" autoplay playsinline width="640" height="480"></video>
                    
                    <div class="controls">
                        <button onclick="startStream()">Connect</button>
                        <button onclick="stopStream()">Disconnect</button>
                    </div>
                    
                    <div id="status" class="disconnected">Status: Ready</div>
                    
                    <div class="stats">
                        <div>Frames: <span id="frames">0</span></div>
                        <div>Connection: <span id="connection">idle</span></div>
                        <div>Bitrate: <span id="bitrate">0</span> kbps</div>
                    </div>

                    <script src="https://cdn.jsdelivr.net/npm/webrtc-adapter@8.1.1/out/adapter.js"></script>
                    <script>
                        let pc = null;
                        let statsInterval = null;

                        async function startStream() {
                            try {
                                updateStatus('Connecting...', false);
                                
                                pc = new RTCPeerConnection({
                                    iceServers: []
                                });

                                // Request to receive video from the server
                                pc.addTransceiver('video', { direction: 'recvonly' });

                                pc.ontrack = (event) => {
                                    console.log('Track received');
                                    document.getElementById('video').srcObject = event.streams[0];
                                };

                                pc.onconnectionstatechange = () => {
                                    console.log('Connection state:', pc.connectionState);
                                    document.getElementById('connection').textContent = pc.connectionState;
                                    
                                    if (pc.connectionState === 'connected') {
                                        updateStatus('Connected', true);
                                        startStatsMonitor();
                                    } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
                                        updateStatus('Connection failed', false);
                                        stopStream();
                                    }
                                };

                                const offer = await pc.createOffer();
                                await pc.setLocalDescription(offer);

                                const response = await fetch('/offer', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        sdp: pc.localDescription.sdp,
                                        type: pc.localDescription.type
                                    })
                                });

                                if (!response.ok) {
                                    throw new Error(`Server error: ${response.status}`);
                                }

                                const answer = await response.json();
                                await pc.setRemoteDescription(new RTCSessionDescription(answer));

                            } catch (error) {
                                console.error('Error:', error);
                                updateStatus('Error: ' + error.message, false);
                            }
                        }

                        async function stopStream() {
                            if (pc) {
                                pc.close();
                                pc = null;
                            }
                            if (statsInterval) {
                                clearInterval(statsInterval);
                            }
                            document.getElementById('video').srcObject = null;
                            updateStatus('Disconnected', false);
                        }

                        function updateStatus(message, isConnected) {
                            const el = document.getElementById('status');
                            el.textContent = 'Status: ' + message;
                            el.className = isConnected ? 'connected' : 'disconnected';
                        }

                        async function startStatsMonitor() {
                            statsInterval = setInterval(async () => {
                                if (!pc) return;
                                
                                try {
                                    const stats = await pc.getStats();
                                    let bytesReceived = 0;
                                    let packetsReceived = 0;
                                    
                                    stats.forEach(report => {
                                        if (report.type === 'inbound-rtp' && report.mediaType === 'video') {
                                            bytesReceived = report.bytesReceived;
                                            packetsReceived = report.packetsReceived;
                                        }
                                    });
                                    
                                    // Simple bitrate calculation
                                    if (window.lastBytes !== undefined) {
                                        const bitrate = Math.round(((bytesReceived - window.lastBytes) * 8) / 1000);
                                        document.getElementById('bitrate').textContent = bitrate;
                                    }
                                    window.lastBytes = bytesReceived;
                                    document.getElementById('frames').textContent = packetsReceived;
                                } catch (e) {
                                    console.error('Stats error:', e);
                                }
                            }, 1000);
                        }

                        // Auto-connect on load
                        window.addEventListener('load', () => {
                            console.log('Page loaded');
                        });
                    </script>
                </body>
                </html>
                """

class WebRTCServer:
    def __init__(self):
        self.ffmpeg = FFmpegCapture(FFmpegConfig())
        self.pcs = set()
        self.video_track = None
    
    async def handle_offer(self, request):
        try:
            params = await request.json()
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
            
            # Ensure video track exists
            if self.video_track is None:
                logger.error("Video track not initialized")
                return web.json_response({"error": "Video track not ready"}, status=500)
            
            pc = RTCPeerConnection()
            self.pcs.add(pc)
            
            logger.info(f"Connection from {request.remote}")
            
            @pc.on("connectionstatechange")
            async def on_state_change():
                logger.info(f"State: {pc.connectionState}")
                if pc.connectionState == "failed":
                    await pc.close()
                    self.pcs.discard(pc)

            # Explicitly handle data channels if offered. Flutter/Google WebRTC often 
            # requires the SCTP section to be present in the answer if it was in the offer.
            @pc.on("datachannel")
            def on_datachannel(channel):
                logger.info(f"Data channel received: {channel.label}")

            await pc.setRemoteDescription(offer)

            # Respond to all transceivers created by the offer.
            # We remove the 'break' to ensure all media sections are properly reconciled
            # in the Answer SDP, avoiding BUNDLE group mismatches.
            for transceiver in pc.getTransceivers():
                if transceiver.kind == "video":
                    pc.addTrack(self.video_track)
                    logger.info(f"Video track attached to transceiver (MID: {transceiver.mid})")

            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            logger.info("Stream started")
            
            return web.json_response({
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            })
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return web.json_response({"error": str(e)}, status=400)
    
    async def handle_health(self, request):
        return web.json_response({
            "status": "ok",
            "connections": len(self.pcs),
            "frames": self.video_track.frame_count if self.video_track else 0,
        })
    
    async def handle_player(self, request):
        return web.Response(body=PLAYER_HTML, content_type="text/html")
    
    async def start(self, host="0.0.0.0", port=8080):
        if not self.ffmpeg.start():
            logger.error("FFmpeg failed")
            return
        
        self.video_track = CameraVideoTrack(self.ffmpeg)
        
        app = web.Application()
        app.router.add_post("/offer", self.handle_offer)
        app.router.add_get("/health", self.handle_health)
        app.router.add_get("/player", self.handle_player)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"🚀 WebRTC server: http://{host}:{port}")
        logger.info(f"   Resolution: {self.ffmpeg.config.width}x{self.ffmpeg.config.height}")
        logger.info(f"   FPS: {self.ffmpeg.config.fps}")
        logger.info(f"   Device: {self.ffmpeg.config.video_device}")
        
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            self.ffmpeg.stop()
            for pc in self.pcs:
                await pc.close()
            logger.info("Shutdown")

async def main():
    server = WebRTCServer()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
