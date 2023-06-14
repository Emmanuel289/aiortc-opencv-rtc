import asyncio
import os
from aiohttp import web
from aiortc import RTCPeerConnection
from aiortc.contrib.signaling import TcpSocketSignaling


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
