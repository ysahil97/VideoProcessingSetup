# Video Processing Site

This README is about the client-server setup, simulating the process of video translation in a server. The goal of this project is to create a developer-friendly client library, which takes care of sending this api to the server while taking into account the intermediate pending responses that the client can face most of the times.

## Description of the files

- `client.py`: Python file containing the client business logic, simulating the retry mechanism of the `/status` api with exponential backoff, while also employing asynchronous programming to reduce the waiting time for the user waiting on this call.
- `server.py`: Simple server setup with a configurable `processing_time` to simulate an intensive video translation process happening on the server
- `integration_test.py`: Integration test which spawns up a server on a separate process, and calls the client function with simple duration and final status checks

## Usage of the Client Library
In `client.py`, the async method `make_complete_request()` takes care of hitting the `/status` endpoint of the server with multiple retries. As it is an asynchronous call, other async functions could work in the cases when the given function function is in a waiting stage, thereby reducing wastage of idle time otherwise occuring in synchronous implementation. The arguments of these functions are two callbacks:
- Progress callback: callback to print the progress (status of intermediate API request) in console
- Error callback: callback to log the errors of the client implementation.


## Start Server

```
python run_server.py
```


## Run the testing module
```
python integration_test.py
```