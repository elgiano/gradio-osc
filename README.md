# gradio-osc

[![PyPI - Version](https://img.shields.io/pypi/v/gradio-osc.svg)](https://pypi.org/project/gradio-osc)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/gradio-osc.svg)](https://pypi.org/project/gradio-osc)

-----

gradio-osc connects to a gradio app and runs an OSC server exposing its API endpoints

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)

## Installation

Soon:
```console
pip install gradio-osc
```

use hatch for now:
```console
hatch shell
python -m gradio_osc -p 10508 https://url.to.gradio.live
```

## Usage
```console
gradio-osc -p 10518 "https://url.to.gradio.live"
```

OSC endpoints mimic gradio API endpoints. Parameters have to be submitted as pairs of names and values, e.g.:

```
"/generate" "prompt" "deconstructed techno" "negative_prompt" "techno"
```

Here `"/generate"` is the OSC path, corresponding to gradio's API path. Two parameters are provided, namely `prompt="deconstructed techno"` and `negative_prompt="techno"`. It's equivalent to the following call:

```python
gradio_client.predict(api_name="/generate",
  prompt="deconstructed_techno",
  negative_prompt="techno"
)
```

### special arguments:
A few special arguments can be added to OSC messages to affect gradio_client itself. They won't be forwarded to the gradio app.

- `"osc-download_path"`: specifies the path where to eventually download files
- `"osc-reply_host"`: specifies an alternative hostname to send replies (results) to.
- `"osc-reply_port"`: specifies an alternative port to send replies (results) to.

### Receiving results

By default replies will be sent back to the same address that sent the message. It is possible to change this behavior by sending "osc-reply_host" and "osc-reply_port" along with any OSC message (see above). Just in case you're using MaxMSP and you need to recv on a different address than the one you send from.

## SuperCollider example

Reference example for stable-audio:

```console
hatch shell
python -m gradio_osc -p 10508 https://url.to.gradio.live
```

```supercollider
(
// osc responder triggered when a sample is ready
OSCdef(\generateDone, { |msg|
	var path = msg[1];
	"Generated: %".format(path).postln;
	// do something with this fresh fresh ai music
	s.waitForBoot {Buffer.read(s, path, action: {|b| b.play })}
}, "/generate.reply")
)

(
// uncond with prompt and negative
NetAddr("localhost", 10518).sendMsg("/generate", 
	"prompt", "hey I'm just developing some osc integration",
	"negative_prompt", "field recordings, programming",
	"seconds_total", 1,
	"steps", 100,
	"osc-download_path", Platform.userHomeDir +/+ "stable-audio/"
)
)

(
// generate from init_audio (upload is handled automagically by gradio-osc and gradio-client
NetAddr("localhost", 10518).sendMsg("/generate", 
	"prompt", "hey I'm just re-digesting some osc integration",
	"use_init", "true",
	"init_audio", "/home/giano/stable-audio/d52c4820d22e0d81edd9f55c0c1cdf3fbcd418eb/output.wav",
	"init_noise_level", 0.3
	"negative_prompt", "field recordings, programming",
	"osc-download_path", Platform.userHomeDir +/+ "stable-audio/"
)
)
```