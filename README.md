# [HeyGen] Video Processing Site

- This is the submission for my take home assessment for **HeyGen** Backend Engineer role 2024

This README is about the client-server setup, simulating the process of video translation in a server. The goal of this project is to create a developer-friendly client library, which takes care of sending this api to the server while taking into account the intermediate pending responses that the client can face most of the times.

## Description of the files
In `src/videotranslation`:

- `client.py`: 
    - It Implements retry mechanism with exponential backoff for /status API calls

    - Utilizes asynchronous programming to minimize user wait times

    - Features caching system for frequent requests

    - Implements circuit breaker pattern for fault tolerance
- `server.py`: 

    - Built with FastAPI for high-performance API handling, comparable to Golang and Node.js

    - Configurable processing_time to simulate intensive video translation processes


Features of the client Library:
- The api's are designed using FastAPI library, rather than basic `http.request` methods, to provide comparable performance to other backend languages such as Node.js and Golang
- **Cache**:
The client uses a Cache to store recent requests, which can decrease the api response time of requests provided frequently to server. Every entry of Cache has a ttl value which is used to discard the stale entries.
    - `tests/test_cache.py` contains the testcases pertaining to the proper functioning of the cache.
- **Circuit Breaker Design Pattern**:
In order to prevent cascading errors occuring from the exceptions in the client, I have used a circuit-breaker design pattern, which is based on 3 internal states: **closed**,**open** and **half-open**. The **closed** state means that the system is working well. If the number of failure occurences exceeds a threshold, the CircuitBreaker moves to the **open** state. Here, the api would not work, in order to examine the production system for its bugs. After a certain "Timeout" period since the last failure, the system is now able to execute and move into **half-open** state. From here, there are two possible paths:
    - If we encounter another failure, the Circuit Breaker reverts back to **open** state
    - If we encounter a success, the Circuit Breaker design pattern goes to **closed** state, opening the api for all the users.

    - `tests/test_circuit_breaker.py` contains the test cases for proper functioning of the circuit breaker.

### Integration tests
- `tests/test_integration.py`: Integration test which spawns up a server on a separate process, and calls the client function with simple duration and final status checks

## Usage of the Client Library
In `client.py`, the async method `make_complete_request()` takes care of hitting the `/status` endpoint of the server with multiple retries. As it is an asynchronous call, other async functions could work in the cases when the given function function is in a waiting stage, thereby reducing wastage of idle time otherwise occuring in synchronous implementation. The arguments of these functions are two callbacks:
- Progress callback: callback to print the progress (status of intermediate API request) in console
- Error callback: callback to log the errors of the client implementation.
- Job Id: id of the concerned video translation job
    - currently job id is hardcoded, as the api requirements strictly suggested "/status" api, but it can be easily extended to fetch status result for any video translation job.


## Usage
To initialize the server
```
python run_server.py
```

To run the standalone client
```
python run_client.py
```


## Run the testing module
The testing could be done by running `pytest` on the root directory of this project. It will automatically fetch the test scripts, and get the results for them.