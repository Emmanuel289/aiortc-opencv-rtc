import asyncio
import cv2 as cv
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from av import VideoFrame
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
        app_log.info('inside client recv()')
        while True:

            frame = await self.track.recv()
            image = frame.to_ndarray(format="bgr24")
            frame_queue.put(image)


def process_frame(queue, ball_location):
    app_log.info('Processing frames...')

    while True:
        image = queue.get()
        app_log.info('queue size: %s', frame_queue.qsize())

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

        # Store the ball coordinates in multiprocessing.Value
        if ball_x is not None and ball_y is not None:
            ball_location = (ball_x, ball_y)
            app_log.info('Value stored is %s', ball_location)

        # Exit if 'q' is pressed
        if cv.waitKey(1) & 0xFF == ord('q'):
            break

    cv.destroyAllWindows()


async def display_ball_frames(pc, signaling):
    app_log.info("Display ball frames...")

    @pc.on("track")
    def on_track(track):
        app_log.info("Receiving %s" % track.kind)
        if track.kind == "video":
            pc.addTrack(ImageDisplayReceiver(track))

    # connect signaling
    await signaling.connect()

    # consume signaling
    while True:
        obj = await signaling.receive()
        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)

            if obj.type == "offer":
                # send answer
                app_log.info("Client received offer")
                await pc.setLocalDescription(await pc.createAnswer())
                await signaling.send(pc.localDescription)
        elif isinstance(obj, RTCIceCandidate):
            await pc.addIceCandidate(obj)
        elif obj is BYE:
            app_log.warning("Exiting")
            break


async def receive_offer_send_answer(pc, signaling):
    app_log.info("Receive Offer and Send Answer")

    @pc.on("track")
    def on_track(track):
        app_log.info("Receiving %s" % track.kind)

    # connect signaling
    await signaling.connect()

    # consume signaling
    while True:
        obj = await signaling.receive()
        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)

            if obj.type == "offer":
                # send answer
                # add_tracks()
                app_log.info("Client received offer")
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                app_log.info("Answer sent %s", answer.sdp)
                await signaling.send(pc.localDescription)
        elif isinstance(obj, RTCIceCandidate):
            await pc.addIceCandidate(obj)
        elif obj is BYE:
            app_log.warning("Exiting")
            break


if __name__ == "__main__":
    signaling = TcpSocketSignaling(HOST_IP, PORT_NO)

    peer_connection = RTCPeerConnection()
    loop = asyncio.get_event_loop()

    frame_queue = Queue(10)

    ball_location = Value('i', 0)
    process_a = Process(target=process_frame,
                        args=(frame_queue, ball_location))
    process_a.start()

    try:
        # loop.run_until_complete(
        # receive_offer_send_answer(peer_connection, signaling))
        loop.run_until_complete(
            display_ball_frames(peer_connection, signaling))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(peer_connection.close())
