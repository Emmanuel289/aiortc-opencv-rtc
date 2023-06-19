import asyncio
import fractions
import time
import numpy as np
import cv2 as cv
from aiortc import (
    RTCPeerConnection,
    MediaStreamTrack,
    RTCSessionDescription,
    RTCIceCandidate,
)
from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from av import VideoFrame
from logger import app_log

VIDEO_CLOCK_RATE = 90000
VIDEO_PTIME = 1 / 30  # 30fps
VIDEO_TIME_BASE = fractions.Fraction(1, VIDEO_CLOCK_RATE)
HOST_IP = '127.0.0.1'
PORT_NO = 8080

# Define queue to store ball positions
locations_queue = asyncio.Queue()


class BouncingBallTrack(MediaStreamTrack):
    """
    Media Stream Track for generating 2D images of a bouncing ball
    """

    kind = "video"

    def __init__(self):
        super().__init__()
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

    def generate_moving_ball(self):
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

            server_ball_position = [self.ball_x, self.ball_y]
            locations_queue.put_nowait(server_ball_position)

            # Draw the ball on the canvas
            cv.circle(canvas, (self.ball_x, self.ball_y),
                      self.ball_radius, self.ball_color, -1)

            return canvas

    async def recv(self):
        ball_canvas = self.generate_moving_ball()
        frame = VideoFrame.from_ndarray(ball_canvas, format="bgr24")

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


def compute_errors(reported_location: tuple, server_queue: asyncio.Queue) -> float:
    """
    Computes the percentage error between the reported ball location and actual ball location.

    Args:
        reported_location (tuple): The reported ball location as (x, y) coordinates.
        server_queue (asyncio.Queue): The queue storing the actual ball locations.

    Returns:
        float: The percentage error.
    """
    actual_location = server_queue.get_nowait()
    print('Actual location:', tuple(actual_location))

    percentage_error_x = abs(
        actual_location[0] - reported_location[0]) / actual_location[0] * 100
    percentage_error_y = abs(
        actual_location[1] - reported_location[1]) / actual_location[1] * 100

    print("Error in ball's x coordinate: %.2f" % percentage_error_x, "%")
    print("Error in ball's y coordinate: %.2f" % percentage_error_y, "%")

    return round(percentage_error_x, 2), round(percentage_error_y, 2)


async def consume_signaling(pc, signaling):
    """
    Consumes signaling messages and handles different types of objects received.

    Args:
        pc (RTCPeerConnection): Peer connection object.
        signaling: Signaling object for communication.

    Returns:
        None
    """
    while True:
        obj = await signaling.receive()
        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)

            if obj.type == "offer":
                # send answer
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                app_log.info(
                    'Offer was received from server and answer was generated')
                await signaling.send(pc.localDescription)
        elif isinstance(obj, RTCIceCandidate):
            await pc.addIceCandidate(obj)
        elif obj is BYE:
            print("Exiting")
            break


async def run_offer(pc, signaling):
    app_log.info("Receiving live ball locations from client...")
    await signaling.connect()

    channel = pc.createDataChannel("live ball locations")

    async def wait_for_ball_location():
        while True:
            channel.send("Server is waiting for live ball locations...")
            await asyncio.sleep(1)

    @channel.on("open")
    def on_open():
        asyncio.ensure_future(wait_for_ball_location())

    @channel.on("message")
    def on_message(message):
        print(f"channel({channel.label}): {message}")
        if isinstance(message, str) and message:
            app_log.info(
                "Current ball location sent by client\n %s " % message)
            client_ball_position_x, client_ball_position_y = int(
                message.split(',')[0][1:]), int(message.split(',')[1][:-1])

            # compute error to the actual location of the ball
            compute_errors(
                (client_ball_position_x, client_ball_position_y), locations_queue)

    # send offer
    await pc.setLocalDescription(await pc.createOffer())
    await signaling.send(pc.localDescription)

    await consume_signaling(pc, signaling)


async def run_signaling(pc, signaling):
    app_log.info("Signaling path on server...")

    # connect signaling
    await signaling.connect()
    bouncing_ball = BouncingBallTrack()

    # add bouncing ball media track
    pc.addTrack(bouncing_ball)

    # Send pings
    await run_offer(pc, signaling)
    offer = await pc.createOffer()
    app_log.info('Offer was created and sent to client')
    await pc.setLocalDescription(offer)
    await signaling.send(pc.localDescription)


if __name__ == "__main__":
    signaling = TcpSocketSignaling(HOST_IP, PORT_NO)
    peer_connection = RTCPeerConnection()
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(run_signaling(peer_connection, signaling))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(peer_connection.close())
