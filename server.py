import asyncio
import time
import numpy as np
import cv2
from aiortc import RTCPeerConnection, MediaStreamTrack, RTCSessionDescription
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
from logger import app_log

WIDTH = 640
HEIGHT = 480
FPS = 30

BALL_RADIUS = 20
BALL_COLOR = (0, 255, 0)


class BouncingBallTrack(MediaStreamTrack):
    """
    Creates a bouncing ball media stream track
    """

    kind = "video"

    def __init__(self):
        super().__init__()

        self.ball_x = WIDTH // 2
        self.ball_y = HEIGHT // 2
        self.velocity_x = 5
        self.velocity_y = 5
        self.timestamp = 0

        self.frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

    async def recv(self):
        while True:
            await asyncio.sleep(1 / FPS)

            self.ball_x += self.velocity_x
            self.ball_y += self.velocity_y

            if self.ball_x + BALL_RADIUS >= WIDTH or self.ball_x - BALL_RADIUS <= 0:
                self.velocity_x *= -1
            if self.ball_y + BALL_RADIUS >= HEIGHT or self.ball_y - BALL_RADIUS <= 0:
                self.velocity_y *= -1

            self.frame.fill(0)
            cv2.circle(self.frame, (self.ball_x, self.ball_y),
                       BALL_RADIUS, BALL_COLOR, -1)

            # Convert the frame to RGB
            rgb_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)

            # Convert the frame to bytes
            frame_bytes = rgb_frame.tobytes()

            # Yield the frame for transmission
            pts, time_base = self._next_timestamp()
            frame = cv2.UMat(rgb_frame)
            yield cv2.UMat.get(frame), pts, time_base

    def _next_timestamp(self):
        self.timestamp += 1
        return self.timestamp


async def run_server():
    pc = RTCPeerConnection()
    signaling = TcpSocketSignaling('localhost', 8080)
    await signaling.connect()
    pc.addTrack(BouncingBallTrack())

    # handle offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    await signaling.send(offer)

    while True:
        message = await signaling.receive()
        if message.type == 'answer':
            answer = RTCSessionDescription(sdp=message.sdp, type='answer')
            curr_time = time.strftime('%X')
            app_log.info(
                "Received answer from client at %s:\n %s ", curr_time, answer.sdp)
            break

    await signaling.close()


if __name__ == "__main__":
    asyncio.run(run_server())
