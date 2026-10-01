"""Owned isolated actual-duration inspection for Resume WebM/Opus and PCM WAV.

No filename/URL/provider/credentials enter the child. It reads one bounded byte
payload, validates complete container elements and fully decodes audio samples.
Private decoder diagnostics are discarded; result JSON is content-free.
"""
from __future__ import annotations
import io
import json
import math
from fractions import Fraction
from pathlib import Path
import subprocess
import sys
import sysconfig

MAX_BYTES=20*1024*1024
CHILD_MEMORY=512*1024*1024
WALL_SECONDS=8
MAX_ELEMENTS=100000
MAX_FRAMES=60000


class ProbeRefusal(Exception):
    def __init__(self,code):self.code=code


def _vint(data,pos,*,identifier=False):
    if pos>=len(data) or data[pos]==0:raise ProbeRefusal("malformed")
    first=data[pos];width=1
    while not first & (1<<(8-width)):
        width+=1
        if width>8:raise ProbeRefusal("malformed")
    if identifier and width>4 or pos+width>len(data):raise ProbeRefusal("malformed")
    value=int.from_bytes(data[pos:pos+width],"big")
    if not identifier:value&=(1<<(7*width))-1
    return value,pos+width,not identifier and value==(1<<(7*width))-1


def _webm_complete(data):
    # Unknown-length Segment/Cluster are normal MediaRecorder streaming WebM.
    # Every finite child, especially the final audio Block, must be complete.
    masters={0x1A45DFA3,0x18538067,0x1549A966,0x1654AE6B,0xAE,0xE1,0x1F43B675,0xA0,
             0x1C53BB6B,0xBB,0xB7,0x1254C367,0x7373,0x67C8,0x114D9B74,0x4DBB}
    segment_siblings={0x1F43B675,0x1549A966,0x1654AE6B,0x1C53BB6B,0x1254C367,0x114D9B74}
    count=0;doc_type=None;blocks=0
    def scan(pos,end,parent=None,unknown_parent=False,depth=0):
        nonlocal count,doc_type,blocks
        if depth>12:raise ProbeRefusal("malformed")
        while pos<end:
            begin=pos;tag,pos,_=_vint(data,pos,identifier=True)
            if parent==0x1F43B675 and unknown_parent and tag in segment_siblings:return begin
            size,pos,unknown=_vint(data,pos)
            count+=1
            if count>MAX_ELEMENTS:raise ProbeRefusal("probe_bounds")
            if unknown and tag not in {0x18538067,0x1F43B675}:raise ProbeRefusal("malformed")
            stop=end if unknown else pos+size
            if stop>end:raise ProbeRefusal("malformed")
            if tag==0x4282:doc_type=data[pos:stop]
            if tag in {0xA3,0xA1}:blocks+=1
            if tag in masters:
                pos=scan(pos,stop,tag,unknown,depth+1)
                if not unknown and pos!=stop:raise ProbeRefusal("malformed")
            else:pos=stop
        return pos
    if not data.startswith(b"\x1aE\xdf\xa3"):raise ProbeRefusal("unsupported")
    scan(0,len(data))
    if doc_type!=b"webm" or blocks<1:raise ProbeRefusal("unsupported")


def _wave_complete(data):
    if len(data)<44 or data[:4]!=b"RIFF" or data[8:12]!=b"WAVE":raise ProbeRefusal("unsupported")
    if int.from_bytes(data[4:8],"little")+8!=len(data):raise ProbeRefusal("malformed")
    pos=12;data_size=None;block_align=None
    while pos<len(data):
        if pos+8>len(data):raise ProbeRefusal("malformed")
        tag=data[pos:pos+4];size=int.from_bytes(data[pos+4:pos+8],"little");pos+=8
        end=pos+size
        if end+(size&1)>len(data):raise ProbeRefusal("malformed")
        if tag==b"fmt ":
            if size<16 or int.from_bytes(data[pos:pos+2],"little") not in {1,3}:raise ProbeRefusal("unsupported")
            block_align=int.from_bytes(data[pos+12:pos+14],"little")
        if tag==b"data":
            if data_size is not None:raise ProbeRefusal("malformed")
            data_size=size
        pos=end+(size&1)
    if not block_align or not data_size or data_size%block_align:raise ProbeRefusal("malformed")


def _inspect(data,content_type,maximum_seconds):
    if not data or len(data)>MAX_BYTES:raise ProbeRefusal("too-large")
    if content_type=="audio/webm":_webm_complete(data);fmt="matroska";codecs={"opus"}
    elif content_type in {"audio/wav","audio/x-wav"}:
        _wave_complete(data);fmt="wav";codecs={"pcm_s16le","pcm_u8","pcm_s24le","pcm_s32le","pcm_f32le","pcm_f64le"}
    else:raise ProbeRefusal("unsupported")
    try:import av
    except ImportError:raise ProbeRefusal("probe_unavailable") from None
    if av.__version__!="18.1.0":raise ProbeRefusal("probe_unavailable")
    ceiling=Fraction(str(maximum_seconds));total=Fraction(0);first=None;last=None;quantum=Fraction(0);frames=0
    av.logging.set_level(av.logging.ERROR)
    with av.logging.Capture() as logs:
        with av.open(io.BytesIO(data),format=fmt,options={"err_detect":"explode"}) as container:
            if len(container.streams)!=1 or len(container.streams.audio)!=1:raise ProbeRefusal("unsupported")
            stream=container.streams.audio[0]
            if stream.codec_context.name not in codecs:raise ProbeRefusal("unsupported")
            stream.codec_context.thread_count=1
            stream.codec_context.options={"err_detect":"explode"}
            for frame in container.decode(stream):
                frames+=1
                rate=frame.sample_rate;samples=frame.samples
                if (frames>MAX_FRAMES or not 8000<=rate<=192000 or not 1<=samples<=65536
                        or not 1<=len(frame.layout.channels)<=2):raise ProbeRefusal("probe_bounds")
                span=Fraction(samples,rate);total+=span
                if frame.pts is None or frame.time_base is None:raise ProbeRefusal("malformed")
                start=Fraction(frame.pts)*frame.time_base
                quantum=max(quantum,Fraction(frame.time_base))
                if first is None:first=start
                # Decoded sample count cannot be shortened by forged timestamps.
                # Timestamp span additionally catches actual silent gaps, using
                # its precise lower bound because WebM timestamps are quantized.
                if last is not None and start<last-quantum:raise ProbeRefusal("malformed")
                last=start+span
                observed=max(total,last-first-quantum)
                if observed>ceiling:raise ProbeRefusal("too-long")
    if frames==0 or total<=0 or logs:raise ProbeRefusal("malformed")
    duration=max(total,last-first-quantum)
    return {"ok":True,"duration_numerator":duration.numerator,"duration_denominator":duration.denominator}


_WINDOWS_JOB=None

def _limit_child():
    # Unlike a lifetime app decoder, this process owns all native allocations.
    # Enforce a hard512MiB limit on Linux/Windows before untrusted byte handling.
    global _WINDOWS_JOB
    if sys.platform=="win32":
        import ctypes
        from ctypes import wintypes
        class Basic(ctypes.Structure):
            _fields_=[("process_time",ctypes.c_int64),("job_time",ctypes.c_int64),("flags",wintypes.DWORD),
                      ("minimum",ctypes.c_size_t),("maximum",ctypes.c_size_t),("active",wintypes.DWORD),
                      ("affinity",ctypes.c_size_t),("priority",wintypes.DWORD),("scheduling",wintypes.DWORD)]
        class Io(ctypes.Structure):_fields_=[(name,ctypes.c_uint64) for name in ("read_ops","write_ops","other_ops","read_bytes","write_bytes","other_bytes")]
        class Extended(ctypes.Structure):
            _fields_=[("basic",Basic),("io",Io),("process_memory",ctypes.c_size_t),("job_memory",ctypes.c_size_t),
                      ("peak_process",ctypes.c_size_t),("peak_job",ctypes.c_size_t)]
        kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        kernel.CreateJobObjectW.restype=wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        kernel.GetCurrentProcess.restype=wintypes.HANDLE
        kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
        handle=kernel.CreateJobObjectW(None,None);limits=Extended();limits.basic.flags=0x100|0x2000;limits.process_memory=CHILD_MEMORY
        if not handle or not kernel.SetInformationJobObject(handle,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(handle,kernel.GetCurrentProcess()):
            raise ProbeRefusal("probe_unavailable")
        _WINDOWS_JOB=handle
    else:
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS,(CHILD_MEMORY,CHILD_MEMORY))
        except (ImportError,OSError,ValueError):raise ProbeRefusal("probe_unavailable") from None


def _worker():
    try:
        _limit_child()
        # -I -S excludes cwd, PYTHONPATH, user site and all startup/.pth hooks.
        # Only the parent-selected installed dependency directory is restored;
        # no site initialization or environment-based path discovery runs here.
        package_root=Path(sys.argv[3]).resolve()
        if not package_root.is_dir() or not (package_root/'av/__init__.py').is_file():
            raise ProbeRefusal("probe_unavailable")
        sys.path.append(str(package_root))
        header=sys.stdin.buffer.readline(1025)
        if len(header)>1024 or not header.endswith(b"\n"):raise ProbeRefusal("malformed")
        settings=json.loads(header)
        if set(settings)!={"content_type","maximum_seconds"}:raise ProbeRefusal("malformed")
        data=sys.stdin.buffer.read(MAX_BYTES+1)
        result=_inspect(data,settings["content_type"],settings["maximum_seconds"])
    except ProbeRefusal as error:result={"ok":False,"code":error.code}
    except Exception:result={"ok":False,"code":"malformed"}
    sys.stdout.write(json.dumps(result,separators=(",",":")))
    sys.stdout.flush()


def _dependency_root():
    # App/venv installation roots, plus the existing Windows local-test user
    # installation. These are interpreter-derived, never request/env paths.
    roots=[sysconfig.get_path("purelib"),sysconfig.get_path("platlib")]
    if sys.platform=="win32":
        import site
        roots.append(site.USER_SITE)
    for root in roots:
        if root:
            path=Path(root).resolve()
            if (path/'av/__init__.py').is_file():return path
    raise ProbeRefusal("probe_unavailable")


def _child_environment():
    # Linux wheel native libraries use their bundled loader paths. Windows
    # requires the OS directory; read it from the OS, not inherited app env.
    if sys.platform!="win32":return {}
    import ctypes
    buffer=ctypes.create_unicode_buffer(32768)
    length=ctypes.WinDLL("kernel32",use_last_error=True).GetWindowsDirectoryW(buffer,len(buffer))
    if not length or length>=len(buffer):raise ProbeRefusal("probe_unavailable")
    return {"SystemRoot":buffer.value}


def probe_duration(data,content_type,policy):
    if not isinstance(data,bytes) or not data or len(data)>policy.max_recording_bytes or len(data)>MAX_BYTES:
        raise ProbeRefusal("too-large")
    if content_type not in {"audio/webm","audio/wav","audio/x-wav"}:raise ProbeRefusal("unsupported")
    header=json.dumps({"content_type":content_type,"maximum_seconds":policy.max_recording_seconds},separators=(",",":")).encode()+b"\n"
    try:
        child=subprocess.run([sys.executable,"-I","-S","-B",str(Path(__file__).resolve()),
            "--inspect","--package-root",str(_dependency_root())],env=_child_environment(),
            input=header+data,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=WALL_SECONDS,
            check=False)
    except (OSError,subprocess.TimeoutExpired):raise ProbeRefusal("probe_unavailable") from None
    if child.returncode or len(child.stdout)>1024:raise ProbeRefusal("probe_unavailable")
    try:
        result=json.loads(child.stdout)
        if not result.get("ok"):raise ProbeRefusal(result.get("code") if result.get("code") in {"malformed","unsupported","too-long","too-large","probe_bounds","probe_unavailable"} else "malformed")
        numerator=result["duration_numerator"];denominator=result["duration_denominator"]
        if type(numerator) is not int or type(denominator) is not int or numerator<1 or denominator<1:raise ValueError()
        duration=Fraction(numerator,denominator)
        if duration>Fraction(str(policy.max_recording_seconds)):raise ProbeRefusal("too-long")
        return float(duration)
    except ProbeRefusal:raise
    except (ValueError,TypeError,KeyError):raise ProbeRefusal("malformed") from None


if __name__=="__main__":
    if len(sys.argv)!=4 or sys.argv[1:3]!=["--inspect","--package-root"]:raise SystemExit(2)
    _worker()
else:
    from dataclasses import replace
    from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter,RecordingIntakeError
    class ProbedResumeTranscriptionAdapter(ResumeTranscriptionAdapter):
        def admit_bytes(self,content_type,data,duration_seconds,policy):
            # The supplied clock value is advisory only; actual decoded samples
            # and container integrity qualify all audio before Speech/claims.
            try:actual=probe_duration(data,content_type,policy)
            except ProbeRefusal as error:
                messages={"malformed":"That recording could not be checked safely. Keep typing.",
                          "unsupported":"That recording format cannot be checked safely. Keep typing.",
                          "probe_bounds":"That recording could not be checked safely. Keep typing.",
                          "probe_unavailable":"Recording checks are unavailable. Keep typing."}
                raise RecordingIntakeError(error.code,messages.get(error.code)) from None
            return super().admit_bytes(content_type,data,actual,policy)
        def transcribe(self,validated,policy,*,transcribe=None):
            return replace(super().transcribe(validated,policy,transcribe=transcribe),duration_seconds=validated.duration_seconds)
