import asyncio
from queue import Queue
import numpy as np
import cv2 as cv
from aiortc import RTCPeerConnection, MediaStreamTrack, RTCSessionDescription
from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from av.frame import Frame
from av import VideoFrame
from logger import app_log

HOST_IP = '127.0.0.1'
PORT_NO = 8080


class BouncingBallTrack(MediaStreamTrack):
    """
    Media Stream Track for generating 2D images of a bouncing ball
    """

    kind = "video"

    def __init__(self):
        super().__init__()
        self.ball_radius = 20
        self.ball_color = (0, 255, 0)
        self.width = 640
        self.height = 480
        self.ball_x = self.width // 2
        self.ball_y = self.height // 2
        self.velocity_x = 5
        self.velocity_y = 5
        self.timestamp = 0
        self.queue = Queue(100)

    def generate_frames(self):
        # Create a blank image frame
        image = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Draw the ball on the frame
        cv.circle(image, (self.ball_x, self.ball_y),
                  self.ball_radius, self.ball_color, -1)
        # Display the frame
        cv.imshow("Bouncing Ball", image)
        while True:

            # Update ball position
            self.ball_x += self.velocity_x
            self.ball_y += self.velocity_y

            # Check ball boundaries
            if self.ball_x + self.ball_radius >= self.width or self.ball_x - self.ball_radius <= 0:
                self.velocity_x *= -1
            if self.ball_y + self.ball_radius >= self.height or self.ball_y - self.ball_radius <= 0:
                self.velocity_y *= -1

            # Enqueue image with updated coordinates
            app_log.info('image is %s', image)
            self.queue.put(image)

    async def recv(self):
        app_log.info('item in queue is %s', self.queue.get())
        app_log.info('Receiving the next frame...')
        image = self.queue.get()
        app_log.info('image is %s', image)
        frame = VideoFrame.from_ndarray(image, format='bgr24')
        app_log.info('Frame is: %s', frame)
        pts, time_base = await self.next_timestamp()
        frame.pts = pts
        frame.time_base = time_base
        return frame


async def send_offer_receive_answer(pc, signaling):
    """
    Creates an SDP offer and sends to client peer. Also receives answer 
    from client and logs an ACK message
    """
    await signaling.connect()  # connect signaling

    pc = RTCPeerConnection()
    bouncing_ball = BouncingBallTrack()

    pc.addTrack(bouncing_ball)  # add bouncing ball media track

    # create offer and send
    app_log.info('Creating offer...')
    offer = await pc.createOffer()
    app_log.info('Offer created ...')
    await pc.setLocalDescription(offer)
    app_log.info('Offer sent ...')
    await signaling.send(pc.localDescription)

    # consume signaling
    while True:
        obj = await signaling.receive()
        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)

            if obj.type == "answer":
                answer = RTCSessionDescription(sdp=obj.sdp, type='answer')
            app_log.info(
                "Answer received ...")
            break


async def send_bouncing_ball(pc, signaling):
    """
    Send images of the bouncing ball to the client peer
    """
    app_log.info('Sending images of the bouncing ball ...')

    sender = BouncingBallTrack()
    pc.addTrack(sender)

    await signaling.connect()

    await pc.setLocalDescription(await pc.createOffer())
    await signaling.send(pc.localDescription)

    while True:
        obj = await signaling.receive()
        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)
        elif obj is BYE:
            app_log.info("Exiting ...")
            break

if __name__ == "__main__":
    signaling = TcpSocketSignaling(HOST_IP, PORT_NO)
    peer_connection = RTCPeerConnection()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            send_bouncing_ball(peer_connection, signaling))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(peer_connection.close())
