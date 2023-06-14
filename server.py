import asyncio
import numpy as np
import cv2
from aiortc import RTCPeerConnection, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling


class BallStreamTrack(MediaStreamTrack):

    def __init__(self) -> None:
        super().__init__()


def generate_bouncing_ball():
    """
    Generate a continuous 2D image of a ball bouncing  across a screen
    and send to client
    """

    ball_radius = 20
    ball_color = (0, 255, 0)
    ball_pos_x = 0
    ball_speed = 5
    image_width = 640
    image_height = 480

    while True:
        # Create a blank image
        image = np.zeros((image_height, image_width, 3), dtype=np.uint8)

        # Update ball position
        ball_pos_x += ball_speed
        if ball_pos_x < 0 or ball_pos_x > image_width - ball_radius:
            ball_speed *= - 1

        # Draw the ball on the image
        cv2.circle(image, (ball_pos_x, image_height // 2),
                   ball_radius, ball_color, -1)

        # Convert the image to bytes
        image_bytes = cv2.imencode('.png', image)[1].tobytes()
        return image_bytes


async def send_offer(signaling):
    # Create peer connection
    pc = RTCPeerConnection()

    # Create an offer
    offer = await pc.createOffer()

    # Connect signaling
    await signaling.connect()

    # Set the local description of the peer connection
    await pc.setLocalDescription(offer)

    # Send offer to client
    await signaling.send(offer)

    # Send images of the bouncing ball to the client
    await generate_bouncing_ball(signaling)

    # Delay a while before sending next image
    await asyncio.sleep(0.01)

    #


async def handle_client(host, port):
    # Create a signaling instance for the client
    signaling = TcpSocketSignaling(host=host, port=port)

    # Send the offer to the client
    send_offer(signaling)

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
