import asyncio
import time
import cv2
from aiortc import RTCPeerConnection, MediaStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from logger import app_log

WIDTH = 640
HEIGHT = 480


class DispayVideoStreamTrack(MediaStreamTrack):

    kind = "video"

    def __init__(self):
        super().__init__()

    async def recv(self):
        while True:
            frame = await self.frames.get()

            # Convert the frame to BGR
            bgr_frame = cv2.cvtColor(frame.to_ndarray(
                format="bgr24"), cv2.COLOR_RGB2BGR)

            # Display the frame
            cv2.imshow("Video Stream", bgr_frame)
            cv2.waitKey(1)

            # Convert the frame to bytes
            frame_bytes = bgr_frame.tobytes()

            # Yield the frame for transmission
            pts, time_base = self.next_timestamp()
            yield cv2.UMat.get(frame_bytes), pts, time_base


async def run_client():
    signaling = TcpSocketSignaling('localhost', 8080)
    offer = await signaling.receive()
    curr_time = time.strftime('%X')
    app_log.info('Received offer from server at %s is:\n %s',
                 curr_time, offer.sdp)

    pc = RTCPeerConnection()
    pc.addTrack(DispayVideoStreamTrack())

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

    # Initialize OpenCV window - DEBUG
    # cv2.namedWindow("Video Stream", cv2.WINDOW_NORMAL)
    # cv2.resizeWindow("Video Stream", WIDTH, HEIGHT)

    asyncio.run(run_client())

    # Close OpenCV window - DEBUG
    # cv2.destroyAllWindows()
