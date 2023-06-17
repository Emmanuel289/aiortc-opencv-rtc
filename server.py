import asyncio
import fractions
from queue import Queue
import time
import numpy as np
import cv2 as cv
from aiortc import (
    RTCPeerConnection,
    MediaStreamTrack,
    RTCSessionDescription,
)
from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from av import VideoFrame
from logger import app_log

VIDEO_CLOCK_RATE = 90000
VIDEO_PTIME = 1 / 30  # 30fps
VIDEO_TIME_BASE = fractions.Fraction(1, VIDEO_CLOCK_RATE)
HOST_IP = '127.0.0.1'
PORT_NO = 8080

# Step 3 Done -> Get and event loop and run coroutine


class BouncingBallTrack(MediaStreamTrack):
    """
    Media Stream Track for generating 2D images of a bouncing ball
    """

    kind = "video"

    def __init__(self):
        super().__init__()  # did not forget this!

    async def recv(self):
        app_log.info('Inside recv()')
        ball_radius = 10
        ball_color = (0, 0, 255)
        ball_speed = 1

        # Define canvas properties
        canvas_width = 640 * 3
        canvas_height = 480 * 3

        # Initialize ball position and velocity
        ball_x = canvas_width // 2
        ball_y = canvas_height // 2
        ball_dx = ball_speed
        ball_dy = ball_speed

        while True:
            # Create a blank canvas
            canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
            canvas.fill(255)

            # Update ball position
            ball_x += ball_dx
            ball_y += ball_dy

            # Check if the ball hits the boundaries
            if ball_x + ball_radius >= canvas_width or ball_x - ball_radius <= 0:
                ball_dx *= -1  # Reverse horizontal velocity
            if ball_y + ball_radius >= canvas_height or ball_y - ball_radius <= 0:
                ball_dy *= -1  # Reverse vertical velocity

            # Draw the ball on the canvas
            cv.circle(canvas, (ball_x, ball_y), ball_radius, ball_color, -1)

            frame = VideoFrame.from_ndarray(canvas, format="bgr24")

            pts, time_base = await self.next_timestamp()
            frame.pts = pts
            frame.time_base = time_base
            return frame

    async def next_timestamp(self):
        if hasattr(self, "_timestamp"):
            self._timestamp += int(VIDEO_PTIME * VIDEO_CLOCK_RATE)
            wait = self._start + (self._timestamp /
                                  VIDEO_CLOCK_RATE) - time.time()
            await asyncio.sleep(wait)
        else:
            self._start = time.time()
            self._timestamp = 0
        return self._timestamp, VIDEO_TIME_BASE


async def send_offer_receive_answer(pc, signaling):
    """
    Creates an SDP offer and sends to client peer. Also receives answer 
    from client and logs an ACK message
    """
    bouncing_ball = BouncingBallTrack()

    pc.addTrack(bouncing_ball)  # add bouncing ball media track

    # connect signaling

    await signaling.connect()

    # create offer and send
    offer = await pc.createOffer()
    app_log.info('Offer created ...')
    await pc.setLocalDescription(offer)
    await signaling.send(pc.localDescription)

    # consume signaling
    while True:
        obj = await signaling.receive()
        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)

            if obj.type == "answer":
                app_log.info(
                    "Answer %s", obj.sdp)

if __name__ == "__main__":
    signaling = TcpSocketSignaling(HOST_IP, PORT_NO)

    peer_connection = RTCPeerConnection()

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(
            send_offer_receive_answer(peer_connection, signaling))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(peer_connection.close())
