import asyncio
import cv2 as cv
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from av import VideoFrame
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
        app_log.info("track id: %s", track.id)

    def recv(self):
        frame = self.track.recv()
        app_log.info('frame is %s', frame)
        img = frame.to_ndarray(format="bgr24")
        app_log.info('seen image is %s', img)
        cv.imshow("Bouncing ball", img)
        return frame


async def receive_and_display_bouncing_ball(pc, signaling):
    """
    Receives and displays images of the bouncing ball
    """

    app_log.info('Receiving images of bouncing ball...')

    @pc.on("track")
    async def on_track(track):
        app_log.info("Receiving %s" % track.kind)
        if track.kind == "video":
            receiver = ImageDisplayReceiver(track)
            pc.addTrack(receiver)

    # connect signaling
    await signaling.connect()

    while True:
        obj = await signaling.receive()
        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)
            if obj.type == "offer":
                # send answer
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                await signaling.send(pc.localDescription)
        elif isinstance(obj, RTCIceCandidate):
            await pc.addIceCandidate(obj)
        elif obj is BYE:
            print("Exiting")
            break


async def receive_offer_send_answer(pc, signaling):
    """
    Receives SDP offer from server peer and sends an ACK SDP message
    """
    offer = await signaling.receive()
    app_log.info('Received offer from server ...')

    await pc.setRemoteDescription(offer)

    while True:
        obj = await pc.createAnswer()
        if obj.type == "answer":
            app_log.info("Created answer for server ")
            await pc.setLocalDescription(obj)
            await signaling.send(obj)
        break


if __name__ == "__main__":
    signaling = TcpSocketSignaling(HOST_IP, PORT_NO)
    peer_connection = RTCPeerConnection()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            receive_and_display_bouncing_ball(peer_connection, signaling))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(peer_connection.close())
        cv.destroyAllWindows()
