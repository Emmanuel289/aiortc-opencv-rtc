import asyncio
import cv2 as cv
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from av import VideoFrame
from multiprocessing import Process, Queue
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
        print('inside client recv()')
        while True:

            frame = await self.track.recv()
            image = frame.to_ndarray(format="bgr24")
            frame_queue.put(image)


def process_frame(queue):
    print('inside process_frame')

    while True:
        image = queue.get()
        print('queue size inside process_frame is', frame_queue.qsize())

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

            # Display the ball center
            print(
                f"Ball location reported by client: x={center_x}, y={center_y}")

        # Exit if 'q' is pressed
        if cv.waitKey(1) & 0xFF == ord('q'):
            break

    cv.destroyAllWindows()


async def display_ball_frames(pc, signaling):
    print("Display ball frames...")

    @pc.on("track")
    def on_track(track):
        print("Receiving %s" % track.kind)
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
                print("Received offer")
                await pc.setLocalDescription(await pc.createAnswer())
                await signaling.send(pc.localDescription)
        elif isinstance(obj, RTCIceCandidate):
            await pc.addIceCandidate(obj)
        elif obj is BYE:
            print("Exiting")
            break


async def receive_offer_send_answer(pc, signaling):
    print("Receive Offer and Send Answer")

    @pc.on("track")
    def on_track(track):
        print("Receiving %s" % track.kind)

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
                print("Received offer")
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                print("Answer sent %s", answer.sdp)
                await signaling.send(pc.localDescription)
        elif isinstance(obj, RTCIceCandidate):
            await pc.addIceCandidate(obj)
        elif obj is BYE:
            print("Exiting")
            break


if __name__ == "__main__":
    signaling = TcpSocketSignaling(HOST_IP, PORT_NO)

    peer_connection = RTCPeerConnection()
    loop = asyncio.get_event_loop()
    frame_queue = Queue(10)
    process_a = Process(target=process_frame, args=(frame_queue,))
    process_a.start()
    print("PID:", process_a.pid)

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
