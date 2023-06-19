import asyncio
import cv2 as cv
import numpy as np
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
    MediaStreamTrack,
)
import os
from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from multiprocessing import Process, Queue, Value
from logger import app_log


HOST_IP = os.environ.get('SERVER_HOST', '127.0.0.1')
PORT_NO = 8080

WIDTH = 640
HEIGHT = 480

frame_queue = Queue(20)


class ImageDisplayReceiver(MediaStreamTrack):
    """
    Media Stream Track for receiving and displaying images of a bouncing ball
    """

    kind = "video"

    def __init__(self, track):
        super().__init__()
        self.track = track

    async def recv(self):
        """
        Receives frames and converts them to ndarray format.
        """
        print('inside recv')
        while True:
            frame = await self.track.recv()
            image = frame.to_ndarray(format="bgr24")
            frame_queue.put(image)


def process_frame(queue, ball_location_x, ball_location_y) -> None:
    """
    Processes frames, performs ball detection, and stores the ball location coordinates.

    Args:
        queue (Queue): A queue to receive frames.
        ball_location_x (Value): Shared value for ball x-coordinate.
        ball_location_y (Value): Shared value for ball y-coordinate.
    Returns:
        None
    """
    app_log.info('Processing frames...')
    while True:

        try:
            image = queue.get()

        except queue.Empty:
            print('Empty queue')

        # Convert the image to grayscale for easier ball detection
        gray_image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

        # Perform ball detection using and apply thresholding to separate the ball from the background
        _, binary_image = cv.threshold(
            gray_image, 0, 255, cv.THRESH_BINARY_INV+cv.THRESH_OTSU)

        # Find contours in the binary image
        contours, _ = cv.findContours(
            binary_image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        # Initialize placeholder for ball coordinates
        ball_x = None
        ball_y = None
        # Process each contour
        for contour in contours:
            # Compute the center of each contour
            (x, y, w, h) = cv.boundingRect(contour)
            center_x = x + w // 2
            center_y = y + h // 2

            # Store the ball center coordinates
            ball_x = center_x
            ball_y = center_y

        # Store the ball coordinates as a multiprocessing.Value
        if ball_x is not None and ball_y is not None:
            ball_location_x.value, ball_location_y.value = ball_x, ball_y

        print("Current ball location to be dispatched to server\n",
              (ball_location_x.value, ball_location_y.value))

        # Exit if 'q' is pressed
        if cv.waitKey(1) & 0xFF == ord('q'):
            break

    cv.destroyAllWindows()


async def consume_signaling(pc, signaling) -> None:
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
                await pc.setLocalDescription(await pc.createAnswer())
                await signaling.send(pc.localDescription)
        elif isinstance(obj, RTCIceCandidate):
            await pc.addIceCandidate(obj)
        elif obj is BYE:
            app_log.warning('Exiting...')
            break


async def run_answer(pc, signaling) -> None:
    """
    Runs the answer path for handling data channels and sending responses.

    Args:
        pc (RTCPeerConnection): Peer connection object.
        signaling: Signaling object for communication.
    Returns:
        None
    """
    await signaling.connect()

    @pc.on("datachannel")
    def on_datachannel(channel):
        print("current channel is", channel.label)

        @channel.on("message")
        def on_message(message):
            print(f"channel({channel.label}): {message}")

            if isinstance(message, str) and message.startswith("Server"):
                # reply
                message = f"({ball_location_x.value}, {ball_location_y.value})"
                print("Client sending current ball location\n", message)
                channel.send(message)

    await consume_signaling(pc, signaling)


async def run_signaling(pc, signaling) -> None:
    """
    Runs the signaling path on the client side.

    Args:
        pc (RTCPeerConnection): Peer connection object.
        signaling: Signaling object for communication.
    Returns:
        None
    """
    app_log.info("Signaling path on client...")

    @pc.on("track")
    def on_track(track):
        app_log.info("Receiving %s" % track.kind)
        if track.kind == "video":
            pc.addTrack(ImageDisplayReceiver(track))

    # connect signaling
    await signaling.connect()

    await run_answer(pc, signaling)


if __name__ == "__main__":
    signaling = TcpSocketSignaling(HOST_IP, PORT_NO)

    peer_connection = RTCPeerConnection()
    loop = asyncio.get_event_loop()

    ball_location_x = Value('i', 0)
    ball_location_y = Value('i', 0)
    process_a = Process(target=process_frame,
                        args=(frame_queue, ball_location_x, ball_location_y))

    print(
        f"Initial ball location before processing frames \n x: {ball_location_x.value} \n y: {ball_location_y.value}")

    process_a.start()

    app_log.info('PID of process_a: %s' % process_a.pid)
    try:
        loop.run_until_complete(
            run_signaling(peer_connection, signaling))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(peer_connection.close())
