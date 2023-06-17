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

        self.frame_queue = Queue(10)
        # Start a new mp.Process and send received frames to an mp.Queue
        self.process_a = Process(target=self.recv_frames,
                                 args=(self.frame_queue,))
        self.process_a.start()

    async def recv(self):
        print('inside recv()')

        while True:
            frame = await self.track.recv()
            image = frame.to_ndarray(format="bgr24")
            print('current image is', image)
            self.frame_queue.put(image)
            print('queue size is', self.frame_queue.qsize())

        # Debug -> CV not loading image
        # image = frame.to_ndarray(format="bgr24")
        # Create a window and display the image
        # cv.imshow("Bouncing Ball", image)
        # cv.waitKey(1)  # Wait until a key is pressed
        # cv.destroyAllWindows()  # Close the window

        # # Exit if 'q' is pressed
        # if cv.waitKey(1) & 0xFF == ord('q'):
        #     break

        # return frame

    def recv_frames(self, frame_queue):
        while True:
            image = frame_queue.get()
            # Process the frame as needed
            # Example: Display the image using OpenCV
            cv.imshow("Bouncing Ball", image)
            cv.waitKey(1)  # Wait until a key is pressed
            cv.destroyAllWindows()  # Close the window


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
