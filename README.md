# Vision Speed Pipeline

This project detects vehicles, estimates speed, and sends API alerts for overspeed vehicles.

## Project Files

```text
Speed_Detection_Pipeline/
|- data/
|  |- testing_1.mp4
|  |- testing_2.mp4
|- detection/
|  |- detector.py
|- metadata/
|  |- bridge.py
|- logic/
|  |- speed_estimator.py
|- api/
|  |- handler.py
|- mock/
|  |- server.py
|- tools/
|  |- zone.py
|- main.py
|- .env.example
|- requirements.txt
|- README.md
```

## Module Mapping (Assignment)

1. Detection Engine: detection/detector.py
2. Metadata Bridge: metadata/bridge.py
3. Business Logic: logic/speed_estimator.py
4. Action Handler (API): api/handler.py

## What is mock/server.py?

mock/server.py is a local mock API server.

Use it to confirm your alert POST requests are working.
When overspeed happens, the server prints:

- alert path (/speed)
- request body (vehicle_id and speed)

## What is tools/zone.py? (Very Very IMP do this carefully)

tools/zone.py helps you select 4 road points on the first video frame.

Click in this order:

1. Top-left
2. Top-right
3. Bottom-right
4. Bottom-left

It will show a warped preview so you can validate your zone.

## Setup

1. Create and activate your environment.

2. Install PyTorch with CUDA 12.1 first:

	pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

3. Install project requirements:

	pip install -r requirements.txt

4. Copy env template:

	copy .env.example .env

5. Edit .env values for your system (model path, video path, API URL, speed limit).

Important for this repo:

- Default test video is in data/testing_1.mp4
- Keep VIDEO_PATH in .env as ./data/testing_1.mp4 unless you want another video

## Test Data (Google Drive)

Drive folder:

https://drive.google.com/drive/folders/1ot06Z9VoJ4Gg-rlexvjWXcv2LPyZilPx?usp=drive_link

This folder contains:

- testing_1.mp4
- testing_2.mp4
- Speed_Annotated_Outputs/ (annotated speed output videos for both test videos)

How to use:

1. Download one or both videos.
2. Put them inside the local data folder:

	Speed_Detection_Pipeline/data/

3. In .env, set VIDEO_PATH to whichever file you want to run:

	VIDEO_PATH=./data/testing_1.mp4
	or
	VIDEO_PATH=./data/testing_2.mp4

## Run Pipeline + Alert Test

1. Start mock server in terminal 1:

	python mock/server.py

2. Run speed pipeline in terminal 2:

	python main.py

3. When a vehicle crosses speed limit, you should see alert logs in server terminal.

## Optional: Run Zone Selector

	python tools/zone.py

Use the clicked points to update road zone in main.py if needed.

## Very Important: Update These 2 Things In main.py

Before final run, make sure these are correct for your camera and road.

Current project calibration already set in main.py:

- SRC_POINTS = [(152,124), (610,175), (639,324), (153,340)]
- REAL_ROAD_WIDTH_METERS = 6.0
- REAL_ROAD_LENGTH_METERS = 16.5

Note: REAL_ROAD_WIDTH_METERS and REAL_ROAD_LENGTH_METERS were measured manually by me on-site using shoe-feet stepping approximation.

If you are using the same camera view, keep these values as-is.

1. Zone points (SRC_POINTS)

- In main.py, update SRC_POINTS with the 4 points you got from zone.py.
- Keep this click/order format:
	- Top-left
	- Top-right
	- Bottom-right
	- Bottom-left

2. Real road size

- In main.py, update:
	- REAL_ROAD_WIDTH_METERS
	- REAL_ROAD_LENGTH_METERS
- These values are used to convert pixel movement to real speed.
- If these values are wrong, displayed speed will be wrong.

Quick workflow:

1. Run tools/zone.py
2. Copy final 4 points into SRC_POINTS in main.py
3. Set correct road width/length in meters
4. Run main.py and verify speed labels

## Simple Email Notification Architecture (Client Scenario)

In production, do this flow:

1. Pipeline sends overspeed event to backend API.
2. Backend stores event and pushes notification job.
3. Notification service sends email.
4. Backend stores email delivery status.

This keeps CV pipeline fast and notification system reliable.
