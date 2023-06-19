# Peer-to-Peer RTC with aiortc and OpenCV

This project demonstrates RTC with aiortc and OpenCV using an application that showcases TCP signaling, frame transport, and messaging between peers on a local network. The application consists of a client-side and a server-side component. The server generates continuous frames of 2D images of a bouncing ball, which it transmits to the client for display on a screen. TCP socket signaling is used to establish a connection between the client and the server. Additionally, frame transport and data channel messaging is used to exchange the moving images and positions of the bouncing ball between the server and the client. The server also computes and prints the errors between the ball's positions reported by the client and the actual positions of the ball.

## Project Structure

The project structure is organized as follows:

- `server.py`: Contains the server-side code responsible for handling the signaling and media stream handling between clients. It generates a moving ball on the canvas and provides the current ball position to connected clients.

- `client.py`: Contains the client-side code responsible for displaying the bouncing ball. It processes the received frames, performs ball detection, and sends the current ball position to the server.

- `tests_client.py`: Contains unit tests for the client-side code.

- `tests_server.py`: Contains unit tests for the server-side code.

## Requirements

- Python 3.10 or higher
- OpenCV (cv2)
- aiortc
- av

## Setup

1. Extract the contents of the zip file and navigate to the project's directory.

2. Install and activate a Python virtual environment:

```
python3 -m venv venv
source venv/bin/activate
```

3. Install the application's dependencies:

```
pip install -r requirements.txt
```

## Usage

To use the application, follow these instructions:

1. Navigate to the project directory.

2. Start the server -> `python server.py`

The server will run on `localhost (127.0.0.1)` and listen for incoming connections on port `8080`.

3. Start the client -> `python client.py`

The client will connect to the server and display the bouncing ball on the screen. The real-time positions of the ball will be exchanged between the client and the server, with the respective terminals showing the updates. Additionally, the server terminal will display the computed errors between the received ball positions and the actual positions.

## Testing

To run the unit tests, perform the following steps:

1. Install the required testing packages:
   `pip install -r requirements.tests.txt`

2. Run all the unit tests in verbose mode (optional):

```
pytest
pytest -vv # enable verbose output
```

## Docker workflow and Kubernetes Deployment

We use [minikube](https://minikube.sigs.k8s.io/docs/start/) for starting a kube cluster and deploying the application

1. Start Minikube -> `minikube start`

2. Build the Docker images for the server and client applications

```
docker build -t server .
docker build -t client .
```

3. Apply the deployment manifest files:

```
kubectl apply -f server-deployment.yaml
kubectl apply -f client-deployment.yaml
```

This will create the deployments for the server and client applications in your Minikube cluster.

4. Verify that the deployments are running by checking the deployment and pod statuses:

```
kubectl get deployments
kubectl get pods
```

5. Access the server and client logs

```
kubectl exec -it <server-pod-name> -- /bin/bash  #replace <server-pod-name> with the name of the server pod

kubectl exec -it <client-pod-name> -- /bin/bash #replace <client-pod-name> with the name of the client pod
```

## Contributing

Contributions are welcome! If you encounter any issues or have suggestions for improvements, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License.
