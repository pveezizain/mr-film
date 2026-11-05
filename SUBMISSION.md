# MR Film: The Chini Saga

**Track:** Indie Developer
**Theme:** Build for Your World
**Team:** RaiQalle IBN (solo)

## One-line summary
MR Film lets a viewer step inside an AI film: they explore a scene of *The Chini Saga*, click its story points, ask an in-story guide, and look around the lake in 360°.

## The problem
Film audiences only watch from outside. A filmmaker on a small budget has no simple way to let people explore the world of their story, or to ask questions about it while they watch.

## What it does
- **Scene 1, Tasik Chini:** a boat heads toward a tribe village across the lake, with markers on the two obstacles ahead.
- **Obstacle A:** the boat turns left, and a creature rises in front of it and tries to communicate with the person on board.
- **Obstacle B:** an old lady on the island transforms into a giant snake.
- **In-story guide:** the viewer asks a question and gets an answer in character.
- **360° look-around:** the viewer drags to look in any direction, and zooms with the wheel or pinch.

## Meta tools used
- **Muse Spark 1.3** (through Meta Model API, OpenAI-compatible chat endpoint with tool calling) powers the in-story guide.
- The guide is an **agent**: it calls two tools, one to look up an object by name, and one to read the current scene's notes.
- A **second check** uses Muse Spark to stop any answer that reveals story beyond the current scene. The server log shows each check's verdict.

## How it works
1. A browser page shows the film player, with markers and scene navigation.
2. A small local Python server (`server.py`) holds the API key, so the key never reaches the browser.
3. Each guide question goes to the server, the agent answers using the tools, and the spoiler check runs before the answer is shown.
4. If the server or Meta is unreachable, the guide answers from the scene notes and labels the answer as offline.

## What works
- Sign-in, catalogue, and film details pages
- The Tasik scene with working markers
- Both obstacle scenes and the alternate cut
- The live guide through Muse Spark, with the spoiler check
- The 360° look-around

## Honest notes
- The Tasik footage was filmed by the author.
- The obstacle clips and the 360° panorama were created with AI video and image tools. Their terms are saved for review.
- This is a **web prototype**, not a headset or smart-glasses app.
- The markers are placed by hand. Automatic object detection with SAM 3.1 is planned but is **not** in the submitted version.

## Next steps
- Detect the markers automatically with SAM 3.1.
- Replace the AI panorama and obstacle clips with the author's own 360° footage.
- Add motion to the 360 view, once a 2:1 video is ready.
- Test the viewer on a VR headset over HTTPS.

## How to run it
See `README.txt`. In short: install `requirements.txt`, set `META_API_KEY` in the same PowerShell window, run `python -u server.py`, and open http://localhost:8000.
