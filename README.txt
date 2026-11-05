MR FILM - THE CHINI SAGA (Meta Global AI Developer Hackathon, Track 1)
======================================================================

WHAT IS IN THIS FOLDER
  index.html          the demo page (Tasik scene, obstacle A and B, guide)
  server.py           local server; sends guide questions to Meta Model API (Muse Spark)
  requirements.txt    Python package needed (openai)
  scenes\             the video and image files the demo loads (stills for all 3 scenes are here)

WINDOWS SETUP (PowerShell)
  1. Open PowerShell inside this folder (type "powershell" in the address bar).
  2. Install the package once:
        python -m pip install -r requirements.txt
  3. Set your API key for this window only (use your own key, keep the quotes).
     Either variable name works (META_API_KEY or MODEL_API_KEY):
        $env:META_API_KEY="your-key-here"
  4. Start the server:
        python -u server.py
  5. Open http://localhost:8000 in Chrome or Edge, press Ctrl + F5.

IMPORTANT
  - Keep the PowerShell window open while using the demo.
  - Set the key in the same window that runs server.py.
  - Never paste the key into index.html, this file, or any chat.
  - The 360 Look Around uses our own viewer. It needs scenes\tasik-360.jpg (a 2:1 panorama).
  - To change the model: $env:MUSE_MODEL="model-name" (default muse-spark-1.3).
  - Without a key the guide answers from the scene notes (labelled "offline answer").
  - If you see "[guide] Meta call failed", the line after it gives the reason.

SCENES FOLDER
  tasik-chini.mp4         Scene 1, main footage (looped)
  tasik-chini-2.mp4       Scene 1b, alternative cut
  tasik-chini-frame.jpg   still frame the guide can see (used when SEND_FRAME=1)
  obstacle-a.mp4          Obstacle A: the creature
  obstacle-b.mp4          Obstacle B: the old lady
  obstacle-a-frame.jpg    still of Obstacle A for the guide
  obstacle-b-frame.jpg    still of Obstacle B for the guide
  tasik-360.jpg           2:1 panorama for the 360 Look Around

