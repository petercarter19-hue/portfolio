"""Focused real-byte actual-duration/media-integrity proof; Speech is local stub."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import hashlib
import json
import struct
import subprocess
import unittest
import av
from fractions import Fraction
from services.resume_recording_probe import ProbedResumeTranscriptionAdapter,probe_duration,ProbeRefusal,_vint
from services.resume_intake_policy import SELECTED_RESUME_ONBOARDING_POLICY
from tests import test_resume_selected_boundaries as boundary_fixtures
wave_file=boundary_fixtures.wave_file

RESULTS=[]
FIXTURES={}


class RecordingChildPrivacyTests(unittest.TestCase):
    def test_actual_decoder_excludes_parent_secrets_and_startup_injection(self):
        import os
        from services import resume_recording_probe as probe
        real_run=probe.subprocess.run
        observations=[]
        with TemporaryDirectory() as directory:
            hook=Path(directory); marker=hook/'startup-ran'
            malicious="from pathlib import Path\nPath("+repr(str(marker))+ ").write_text('unexpected')\nraise RuntimeError('startup injection')\n"
            for filename in ('sitecustomize.py','usercustomize.py','av.py'):
                (hook/filename).write_text(malicious,encoding='utf-8')
            injected={key:'parent-secret-do-not-pass' for key in (
                'AZURE_SQL_CONNECTIONSTRING','MSSQL_SA_PASSWORD','AZURE_OPENAI_API_KEY',
                'AZURE_CLIENT_SECRET','RESUME_INTAKE_PROVIDER_CONFIGURATION','PEERSLATE_PRIVATE_SENTINEL')}
            injected.update(PYTHONPATH=str(hook),PYTHONHOME=str(hook),PYTHONSTARTUP=str(hook/'sitecustomize.py'),
                PYTHONINSPECT='1',PYTHONPYCACHEPREFIX=str(hook),LD_PRELOAD=str(hook/'injected.so'))
            def observed(args,**kwargs):
                self.assertEqual(args[1:4],['-I','-S','-B'])
                self.assertEqual(set(kwargs['env']),{'SystemRoot'} if os.name=='nt' else set())
                self.assertTrue(set(injected).isdisjoint(kwargs['env']))
                self.assertNotIn('parent-secret-do-not-pass',json.dumps(kwargs['env']))
                observations.append({'isolated_flags':args[1:4],'environment_keys':sorted(kwargs['env'])})
                completed=real_run(args,**kwargs)
                self.assertNotIn(b'parent-secret',completed.stdout)
                return completed
            wave,_=wave_file(seconds=1)
            with wave:pcm=wave.read()
            with patch.dict(os.environ,injected),patch.object(probe.subprocess,'run',side_effect=observed):
                self.assertEqual(probe.probe_duration(pcm,'audio/wav',SELECTED_RESUME_ONBOARDING_POLICY),1)
                self.assertEqual(probe.probe_duration(webm(1),'audio/webm',SELECTED_RESUME_ONBOARDING_POLICY),1)
            self.assertFalse(marker.exists(),'child ran an injected Python startup/package hook')
        self.assertEqual(len(observations),2)
        self.assertEqual(probe.WALL_SECONDS,8)
        self.assertEqual(probe.CHILD_MEMORY,512*1024*1024)
        RESULTS.append({'case':'parent_secret_exclusion_and_startup_isolation','actual_child_formats':['PCM WAV','WebM/Opus'],
            'child_observations':observations,'startup_marker_created':False,'real_provider_calls':0})


def webm(seconds,*,seekable=False):
    key=(seconds,seekable)
    if key not in FIXTURES:
        # Same pinned library as the probe; no extra encoder/CLI dependency in CI.
        class StreamingWriter:
            def __init__(self):self.data=bytearray()
            def write(self,chunk):self.data.extend(chunk);return len(chunk)
            def tell(self):return len(self.data)
            def writable(self):return True
        target=BytesIO() if seekable else StreamingWriter()
        options={} if seekable else {"live":"1"}
        with av.open(target,mode="w",format="webm",options=options) as out:
            stream=out.add_stream("libopus",rate=48000);stream.layout="mono"
            total=round(seconds*48000);position=0
            while position<total:
                count=min(960,total-position)
                frame=av.AudioFrame(format="s16",layout="mono",samples=count)
                frame.planes[0].update(b"\0"*frame.planes[0].buffer_size)
                frame.sample_rate=48000;frame.pts=position;frame.time_base=Fraction(1,48000)
                for packet in stream.encode(frame):out.mux(packet)
                position+=count
            for packet in stream.encode(None):out.mux(packet)
        FIXTURES[key]=target.getvalue() if seekable else bytes(target.data)
    return FIXTURES[key]


class RecordingProbeTests(unittest.TestCase):
    # Explicit runner loads only these named methods, not inherited boundary tests.
    def setUp(self):
        boundary_fixtures.ExactBoundaryTests.setUp(self)
        self.service.transcription_adapter=ProbedResumeTranscriptionAdapter(service=self.service.transcription_adapter._service)

    def observe(self,label,data,declared,duration):
        response=self.client.post("/api/resume-intake/me/recordings",headers=self.headers,
            data={"request":json.dumps({"request_id":__import__('uuid').uuid4().hex,"client_key":"audio","duration_seconds":duration}),
                  "recording":(BytesIO(data),"synthetic-recording",declared)})
        RESULTS.append({"case":label,"file_bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),
            "client_duration":duration,"status":response.status_code,"local_speech_stub_calls":len(self.transcriptions),
            "returned_actual_duration":((response.get_json() or {}).get("receipt") or {}).get("duration_seconds"),
            "message":(response.get_json() or {}).get("message"),"real_provider_calls":0})
        return response

    def assert_refused(self,response):
        self.assertEqual(response.status_code,400,response.get_json())
        self.assertEqual(self.transcriptions,[])
        self.assertEqual(self.service._load("member")["sources"],{})

    def test_real_pcm_300_seconds_and_forged_short_for_overlimit(self):
        stream,seconds=wave_file(seconds=300)
        with stream:data=stream.read()
        response=self.observe("pcm_exact300_client1",data,"audio/wav",1)
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(response.get_json()["receipt"]["duration_seconds"],300)
        self.assertEqual(len(self.transcriptions),1)
        self.transcriptions.clear()
        stream,_=wave_file(seconds=300.001)
        with stream:data=stream.read()
        response=self.observe("pcm_actual300001_client1",data,"audio/wav",1)
        self.assertEqual(response.status_code,400,response.get_json())
        self.assertEqual(self.transcriptions,[])

    def test_real_streaming_webm_opus_300_seconds_and_forged_short_overlimit(self):
        data=webm(300)
        self.assertEqual(probe_duration(data,"audio/webm",SELECTED_RESUME_ONBOARDING_POLICY),300)
        response=self.observe("streaming_webm_actual300_client1",data,"audio/webm",1)
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(response.get_json()["receipt"]["duration_seconds"],300)
        self.assertEqual(len(self.transcriptions),1)
        self.transcriptions.clear()
        response=self.observe("streaming_webm_actual30002_client1",webm(300.02),"audio/webm",1)
        self.assertEqual(response.status_code,400,response.get_json())
        self.assertEqual(self.transcriptions,[])

    def test_forged_container_duration_cannot_shorten_decoded_samples(self):
        data=bytearray(webm(300.02,seekable=True))
        pos=data.find(b"\x44\x89")
        self.assertGreater(pos,0)
        size,start,unknown=_vint(data,pos+2)
        self.assertEqual(size,8);self.assertFalse(unknown)
        data[start:start+size]=struct.pack(">d",1000.0)
        # ffmpeg WebM1ms timestamp scale: forged header advertises1second.
        import av,io
        with av.open(io.BytesIO(data),format="matroska") as container:
            self.assertEqual(container.duration,1_000_000)
        self.assert_refused(self.observe("webm_actual30002_container1_client1",bytes(data),"audio/webm",1))

    def test_truncated_or_malformed_pcm_and_webm_refuse_before_speech(self):
        data=webm(1)
        stream,_=wave_file(seconds=1)
        with stream:wav=stream.read()
        for label,blob,mime in [("webm_lastbyte_truncated",data[:-1],"audio/webm"),
                               ("webm_last40bytes_truncated",data[:-40],"audio/webm"),
                               ("webm_malformed",data[:24]+b"bad","audio/webm"),
                               ("wav_lastbyte_truncated",wav[:-1],"audio/wav"),
                               ("wav_forged_riff_size",wav[:4]+b"\x00\x00\x00\x00"+wav[8:],"audio/wav")]:
            with self.subTest(label=label):self.assert_refused(self.observe(label,blob,mime,1))

    def test_invalid_compressed_opus_payload_is_not_duration_only_admission(self):
        data=bytearray(webm(1))
        # Walk finite EBML children until the first actual audio block.
        def find_block(start,end):
            pos=start
            while pos<end:
                tag,pos,_=_vint(data,pos,identifier=True);size,pos,unknown=_vint(data,pos)
                stop=end if unknown else pos+size
                if tag==0xA3:return pos,stop
                if tag in {0x18538067,0x1F43B675}:
                    found=find_block(pos,stop)
                    if found:return found
                pos=stop
        block,end=find_block(0,len(data))
        _,packet,_=_vint(data,block);packet+=3 # track-vint, timestamp2, flags1
        data[packet:end]=b"\xff"*(end-packet)
        self.assert_refused(self.observe("opus_payload_malformed",bytes(data),"audio/webm",1))

    def test_byte_ceiling_unsupported_and_missing_probe_keep_manual_input(self):
        stream,_=wave_file(total_bytes=20*1024*1024)
        with stream:data=stream.read()
        response=self.observe("pcm_exact20mib",data,"audio/wav",1)
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertAlmostEqual(response.get_json()["receipt"]["duration_seconds"],262.14345)
        self.transcriptions.clear()
        response=self.observe("pcm_20mib_plus1",data+b"x","audio/wav",1)
        self.assertEqual(response.status_code,400);self.assertEqual(self.transcriptions,[])
        with self.subTest("unsupported"):
            response=self.observe("unsupported_mp4",b"\x00\x00\x00\x18ftypisom"+b"x"*20,"audio/mp4",1)
            self.assertEqual(response.status_code,400);self.assertEqual(self.transcriptions,[])
        from services import resume_recording_probe as probe
        short_webm=webm(1)
        with patch.object(probe.subprocess,"run",side_effect=subprocess.TimeoutExpired("owned-probe",8)):
            response=self.observe("probe_timeout_failclosed",short_webm,"audio/webm",1)
            self.assertEqual(response.status_code,400);self.assertIn("unavailable",response.get_json()["message"])
            self.assertEqual(self.transcriptions,[])
        manual=self.client.post("/api/resume-intake/me/submissions",headers=self.headers,
            data={"request":json.dumps({"type":"add_submission","request_id":__import__('uuid').uuid4().hex,"text":"Manual words remain usable."})})
        self.assertEqual(manual.status_code,200,manual.get_json())
        self.assertEqual(len(self.transcriptions),0)

    def test_unknown_length_mediarecorder_cluster_remains_supported(self):
        data=bytearray(webm(1))
        pos=data.find(b"\x1f\x43\xb6\x75")
        self.assertGreater(pos,0)
        _,start,_=_vint(data,pos+4)
        width=start-(pos+4)
        data[pos+4:start]=((1<<(7*width+1))-1).to_bytes(width,"big")
        response=self.observe("unknown_length_webm_cluster",bytes(data),"audio/webm",1)
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(response.get_json()["receipt"]["duration_seconds"],1)

    def test_factory_uses_probe_only_for_resume_not_shared_voice_adapter(self):
        from services.resume_intake_runtime import build_hosted_resume_intake
        class NeverDatabase:
            def __getattr__(self,name):raise AssertionError("constructor must not perform database IO")
        service=build_hosted_resume_intake({},database=NeverDatabase())
        self.assertIsInstance(service.transcription_adapter,ProbedResumeTranscriptionAdapter)
