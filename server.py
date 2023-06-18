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
        self.ball_radius = 10
        self.ball_color = (0, 0, 255)
        self.ball_speed = 10

        # Define canvas properties
        self.canvas_width = 640
        self.canvas_height = 480

        # Initialize ball position and velocity
        self.ball_x = self.canvas_width // 2
        self.ball_y = self.canvas_height // 2
        self.ball_dx = self.ball_speed
        self.ball_dy = self.ball_speed

    def generate_ball(self):
        while True:
            # Create a blank canvas
            canvas = np.zeros(
                (self.canvas_height, self.canvas_width, 3), dtype=np.uint8)
            canvas.fill(255)

            # Update ball position
            self.ball_x += self.ball_dx
            self.ball_y += self.ball_dy

            # Check if the ball hits the boundaries
            if self.ball_x + self.ball_radius >= self.canvas_width or self.ball_x - self.ball_radius <= 0:
                self.ball_dx *= -1  # Reverse horizontal velocity
            if self.ball_y + self.ball_radius >= self.canvas_height or self.ball_y - self.ball_radius <= 0:
                self.ball_dy *= -1  # Reverse vertical velocity

            print(
                f"Location of ball reported by server: x={self.ball_x}, y={self.ball_y}")

            # Draw the ball on the canvas
            cv.circle(canvas, (self.ball_x, self.ball_y),
                      self.ball_radius, self.ball_color, -1)

            # # Display the frame
            # cv.startWindowProcess()
            # cv.imshow("Bouncing Ball", canvas)

            # # Exit if 'q' is pressed
            # if cv.waitKey(1) & 0xFF == ord('q'):
            #     break

            # cv.destroyAllWindows()

            return canvas

    async def recv(self):
        print('Inside recv()')

        canvas = self.generate_ball()
        frame = VideoFrame.from_ndarray(canvas, format="bgr24")

        pts, time_base = await self.next_timestamp()
        frame.pts = pts
        frame.time_base = time_base
        return frame

        # while True:
        #     # Create a blank canvas
        #     canvas = np.zeros(
        #         (self.canvas_height, self.canvas_width, 3), dtype=np.uint8)
        #     canvas.fill(255)

        #     self.update_ball_position()
        #     self.print_ball_coordinates()
        #     # Draw the ball on the canvas
        #     cv.circle(canvas, (self.ball_x, self.ball_y),
        #               self.ball_radius, self.ball_color, -1)

        #     frame = VideoFrame.from_ndarray(canvas, format="bgr24")

        #     pts, time_base = await self.next_timestamp()
        #     frame.pts = pts
        #     frame.time_base = time_base
        #     return frame

    def update_ball_position(self):
        # Update ball position
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy

        # Check if the ball hits the boundaries
        if (
            self.ball_x + self.ball_radius >= self.canvas_width
            or self.ball_x - self.ball_radius <= 0
        ):
            self.ball_dx *= -1  # Reverse horizontal velocity
        if (
            self.ball_y + self.ball_radius >= self.canvas_height
            or self.ball_y - self.ball_radius <= 0
        ):
            self.ball_dy *= -1  # Reverse vertical velocity

    def print_ball_coordinates(self):
        # Print the ball's coordinates
        print(
            f"Location of ball reported by server: x={self.ball_x}, y={self.ball_y}"
        )

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
