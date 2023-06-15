import asyncio
import time
import numpy as np
import cv2
from aiortc import RTCPeerConnection, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame


class BouncingBallTrack(MediaStreamTrack):
    """
    A single track of a bouncing ball within a stream.
    """

    kind = "video"

    def __init__(self) -> None:
        super().__init__()
        self.ball_radius = 20
        self.ball_color = (0, 255, 0)
        self.ball_pos_x = 0
        self.ball_speed = 5
        self.image_width = 640
        self.image_height = 480
        self.timestamp = 0

    async def recv(self) -> VideoFrame:
        """
        Receives the next video frame of the bouncing ball
        """
        # Create a blank image
        image = np.zeros(
            (self.image_height, self.image_width, 3), dtype=np.uint8)

        # Update ball position
        self.ball_pos_x += self.ball_speed
        if self.ball_pos_x < 0 or self.ball_pos_x > self.image_width - self.ball_radius:
            self.ball_speed *= -1

        # Draw the ball on the image
        cv2.circle(image, (self.ball_pos_x, self.image_height // 2),
                   self.ball_radius, self.ball_color, -1)

        # Convert the image to bytes
        image_bytes = cv2.imencode('.png', image)[1].tobytes()

        # Create a video frame from the image bytes
        timestamp = self._next_time_stamp()
        frame = VideoFrame(width=self.image_width, height=self.image_height,
                           data=image_bytes, timestamp=timestamp)

        return frame

    def _next_time_stamp(self):
        self.timestamp += 1
        return self.timestamp


async def offer():
    pc = RTCPeerConnection()

    offer = pc.createOffer()

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])

     # handle offer
    await pc.setRemoteDescription(offer)

    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):

    print('Client handler has been called at:', time.strftime('%X'))
    print('Sleep for one second')
    await asyncio.sleep(1)
    print('Handling client connection')


async def main():
    server = await asyncio.start_server(handle_client, host='localhost', port=8080)

    addr = server.sockets[0].getsockname()

    print(f'Server started on {addr[0]}:{addr[1]}')

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())
