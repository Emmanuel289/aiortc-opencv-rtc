import asyncio
from aiortc import RTCPeerConnection
from aiortc.contrib.signaling import TcpSocketSignaling


async def receive_offer(signaling):
    # Create a peer connection
    pc = RTCPeerConnection()

    # Receive the offer from the server
    offer = await signaling.receive()

    # Set the remote description of the peer connection
    await pc.setRemoteDescription(offer)

    # Create an answer
    await pc.createAnswer()


async def main():
    # Connect to the server
    host, port = await asyncio.open_connection(host='0.0.0.0', port=8080)

    # Create a signaling instance for the server
    signaling = TcpSocketSignaling(host=host, port=port)

    # Receive the offer from the server and send an answer
    await receive_offer(signaling)

    # Close the signaling connection
    signaling.close()
