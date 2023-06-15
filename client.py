import asyncio
import time
import cv2
from aiortc import RTCPeerConnection, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from logger import app_log


class VideoTransformTrack(MediaStreamTrack):

    kind = "video"

    def __init__(self):
        super().__init__()

    async def recv(self):
        frame = await self.track.recv()
        app_log.info("received frame is:", frame)
        image = frame.to_ndarray(format="bgr24")
        app_log.info("received image is:", image)
        cv2.imshow("Video", image)
        cv2.waitKey(1)
        return frame


async def run_client():
    signaling = TcpSocketSignaling('localhost', 8080)
    offer = await signaling.receive()
    curr_time = time.strftime('%X')
    app_log.info('Received offer from server at %s is:\n %s',
                 curr_time, offer.sdp)

    pc = RTCPeerConnection()
    pc.addTrack(VideoTransformTrack())

    await pc.setRemoteDescription(offer)

    while True:
        answer = await pc.createAnswer()
        if answer.type == "answer":
            app_log.info("Created answer is:\n %s", answer)
            await pc.setLocalDescription(answer)
            await signaling.send(answer)
            break

    await signaling.close()


if __name__ == "__main__":
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(run_client())
    asyncio.run(run_client())
