from gradio_osc import parse_args
from gradio_osc.server import GradioOSCServer
from gradio_osc.filters import GradioOSCFilter
from math import floor, log10
import os
# Note: librosa shouldn't come with gradio_osc
# one would need to install librosa separately
import librosa
import soundfile as sf


# define custom filter for automatic beat slicing
class SliceBeats(GradioOSCFilter):
    '''
    For every downloaded audiofile:
    - detect bpm and beats
    - cut in subsamples of n_beats (default 4)
    - save all cuts in same folder
    '''

    def __init__(self, beats_per_slice=4):
        self.beats_per_slice = beats_per_slice

    def slice(self, filepath):
        # load audio
        try:
            audio, sr = librosa.load(filepath, sr=None, mono=False)
        except (librosa.util.exceptions.ParameterError, RuntimeError, EOFError, IOError):
            print(f"{filepath} is not a soundfile")
            return

        print(f"🎶Detecting beats in {filepath}")
        # mixdown to mono for beat_track
        mono = audio.sum(axis=0)
        tempo, beat_frames = librosa.beat.beat_track(y=mono, sr=sr)
        beat_frames = librosa.frames_to_samples(beat_frames)
        num_beats = len(beat_frames)
        print(f"{num_beats} beats detected")
        print(f"BPM: {tempo}")

        # group beats
        beats_per_slice = 4
        groups = [
            beat_frames[i:i+self.beats_per_slice+1]
            for i in range(0, num_beats, self.beats_per_slice)
        ]
        print(f"Exporting {len(groups)} slices of {beats_per_slice} beats")

        # for zero-padding filenames
        num_zeros = floor(log10(len(groups)))

        # export slices
        for (i, beats) in enumerate(groups):
            start, end = beats[0], beats[len(beats)-1]
            basename, ext = os.path.splitext(filepath)
            out_path = f"{basename}-beats_{i:0{num_zeros + 1}d}{ext}"
            y = audio[:, start:end]
            # transpose stereo for libsndfile (frames, channels)
            sf.write(out_path, y.T, samplerate=sr)


    # this hooks is run after results are received and files downloaded
    def process_outputs(self, path, args, results, replyAddr):
        # use self.server to get result types and detect filepaths
        types = self.server.get_results_types(path)
        for i, r in enumerate(results):
            if types[i] == 'filepath':
                self.slice(r)


def main():
    # import parse_args from gradio_osc to use same cli args
    args = parse_args()

    # start a server with an extra filter: SliceBeats
    print("*>* Hold on while we connect to your gradio app...")
    osc = GradioOSCServer(args.osc_port, filters=[
        SliceBeats()
    ])

    # connect to gradio
    osc.connect_gradio(args.gradio_url, download_dir=args.gradio_dl)
    print(f'*>* Connected! OSC listening to port {args.osc_port}')

    # start serving
    # note: this is blocking, wrap in a thread if you need to run concurrently
    osc.serve_forever()

if __name__ == "__main__":
    main()
