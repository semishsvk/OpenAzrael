from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import math
import struct
import unittest

import numpy as np

from tools.audio_lab.common import sha256_file
from tools.audio_lab.oa_audio_spectral import (
    analyze_file,
    main as spectral_main,
    spectral_metrics,
    spectrogram_preview,
    stft_power,
    write_grayscale_png,
)

def write_pcm16_wave(path: Path, samples: np.ndarray, sample_rate: int=8000) -> None:
    x=np.clip(np.asarray(samples,dtype=np.float64),-1.0,0.999969)
    pcm=np.rint(x*32767.0).astype("<i2").tobytes()
    fmt=struct.pack("<HHIIHH",1,1,sample_rate,sample_rate*2,2,16)
    body=b"WAVE"+b"fmt "+struct.pack("<I",16)+fmt+b"data"+struct.pack("<I",len(pcm))+pcm
    path.write_bytes(b"RIFF"+struct.pack("<I",len(body))+body)

class AudioLabSpectralTests(unittest.TestCase):
    def test_sine_frequency_metrics_are_close(self):
        sr=8000
        t=np.arange(sr,dtype=np.float64)/sr
        x=0.5*np.sin(2*np.pi*1000*t)
        power,freqs=stft_power(x,sr,512,128)
        m=spectral_metrics(x,sr,power,freqs)
        self.assertAlmostEqual(m["dominant_frequency_hz"],1000.0,delta=20.0)
        self.assertAlmostEqual(m["spectral_centroid_hz"],1000.0,delta=80.0)
        self.assertAlmostEqual(m["spectral_rolloff_85_hz"],1000.0,delta=80.0)
        self.assertLess(m["spectral_flatness"],0.05)
        self.assertTrue(all(math.isfinite(float(v)) for v in m.values()))

    def test_silence_metrics_are_finite(self):
        x=np.zeros(256,dtype=np.float64)
        power,freqs=stft_power(x,8000,512,128)
        m=spectral_metrics(x,8000,power,freqs)
        self.assertEqual(m["dominant_frequency_hz"],0.0)
        self.assertEqual(m["spectral_centroid_hz"],0.0)
        self.assertEqual(m["crest_factor"],0.0)
        self.assertTrue(all(math.isfinite(float(v)) for v in m.values()))

    def test_spectrogram_png_is_valid_grayscale_png(self):
        x=np.sin(2*np.pi*440*np.arange(4000)/8000)
        power,_=stft_power(x,8000,512,128)
        preview=spectrogram_preview(power,-80.0,64,32)
        self.assertEqual(preview.shape,(32,64))
        with TemporaryDirectory() as td:
            p=Path(td)/"spec.png"
            write_grayscale_png(p,preview)
            raw=p.read_bytes()
            self.assertTrue(raw.startswith(b"\x89PNG\r\n\x1a\n"))
            width,height,bit_depth,color_type=struct.unpack_from(">IIBB",raw,16)
            self.assertEqual((width,height),(64,32))
            self.assertEqual(bit_depth,8)
            self.assertEqual(color_type,0)

    def test_analyze_file_reports_expected_dimensions_and_frequency(self):
        with TemporaryDirectory() as td:
            p=Path(td)/"tone.wav"
            sr=8000
            t=np.arange(sr,dtype=np.float64)/sr
            write_pcm16_wave(p,0.4*np.sin(2*np.pi*500*t),sr)
            rec,preview=analyze_file(p,fft_size=512,hop_size=128,time_bins=80,freq_bins=40)
            self.assertAlmostEqual(rec["dominant_frequency_hz"],500.0,delta=20.0)
            self.assertEqual(preview.shape,(40,80))
            self.assertEqual(rec["sample_rate"],sr)

    def test_directory_run_is_source_safe_and_deterministic(self):
        with TemporaryDirectory() as td:
            base=Path(td)
            src=base/"src"; src.mkdir()
            sr=8000
            t=np.arange(sr,dtype=np.float64)/sr
            write_pcm16_wave(src/"A.wav",0.4*np.sin(2*np.pi*440*t),sr)
            write_pcm16_wave(src/"B.wav",0.2*np.sin(2*np.pi*880*t),sr)
            before={p.name:sha256_file(p) for p in src.iterdir()}
            out1=base/"out1"; out2=base/"out2"
            self.assertEqual(spectral_main([str(src),"--output-dir",str(out1)]),0)
            self.assertEqual(spectral_main([str(src),"--output-dir",str(out2)]),0)
            after={p.name:sha256_file(p) for p in src.iterdir()}
            self.assertEqual(before,after)
            m1=(out1/"spectral_manifest.json").read_bytes()
            m2=(out2/"spectral_manifest.json").read_bytes()
            self.assertEqual(m1,m2)
            manifest=json.loads(m1)
            self.assertEqual(manifest["status"],"PASS")
            self.assertTrue(manifest["source_unchanged"])
            self.assertEqual(len(manifest["assets"]),2)
            self.assertTrue((out1/"spectral_review.html").is_file())
            self.assertEqual(len(list((out1/"spectrograms").glob("*.png"))),2)

    def test_output_inside_source_is_rejected(self):
        with TemporaryDirectory() as td:
            src=Path(td)/"src"; src.mkdir()
            write_pcm16_wave(src/"A.wav",np.zeros(1000),8000)
            with self.assertRaises(SystemExit) as cm:
                spectral_main([str(src),"--output-dir",str(src/"reports")])
            self.assertEqual(cm.exception.code,2)
            self.assertFalse((src/"reports").exists())

if __name__=="__main__":
    unittest.main()
