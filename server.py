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

# Step 3 Done -> Get and event loop and run coroutine


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

            # self.print_ball_coordinates()

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

        ball_canvas = self.generate_moving_ball()
        frame = VideoFrame.from_ndarray(ball_canvas, format="bgr24")

        pts, time_base = await self.next_timestamp()
        frame.pts = pts
        frame.time_base = time_base
        return frame

    def print_ball_coordinates(self):
        # Print the ball's coordinates
        print(
            f"Ball's position from server end: x={self.ball_x}, y={self.ball_y}"
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


def channel_log(channel, t, message):
    print("channel(%s) %s %s" % (channel.label, t, message))


def channel_send(channel, message):
    channel_log(channel, ">", message)
    channel.send(message)


async def consume_signaling(pc, signaling):
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


time_start = None


def current_stamp():
    global time_start

    if time_start is None:
        time_start = time.time()
        return 0
    else:
        return int((time.time() - time_start) * 1000000)


async def run_offer(pc, signaling):
    app_log.info("Server is sending HIs...")
    await signaling.connect()

    channel = pc.createDataChannel("chat")
    channel_log(channel, "-", "created by local party")

    async def send_pings():
        while True:
            channel_send(channel, "HI %d" % current_stamp())
            await asyncio.sleep(1)

    @channel.on("open")
    def on_open():
        asyncio.ensure_future(send_pings())

    @channel.on("message")
    def on_message(message):
        channel_log(channel, "<", message)
        print('message is', message)
        if isinstance(message, str) and message.startswith("BYE"):
            print("Success!")

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
    # Receive ball positions
    # await receive_ball_positions(pc, signaling)
    # send offer
    offer = await pc.createOffer()
    app_log.info('Offer was created and sent to client')
    await pc.setLocalDescription(offer)
    await signaling.send(pc.localDescription)


if __name__ == "__main__":
    signaling = TcpSocketSignaling(HOST_IP, PORT_NO)

    peer_connection = RTCPeerConnection()

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(
            run_signaling(peer_connection, signaling))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(peer_connection.close())
