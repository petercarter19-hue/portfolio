"""Exact local Flask/policy boundary proof; no real provider/storage/engine."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryFile
from types import SimpleNamespace
from uuid import uuid4
import json
import unittest
import wave
from unittest.mock import patch
from flask import Flask, request
import resume_intake_routes as routes
from services.resume_draft_repository import InMemoryCanonicalCatalog, InMemoryResumeDraftRepository
from services.resume_draft_service import ResumeDraftService
from services.resume_intake_policy import SELECTED_RESUME_ONBOARDING_POLICY
from services.resume_intake_repository import InMemoryResumeIntakeRepository
from services.resume_intake_service import ResumeIntakeService
from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter

RESULTS=[]

class OriginalsFixture:
    def __init__(self): self.admitted=[]
    def retain(self, owner, source, prepared):
        self.admitted.append({"bytes":len(prepared),"content_type":source["content_type"]})


def filled_file(size, prefix=b"Synthetic selectable text.\n", fill=b" "):
    stream=TemporaryFile()
    stream.write(prefix)
    remaining=size-len(prefix)
    block=fill*min(1024*1024,remaining)
    while remaining:
        part=block[:min(len(block),remaining)]
        stream.write(part); remaining-=len(part)
    stream.seek(0)
    return stream


def wave_file(*, seconds=None,total_bytes=None):
    stream=TemporaryFile()
    rate=8000 if seconds is not None else 40000
    frames=round(seconds*rate) if seconds is not None else (total_bytes-44)//2
    with wave.open(stream,"wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate)
        remaining=frames*2
        block=b"\0"*(1024*1024)
        while remaining:
            part=block[:min(len(block),remaining)]
            wav.writeframesraw(part); remaining-=len(part)
    if total_bytes is not None:
        assert stream.tell()==total_bytes
    stream.seek(0)
    return stream,frames/rate


class ExactBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.app=Flask("exact-boundary-fixture")
        self.originals=OriginalsFixture()
        self.transcriptions=[]
        def speech(data, content_type, *, locale):
            self.transcriptions.append({"bytes":len(data),"type":content_type,"locale":locale})
            return {"provider_transcript":"Synthetic local transcript"}
        self.service=ResumeIntakeService(
            repository=InMemoryResumeIntakeRepository(),
            draft_service=ResumeDraftService(repository=InMemoryResumeDraftRepository(),catalog=InMemoryCanonicalCatalog()),
            policy=SELECTED_RESUME_ONBOARDING_POLICY, original_files=self.originals,
            transcription_adapter=ResumeTranscriptionAdapter(service=SimpleNamespace(transcribe=speech)),
        )
        self.app.config.update(TESTING=True,MAX_CONTENT_LENGTH=2*1024*1024,
            MAX_FORM_MEMORY_SIZE=500*1024,PEERSLATE_RESUME_INTAKE_ENABLED=True,
            RESUME_INTAKE_SERVICE=self.service)
        self.app.register_blueprint(routes.resume_intake)
        @self.app.post("/unrelated")
        def unrelated(): return str(len(request.get_data()))
        self.client=self.app.test_client()
        identity=patch.object(routes,"get_current_identity",return_value=SimpleNamespace(user_key="member"))
        identity.start(); self.addCleanup(identity.stop)
        self.headers={"X-PeerSlate-Request":"same-origin"}
        @self.app.after_request
        def record_envelope(response):
            response.headers["X-Fixture-Content-Length"]=str(request.content_length or 0)
            response.headers["X-Fixture-Envelope"]=str(request.max_content_length)
            return response

    def document(self, size):
        key="document"
        body={"type":"add_submission","request_id":str(uuid4()),"attachments":[{
            "kind":"document","client_key":key,"filename":"fixture.txt","declared_content_type":"text/plain"}]}
        with filled_file(size) as stream:
            return self.client.post("/api/resume-intake/me/submissions",headers=self.headers,
                data={"request":json.dumps(body),"file:"+key:(stream,"fixture.txt","text/plain")})

    def recording(self, stream, duration):
        body={"request_id":str(uuid4()),"client_key":"recording","duration_seconds":duration}
        return self.client.post("/api/resume-intake/me/recordings",headers=self.headers,
            data={"request":json.dumps(body),"recording":(stream,"fixture.wav","audio/wav")})

    def test_exact_document_bytes_admitted_real_parser_remains_separate(self):
        response=self.document(50_000_000)
        payload=response.get_json()
        self.assertEqual(response.status_code,200,payload)
        self.assertEqual(self.originals.admitted,[{"bytes":50_000_000,"content_type":"text/plain"}])
        self.assertGreater(int(response.headers["X-Fixture-Content-Length"]),50_000_000)
        self.assertEqual(int(response.headers["X-Fixture-Envelope"]),250_256_000)
        row=payload["results"][0]
        self.assertNotEqual(row.get("code"),"too_large")
        sources=self.service._load("member")["sources"]
        self.assertTrue(sources)
        for source in sources.values():
            self.assertLessEqual(len((source.get("text") or "").encode("utf-16-le"))//2,20_000)
        RESULTS.append({"case":"document_exact_50000000","status":response.status_code,
            "file_bytes":50_000_000,"multipart_bytes":int(response.headers["X-Fixture-Content-Length"]),
            "route_envelope":int(response.headers["X-Fixture-Envelope"]),"admission":"accepted actual bytes",
            "intake_row_outcome":row.get("outcome"),"intake_row_code":row.get("code"),
            "document_parser_receipt":row.get("document"),
            "stored_text_utf16_units":[len((s.get("text") or "").encode("utf-16-le"))//2 for s in sources.values()]})

    def test_document_one_byte_over_rejected_before_retention_and_parse(self):
        response=self.document(50_000_001)
        self.assertEqual(response.status_code,200,response.get_json())
        row=response.get_json()["results"][0]
        self.assertEqual(row["code"],"too_large")
        self.assertFalse(row["saved"])
        self.assertEqual(self.originals.admitted,[])
        self.assertEqual(self.service._load("member")["sources"],{})
        RESULTS.append({"case":"document_50000001","status":response.status_code,"code":row["code"],
            "multipart_bytes":int(response.headers["X-Fixture-Content-Length"]),"retention_calls":0,
            "meaning":"multipart envelope admitted request; per-file MAX+1 sentinel rejected file"})

    def test_300_second_pcm_recording_and_over_duration_rejection(self):
        stream,duration=wave_file(seconds=300)
        with stream: response=self.recording(stream,duration)
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertTrue(response.get_json()["success"])
        self.assertEqual(len(self.transcriptions),1)
        self.assertEqual(self.transcriptions[0]["bytes"],4_800_044)
        self.assertFalse(response.get_json().get("audio_retained",False))
        stream,duration=wave_file(seconds=300.001)
        with stream: over=self.recording(stream,duration)
        self.assertEqual(over.status_code,400,over.get_json())
        self.assertIn("longer",over.get_json()["message"])
        self.assertEqual(len(self.transcriptions),1)
        RESULTS.append({"case":"recording_duration","exact_seconds":300,"exact_status":response.status_code,
            "exact_bytes":4_800_044,"over_seconds":duration,"over_status":over.status_code,
            "over_message":over.get_json()["message"],"local_transcription_stub_calls":1,
            "route_envelope":int(response.headers["X-Fixture-Envelope"]),
            "actual_provider_calls":0,"limitation":"existing admission uses submitted duration; valid PCM fixture independently confirms its frame duration"})

    def test_audio_20mib_byte_limit_is_independent_of_300_seconds_and_50mb(self):
        stream,duration=wave_file(total_bytes=20*1024*1024)
        with stream: response=self.recording(stream,duration)
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(self.transcriptions[0]["bytes"],20*1024*1024)
        self.assertLess(duration,300)
        stream,duration=wave_file(total_bytes=20*1024*1024)
        stream.seek(0,2); stream.write(b"x");stream.seek(0)
        with stream: over=self.recording(stream,duration)
        self.assertEqual(over.status_code,400,over.get_json())
        self.assertIn("larger",over.get_json()["message"])
        self.assertEqual(len(self.transcriptions),1)
        RESULTS.append({"case":"recording_bytes","exact_bytes":20*1024*1024,"exact_seconds":duration,
            "exact_status":response.status_code,"over_bytes":20*1024*1024+1,"over_status":over.status_code,
            "over_message":over.get_json()["message"],"actual_provider_calls":0})

    def test_text_utf16_limit_stays_20000(self):
        text="\U0001f642"*10_000
        body={"type":"add_submission","request_id":str(uuid4()),"text":text}
        response=self.client.post("/api/resume-intake/me/submissions",headers=self.headers,data={"request":json.dumps(body)})
        self.assertEqual(response.status_code,200,response.get_json())
        body.update(request_id=str(uuid4()),text=text+"x")
        over=self.client.post("/api/resume-intake/me/submissions",headers=self.headers,data={"request":json.dumps(body)})
        self.assertEqual(over.status_code,400,over.get_json())
        RESULTS.append({"case":"text_utf16","exact_units":20_000,"exact_status":response.status_code,
            "over_units":20_001,"over_status":over.status_code,"over_message":over.get_json()["message"]})

    def test_workspace_policy_ui_payload_carries_separate_selected_limits(self):
        response=self.client.get("/api/resume-intake/me")
        self.assertEqual(response.status_code,200,response.get_json())
        policy=response.get_json()["policy"]
        self.assertEqual(policy["max_document_bytes"],50_000_000)
        self.assertEqual(policy["max_recording_seconds"],300)
        self.assertEqual(policy["max_text_units"],20_000)
        self.assertEqual(policy["max_recording_bytes"],20*1024*1024)
        self.assertTrue(policy["selected"])
        RESULTS.append({"case":"workspace_policy_ui_payload","status":response.status_code,"policy":policy})

    def test_unrelated_global_envelope_is_exactly_two_mib(self):
        exact=self.client.post("/unrelated",data=b"x"*(2*1024*1024))
        self.assertEqual(exact.status_code,200)
        over=self.client.post("/unrelated",data=b"x"*(2*1024*1024+1))
        self.assertEqual(over.status_code,413)
        self.assertEqual(self.app.config["MAX_CONTENT_LENGTH"],2*1024*1024)
        RESULTS.append({"case":"unrelated_global","exact_bytes":2*1024*1024,"exact_status":exact.status_code,
            "over_bytes":2*1024*1024+1,"over_status":over.status_code,
            "configured_global_envelope":self.app.config["MAX_CONTENT_LENGTH"]})
