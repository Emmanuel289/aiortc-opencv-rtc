# Peer-to-Peer RTC with aiortc and OpenCV

This project demonstrates real time communication using an application that showcases TCP signaling, frame transport, and messaging enabled by [aiortc](https://aiortc.readthedocs.io/en/latest). The application consists of a client-side and a server-side component. The server generates continuous frames of 2D images of a bouncing ball, which it transmits to the client for display on a screen. TCP socket signaling is used to establish a connection between the client and the server. Additionally, frame transport and data channel messaging is used to exchange the moving images and positions of the bouncing ball between the server and the client. The server also computes and prints the errors between the ball's positions reported by the client and the actual positions of the ball.

<div align="center">

![License](https://img.shields.io/badge/License-MIT-blue.svg)
[![Ubuntu Version](https://img.shields.io/badge/Ubuntu-22.04+-orange)](https://releases.ubuntu.com/20.04/)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![numpy](https://img.shields.io/badge/numpy-1.23.5-blue.svg)
![opencv-python](https://img.shields.io/badge/opencv--python-4.7.0-blue.svg)
![aiortc Version](https://img.shields.io/badge/aiortc-%3E%3D1.3.0-blue.svg)
![aiohttp](https://img.shields.io/badge/aiohttp-3.8.4-blue.svg)
![aiohttp-requests](https://img.shields.io/badge/aiohttp--requests-0.1.3-blue.svg)
![Coverage](https://img.shields.io/badge/coverage-95%25-green.svg)

</div>

## Project Structure

The project structure is organized as follows:

- `server.py`: Contains the server-side code responsible for generating continuous 2D images/frames of a bouncing ball and transmitting the images and positions of the ball to the connected client.

- `client.py`: Contains the client-side code responsible for displaying the bouncing ball on a screen. It processes the received frames from the server, performs ball detection, and reports the real-time positions of the ball to the server.

- `tests_client.py`: Contains unit tests for the client-side code.

- `tests_server.py`: Contains unit tests for the server-side code.

## Requirements

- Ubuntu 22.04 or higher
- Python 3.10 or higher
- OpenCV (cv2)
- aiortc

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

Note: PyPi's [opencv-python](https://pypi.org/project/opencv-python/) is a minimalist package and does not contain many of the required plugins for running GUI applications. In order to get all the required
dependencies, it is better to build the development version from source. Detailed instructions on how to build from source are available at [Installing OpenCV on Ubuntu](https://docs.opencv.org/3.4/d2/de6/tutorial_py_setup_in_ubuntu.html).

## Usage

To use the application, follow these instructions:

1. Navigate to the project directory.

2. Start the server -> `python server.py`

The server will run on `localhost (127.0.0.1)` and listen for incoming connections on port `8080`.

3. Start the client -> `python client.py`

The client will connect to the server and display the bouncing ball on the screen. The real-time positions of the ball will be exchanged between the client and the server, with the respective terminals showing the updates. Additionally, the server terminal will display the computed errors between the positions of the ball as reported by the client and the actual positions.

## Testing

To run the unit tests, perform the following steps:

1. Install the required testing packages:
   `pip install -r requirements.tests.txt`

2. Run all the unit tests and optionally enable verbose mode:

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
