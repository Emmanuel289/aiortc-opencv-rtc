import asyncio
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


async def send_offer(signaling):
    # Create peer connection
    pc = RTCPeerConnection()

    # Create an offer
    offer = await pc.createOffer()

    # Set the local description of the peer connection
    await pc.setLocalDescription(offer)

    # Send offer to client
    await signaling.send(offer)


async def handle_client(reader, writer):
    # Create a signaling instance for the client
    signaling = TcpSocketSignaling(reader, writer)

    # Send the offer to the client
    send_offer(signaling)

    # Create a ball stream track
    ball_stream_track = BouncingBallTrack()

    # Create a peer connection
    pc = RTCPeerConnection()

    @pc.on("track")
    def on_track(track):
        print(f"Track {track.kind} received")

    # Add the ball to the peer connection
    pc.addTrack(ball_stream_track)

    # Set the remote description of the peer connection
    answer = await signaling.receive()
    await pc.setRemoteDescription(answer)

    # Close the signaling connection
    signaling.close()


async def main():
    server = await asyncio.start_server(handle_client, host='0.0.0.0', port=8080)

    addr = server.sockets[0].getsockname()

    print(f'Server started on {addr[0]}:{addr[1]}')

    async with server:
        await server.start_serving()


if __name__ == '__main__':
    asyncio.run(main())
