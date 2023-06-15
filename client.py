import asyncio
import time
import cv2
from aiortc import RTCPeerConnection
from aiortc.contrib.signaling import TcpSocketSignaling


async def receive_offer(signaling):

    print('Client now receiving offer at:', time.strftime('%X'))
    # Receive the offer from the server
    offer = await signaling.receive()
    print('offer is', offer)

    # Create a peer connection
    pc = RTCPeerConnection()

    @pc.on("track")
    async def on_track(track):
        print(f"Track received: {track.kind}")

        # Start receiving frames from the server
        while True:
            frame = await track.recv()

            # Display the received frame using OpenCV
            image = frame.to_ndarray()
            cv2.imshow('Received Frame', image)
            if cv2.waitKey(1) == 27:  # ESC key
                break

    # Set the remote description of the peer connection
    await pc.setRemoteDescription(offer)

    # Create an answer
    answer = await pc.createAnswer()

    # Set the local description of the peer connection
    await pc.setLocalDescription(answer)

    # Send the answer to the server
    await signaling.send(answer)

    # Close the peer connection
    await pc.close()


async def main():
    # Create a signaling instance for the server
    signaling = TcpSocketSignaling('localhost', 8080)

    print('host is', signaling._host)
    print('port no is', signaling._port)

    # Connect to the server and receive the offer
    await receive_offer(signaling)

    # Run the event loop until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass

    # Close the signaling connection
    signaling.close()


if __name__ == '__main__':
    asyncio.run(main())
