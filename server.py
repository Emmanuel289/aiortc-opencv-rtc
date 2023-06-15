import asyncio
import time
import numpy as np
import cv2
from aiortc import RTCPeerConnection, MediaStreamTrack, RTCSessionDescription
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
from logger import app_log


class BouncingBallTrack(MediaStreamTrack):
    """
    A single track of a bouncing ball within a stream.
    """

    kind = "video"

    def __init__(self) -> None:
        super().__init__()
        self.ball_radius = 20
        self.ball_color = (0, 255, 0)
        self.ball_pos_x = 0
        self.ball_speed = 5
        self.image_width = 640
        self.image_height = 480
        self.timestamp = 0

    async def recv(self) -> VideoFrame:
        # Create a blank image
        image = np.zeros(
            (self.image_height, self.image_width, 3), dtype=np.uint8)

        # Update ball position
        self.ball_pos_x += self.ball_speed
        if self.ball_pos_x < 0 or self.ball_pos_x > self.image_width - self.ball_radius:
            self.ball_speed *= -1

        # Draw the ball on the image
        cv2.circle(image, (self.ball_pos_x, self.image_height // 2),
                   self.ball_radius, self.ball_color, -1)

        # timestamp = self._next_time_stamp()
        # Generate frame from image array
        frame = VideoFrame.from_ndarray(image, format="bgr24")

        return frame

    def _next_time_stamp(self):
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
