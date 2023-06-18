import asyncio
import time
import cv2 as cv
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from multiprocessing import Process, Queue, Value
from logger import app_log

HOST_IP = '127.0.0.1'
PORT_NO = 8080

WIDTH = 640
HEIGHT = 480


class ImageDisplayReceiver(MediaStreamTrack):
    """
    Media Stream Track for receiving and displaying images of a bouncing ball
    """

    kind = "video"

    def __init__(self, track):
        super().__init__()
        self.track = track

    async def recv(self):
        while True:

            frame = await self.track.recv()
            image = frame.to_ndarray(format="bgr24")
            frame_queue.put(image)


def process_frame(queue, ball_location_x, ball_location_y):
    app_log.info('Processing frames...')

    while True:
        image = queue.get()
        # app_log.info('queue size: %s', frame_queue.qsize())

        # # Display the image
        # cv.imshow("Bouncing Ball", image)

        # Convert the image to grayscale for easier ball detection
        gray_image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

        # Perform ball detection using any suitable technique (e.g., thresholding, contour detection, etc.)
        # Modify the code below based on the specific ball detection method you want to use

        # Apply thresholding to separate the ball from the background
        _, binary_image = cv.threshold(
            gray_image, 0, 255, cv.THRESH_BINARY_INV+cv.THRESH_OTSU)

        # Find contours in the binary image
        contours, _ = cv.findContours(
            binary_image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        # Process each contour
        for contour in contours:
            # Compute the center of each contour
            (x, y, w, h) = cv.boundingRect(contour)
            center_x = x + w // 2
            center_y = y + h // 2

            # Store the ball center coordinates
            ball_x = center_x
            ball_y = center_y

            # Display the ball center

        # Store the ball coordinates as a  multiprocessing.Value
        if ball_x is not None and ball_y is not None:
            ball_location_x.value, ball_location_y.value = ball_x, ball_y

        # Exit if 'q' is pressed
        if cv.waitKey(1) & 0xFF == ord('q'):
            break

    cv.destroyAllWindows()


def channel_log(channel, t, message):
    print("channel(%s) %s %s" % (channel.label, t, message))


def channel_log_ball_position(*args):

    print("x coordinate is", args[0])
    print("y coordinate is", args[1])


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
                await pc.setLocalDescription(await pc.createAnswer())
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


# Data path for sending positions of moving ball to server


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
            print('Success!')


# Data path
async def run_answer(pc, signaling):
    app_log.info("Client is replying with BYEs...")
    await signaling.connect()

    @pc.on("datachannel")
    def on_datachannel(channel):
        channel_log(channel, "-", "created by remote party")

        @channel.on("message")
        def on_message(message):
            channel_log(channel, "<", message)

            if isinstance(message, str) and message.startswith("HI"):
                # reply
                channel_send(channel, "BYE" + message[3:])

    await consume_signaling(pc, signaling)


async def run_signaling(pc, signaling):
    app_log.info("Signaling path on client...")

    @pc.on("track")
    def on_track(track):
        app_log.info("Receiving %s" % track.kind)
        if track.kind == "video":
            pc.addTrack(ImageDisplayReceiver(track))

    # connect signaling
    await signaling.connect()

    # Send pong
    await run_answer(pc, signaling)

if __name__ == "__main__":
    signaling = TcpSocketSignaling(HOST_IP, PORT_NO)

    peer_connection = RTCPeerConnection()
    loop = asyncio.get_event_loop()

    frame_queue = Queue(10)

    ball_location_x = Value('i', 0)
    ball_location_y = Value('i', 0)
    process_a = Process(target=process_frame,
                        args=(frame_queue, ball_location_x, ball_location_y))
    print('ball location after', ball_location_x.value)

    process_a.start()

    try:
        loop.run_until_complete(
            run_signaling(peer_connection, signaling))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(peer_connection.close())
