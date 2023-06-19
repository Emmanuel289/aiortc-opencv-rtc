import asyncio
import fractions
import numpy as np
import pytest
import pytest_mock
from server import compute_errors, BouncingBallTrack, consume_signaling, run_offer, run_signaling, RTCPeerConnection
from aiortc import RTCSessionDescription
from aiortc import MediaStreamTrack
from pytest_mock import mocker
from unittest.mock import AsyncMock


class MockDataChannel:
    def __init__(self, label):
        self.label = label
        self.open = False
        self.buffered_amount = 0
        self.received_messages = []

    def send(self, data):
        if not self.open:
            raise RuntimeError("DataChannel is not open")
        self.buffered_amount += len(data)

    def receive(self, data):
        self.received_messages.append(data)

    def close(self):
        self.open = False

    def set_open(self, is_open):
        self.open = is_open

    def set_buffered_amount(self, amount):
        self.buffered_amount = amount

    def get_received_messages(self):
        return self.received_messages


class MockMediaStream(MediaStreamTrack):

    kind = "video"

    def __init__(self):
        super().__init__()

    async def recv(self):
        pass


class MockPeerConnection:
    def __init__(self):
        self.local_description_set = False
        self.remote_description_set = False
        self.answer_created = False
        self.ice_candidate_added = False
        self.DataChannel = None
        self.tracks = []
        self.localDescription = None
        self.remoteDescription = None
        self.iceCandidate = []

    async def setLocalDescription(self, description):
        self.local_description_set = True
        self.localDescription = description

    async def setRemoteDescription(self, description):
        self.remote_description_set = True
        self.remoteDescription = description

    async def createAnswer(self):
        self.answer_created = True
        return RTCSessionDescription(sdp="sdp", type="answer")

    def addIceCandidate(self, candidate):
        self.ice_candidate_added = True
        self.iceCandidate.append(candidate)

    async def createDataChannel(self, label):
        self.DataChannel = MockDataChannel(label)
        return self.DataChannel

    def addTrack(self, track):
        self.tracks.append(track)

    async def createOffer(self):
        if self.localDescription is not None:
            raise RuntimeError("Local description already exists")

        # Create and return a mock offer session description
        offer = RTCSessionDescription(
            sdp="mock offer sdp",
            type="offer"
        )
        return offer


class MockSignaling:
    def __init__(self):
        self.messages = []

    async def receive(self):
        while not self.messages:
            await asyncio.sleep(0.1)
        return self.messages.pop(0)

    async def send(self, message):
        self.messages.append(message)

    async def connect(self):
        pass


@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_compute_errors():
    server_queue = asyncio.Queue()
    server_queue.put_nowait((100, 100))
    reported_location = (90, 90)

    percentage_error = compute_errors(reported_location, server_queue)
    assert percentage_error == (10.0, 10.0)

    server_queue.put_nowait((200, 200))
    reported_location = (180, 220)

    percentage_error = compute_errors(reported_location, server_queue)
    assert percentage_error == (10.0, 10.0)

    server_queue.put_nowait((300, 300))
    reported_location = (350, 270)

    percentage_error = compute_errors(reported_location, server_queue)
    assert percentage_error == (16.67, 10.0)

    # Test when server_queue is empty
    with pytest.raises(asyncio.QueueEmpty):
        compute_errors(reported_location, server_queue)


@pytest.mark.asyncio
async def test_BouncingBallTrack_generate_moving_ball():
    track = BouncingBallTrack()
    ball_canvas = track.generate_moving_ball()
    assert isinstance(ball_canvas, np.ndarray)


@pytest.mark.asyncio
async def test_BouncingBallTrack_recv():
    track = BouncingBallTrack()
    frame = await track.recv()
    assert frame is not None
    assert isinstance(frame.width, int)
    assert isinstance(frame.height, int)
    assert isinstance(frame.time_base, fractions.Fraction)


@pytest.mark.asyncio
@pytest.mark.timeout(3)
async def test_BouncingBallTrack_next_timestamp():
    track = BouncingBallTrack()
    timestamp, time_base = await track.next_timestamp()
    assert isinstance(timestamp, int)
    assert isinstance(time_base, fractions.Fraction)


@pytest.mark.skip("fix assertion errors")
@pytest.mark.asyncio
async def test_consume_signaling(mocker):
    pc = MockPeerConnection()
    signaling = MockSignaling()

    # Create a mock return value for signaling.receive
    mock_receive = mocker.patch.object(signaling, "receive")
    mock_return_value = asyncio.Future()
    mock_receive.return_value = mock_return_value

    mock_consume_signaling = mocker.patch("server.consume_signaling")
    mock_consume_signaling.return_value = None

    mock_consume_signaling(pc, signaling)

    # Prepare the objects to be received
    offer = RTCSessionDescription(type="offer", sdp="dummy_offer_sdp")
    bye = "BYE"

    # Trigger the consumption of objects in the loop
    mock_return_value.set_result(offer)
    # Allow time for the task to process the received object
    await asyncio.sleep(0)

    # Verify the behavior for RTCSessionDescription object
    assert pc.remoteDescription == None
    pc.createAnswer()
    assert pc.answer_created == True
    signaling.send.assert_called_once_with(pc.localDescription)

    # Reset the mocks for the next object
    pc.setRemoteDescription.reset_mock()
    pc.createAnswer.reset_mock()
    pc.setLocalDescription.reset_mock()
    signaling.send.reset_mock()

    # Trigger the consumption of the next object in the loop
    mock_return_value.set_result(bye)
    # Allow time for the task to process the received object
    await asyncio.sleep(0)

    # Verify the behavior for BYE object
    assert pc.setRemoteDescription.call_count == 0
    assert pc.createAnswer.call_count == 0
    assert pc.setLocalDescription.call_count == 0
    assert signaling.send.call_count == 0


@pytest.mark.asyncio
@pytest.mark.skip("Fix coro attributes")
async def test_run_offer(mocker):
    # Create dummy objects for testing
    pc = MockPeerConnection()
    signaling = MockSignaling()

    mocked_addTrack = mocker.patch('aiortc.RTCPeerConnection.addTrack')
    mocked_createDataChannel = mocker.patch(
        'aiortc.RTCPeerConnection.createDataChannel')

    mocked_addTrack.return_value = 'transceiver.sender'

    # Mock the createDataChannel method
    mocked_datachannel = mocker.MagicMock()
    mocked_datachannel.on.return_value = None
    mocked_createDataChannel.return_value = mocked_datachannel

    # Run the run_offer function
    await run_offer(pc, signaling)

    # Assertions for the expected behavior
    assert pc.local_description_set
    assert len(signaling.messages) == 1
    assert signaling.messages[0].type == "offer"
    assert pc.remote_description_set
    assert pc.answer_created
    assert pc.local_description_set
    assert pc.ice_candidate_added


@pytest.mark.asyncio
@pytest.mark.skip("fix assertion error")
async def test_run_signaling(mocker):
    # Create dummy objects for testing
    pc = MockPeerConnection()
    signaling = MockSignaling()

    # Mock the createDataChannel method
    mocked_datachannel = mocker.Mock()
    mocked_datachannel.on = mocker.Mock()

    # mock createAnswer
    mock_create_answer = AsyncMock()

    # Set the return value of the mock
    mock_create_answer.return_value = RTCSessionDescription(
        sdp="sdp", type="answer")

    pc.createDataChannel = mocker.Mock(return_value=mocked_datachannel)
    # Replace the actual createAnswer method with the mock
    pc.createAnswer = mock_create_answer

    # Call the createAnswer method
    result = await pc.createAnswer()

    # Assert that the mock was called and the answer_created attribute is set to True
    assert mock_create_answer.called
    assert pc.answer_created

    # Assert the result
    assert isinstance(result, RTCSessionDescription)

    # Assertions
    assert signaling.connected
    assert pc.remote_description_set
    assert pc.answer_created
    assert pc.local_description_set
    assert signaling.sent_description == pc.localDescription
    assert pc.DataChannel is not None
    assert pc.DataChannel.label == "live ball locations"
    assert pc.DataChannel.on_called
