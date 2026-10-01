"""Private originals isolation, bounded reads and recoverable lifecycle proof."""

import copy
import hashlib
from io import BytesIO
from types import SimpleNamespace
import unittest
from uuid import uuid4

from services.resume_original_file_repository import OriginalFileConflict, OriginalFileNotFound
from services.resume_original_file_service import ResumeOriginalFileService
from services.resume_original_storage_service import ResumeOriginalStorageService, ResumeOriginalStorageError


DATA = b"private original material"
PATH = "resume/v1/aa/" + "aa" * 16
ETAG = '"version-a"'


class CleanupBoundaryTests(unittest.TestCase):
    def test_cleanup_is_server_only_and_two_commands_bind_all_values(self):
        from unittest.mock import MagicMock,patch
        from services.database_service import ALLOWED_PROCEDURES,DatabaseService
        from services.resume_original_file_repository import SqlResumeOriginalCleanupAdapter,SqlResumeOriginalFileRepository
        workers={'usp_ClaimResumeOriginalCleanup','usp_CompleteResumeOriginalCleanup'}
        self.assertTrue(workers.isdisjoint(ALLOWED_PROCEDURES))
        with patch('services.database_service.get_connection') as browser_connection:
            for name in workers:
                with self.assertRaises(ValueError):DatabaseService().execute_procedure(name)
            browser_connection.assert_not_called()
        factory=MagicMock();connection=factory.return_value.__enter__.return_value;cursor=connection.cursor.return_value
        row={'original_key':str(uuid4()),'source_key':str(uuid4()),'source_version':1,'version':3,
            'blob_name':PATH,'blob_etag':ETAG,'content_type':'text/plain','byte_length':len(DATA),
            'sha256':hashlib.sha256(DATA).hexdigest(),'state':'delete_pending','downloadable':False}
        port=SqlResumeOriginalCleanupAdapter(connection_factory=factory)
        repository=SqlResumeOriginalFileRepository(DatabaseService(),cleanup=port)
        with patch('services.resume_original_file_repository.fetch_all_result_sets',return_value=[[row]]):
            self.assertEqual(repository.claim_cleanup(7)[0]['original_key'],row['original_key'])
        cursor.execute.assert_called_with('EXEC dbo.usp_ClaimResumeOriginalCleanup @Limit = ?',(7,))
        with patch('services.resume_original_file_repository.fetch_all_result_sets',return_value=[[{'completed':True}]]):
            repository.complete_cleanup(row,ETAG)
        cursor.execute.assert_called_with('EXEC dbo.usp_CompleteResumeOriginalCleanup @OriginalKey = ?, @ExpectedVersion = ?, @ConfirmedEtag = ?',
            (row['original_key'],3,ETAG))
        self.assertEqual(factory.call_count,2)
        self.assertEqual(cursor.close.call_count,2)

    def test_invalid_cleanup_arguments_and_unknown_statement_refuse_before_connection(self):
        from unittest.mock import MagicMock
        from services.resume_original_file_repository import SqlResumeOriginalCleanupAdapter
        factory=MagicMock();port=SqlResumeOriginalCleanupAdapter(connection_factory=factory)
        for value in (0,101,True,'25'):
            with self.assertRaises(ValueError):port.claim(value)
        for key,version in [('not-a-uuid',1),(str(uuid4()),0),(str(uuid4()),True)]:
            with self.assertRaises(ValueError):port.complete(key,version,ETAG)
        with self.assertRaises(ValueError):port._execute('EXEC dbo.usp_PurgeEverything',())
        factory.assert_not_called()

    def test_cleanup_failure_is_content_free_without_retry_and_closes_cursor(self):
        from unittest.mock import MagicMock
        from services.resume_original_file_repository import SqlResumeOriginalCleanupAdapter,OriginalFileUnavailable
        factory=MagicMock();cursor=factory.return_value.__enter__.return_value.cursor.return_value
        cursor.execute.side_effect=RuntimeError('private SQL/provider diagnostic')
        with self.assertRaises(OriginalFileUnavailable) as failed:
            SqlResumeOriginalCleanupAdapter(connection_factory=factory).claim(1)
        self.assertNotIn('private SQL/provider diagnostic',str(failed.exception))
        self.assertTrue(failed.exception.__suppress_context__)
        factory.assert_called_once();cursor.execute.assert_called_once();cursor.close.assert_called_once()


class Blob:
    def __init__(self, chunks=None):
        self.parts = [DATA] if chunks is None else chunks
        self.properties = SimpleNamespace(size=len(DATA), etag=ETAG)
        self.exists_now = True
        self.download_arguments = None
        self.delete_arguments = None
        self.read_count = 0
        self.fail_delete = False

    def get_blob_properties(self):
        if not self.exists_now:
            from azure.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError("Synthetic missing upload")
        return self.properties

    def download_blob(self, **kwargs):
        self.read_count += 1
        self.download_arguments = kwargs
        return SimpleNamespace(chunks=lambda: iter(self.parts))

    def delete_blob(self, **kwargs):
        self.delete_arguments = kwargs
        if self.fail_delete:
            raise RuntimeError("provider details must not escape")
        self.exists_now = False

    def exists(self):
        return self.exists_now


class Container:
    def __init__(self, blob):
        self.blob, self.paths, self.upload_arguments = blob, [], None

    def get_blob_client(self, path):
        self.paths.append(path)
        return self.blob

    def upload_blob(self, **kwargs):
        self.upload_arguments = kwargs
        return {"etag": ETAG}


def storage(blob=None):
    container = Container(blob or Blob())
    adapter = ResumeOriginalStorageService(
        account_url="https://fixture.blob.core.windows.net",
        container_name="private-resume-originals", client=container,
    )
    return adapter, container


class StorageTests(unittest.TestCase):
    def test_upload_create_only_and_no_member_metadata(self):
        adapter, container = storage()
        self.assertEqual(adapter.upload(PATH, DATA, "text/plain"), ETAG)
        self.assertIs(container.upload_arguments["overwrite"], False)
        self.assertIsNone(container.upload_arguments["metadata"])
        self.assertEqual(container.upload_arguments["content_settings"].content_type, "application/octet-stream")

    def test_read_has_chunk_bound_length_digest_and_etag(self):
        adapter, container = storage(Blob([DATA[:5], DATA[5:]]))
        self.assertEqual(adapter.read(PATH, etag=ETAG, byte_length=len(DATA), sha256=hashlib.sha256(DATA).hexdigest()), DATA)
        self.assertEqual(container.blob.download_arguments["length"], len(DATA) + 1)
        self.assertEqual(container.blob.download_arguments["etag"], ETAG)
        self.assertEqual(container.blob.download_arguments["max_concurrency"], 1)

    def test_corrupt_truncated_oversized_chunks_never_return_material(self):
        for chunks in ([b"bad"], [DATA[:-1]], [DATA + b"x"], [b"x" * (4 * 1024 * 1024 + 1)]):
            with self.subTest(size=len(chunks[0])):
                adapter, _ = storage(Blob(chunks))
                with self.assertRaises(ResumeOriginalStorageError) as raised:
                    adapter.read(PATH, etag=ETAG, byte_length=len(DATA), sha256=hashlib.sha256(DATA).hexdigest())
                self.assertEqual(str(raised.exception), "original_integrity_unavailable")

    def test_changed_properties_fail_before_download(self):
        for field, value in (("size", 50_000_001), ("etag", '"changed"')):
            adapter, container = storage()
            setattr(container.blob.properties, field, value)
            with self.assertRaises(ResumeOriginalStorageError):
                adapter.read(PATH, etag=ETAG, byte_length=len(DATA), sha256=hashlib.sha256(DATA).hexdigest())
            self.assertEqual(container.blob.read_count, 0)

    def test_client_paths_and_credential_origins_refused(self):
        adapter, _ = storage()
        for path in ("https://fixture/blob", "../private", "resume/v1/../" + "aa" * 16, "photo/v1/aa/" + "aa" * 16):
            with self.subTest(path=path), self.assertRaises(ResumeOriginalStorageError):
                adapter.upload(path, DATA, "text/plain")
        for origin in ("http://fixture.blob.core.windows.net", "https://fixture.blob.core.windows.net?sig=secret", "https://user@fixture.blob.core.windows.net", "https://evil.test"):
            with self.subTest(origin=origin), self.assertRaises(ResumeOriginalStorageError):
                ResumeOriginalStorageService(account_url=origin, container_name="private-resume-originals")

    def test_delete_conditional_and_confirmed_absence(self):
        adapter, container = storage()
        self.assertTrue(adapter.delete(PATH, etag=ETAG))
        self.assertEqual(container.blob.delete_arguments["etag"], ETAG)
        self.assertFalse(container.blob.exists_now)
        container.blob.fail_delete = True
        with self.assertRaises(ResumeOriginalStorageError) as raised:
            adapter.delete(PATH, etag=ETAG)
        self.assertEqual(str(raised.exception), "original_delete_pending")


class Metadata:
    """Semantic fixture of the closed SQL lifecycle; never called engine proof."""
    def __init__(self):
        self.rows, self.sources, self.events = {}, {}, []

    def list(self, owner, original_key=None):
        rows = []
        for key, row in self.rows.items():
            if row["owner"] != owner or (original_key and key != original_key):
                continue
            result = copy.deepcopy(row)
            result["downloadable"] = row["state"] == "uploaded" and row["blob_etag"] is not None
            rows.append(result)
        return rows

    def get(self, owner, original_key):
        rows = self.list(owner, original_key)
        if not rows:
            raise OriginalFileNotFound()
        return rows[0]

    def command(self, owner, payload):
        self.events.append(payload["type"])
        key = payload["original_key"]
        if payload["type"] == "reserve":
            self.rows[key] = {**payload, "owner": owner, "version": 1, "state": "reserved", "blob_etag": None, "created_at": "fixture"}
        else:
            row = self.rows.get(key)
            if row is None or row["owner"] != owner:
                raise OriginalFileNotFound()
            if payload["type"] == "delete" and row.get("delete_request_id") == payload["request_id"] and row["state"] in {"delete_pending", "deleted"}:
                return copy.deepcopy(row)
            if payload.get("expected_version", row["version"]) != row["version"]:
                raise OriginalFileConflict()
            if payload["type"] == "uploaded":
                if row["state"] not in {"reserved","delete_pending"} or row["blob_etag"] is not None:
                    raise OriginalFileConflict()
                row.update(state="uploaded" if row["state"]=="reserved" else row["state"], blob_etag=payload["blob_etag"])
            elif payload["type"] == "delete":
                row.update(state="delete_pending", delete_request_id=payload["request_id"])
            elif payload["type"] == "deleted":
                if row["blob_etag"] is None:raise OriginalFileConflict()
                row.update(state="deleted", blob_name=None, blob_etag=None)
            row["version"] += 1
        return copy.deepcopy(self.rows[key])

    def claim_cleanup(self,limit):
        return [copy.deepcopy(row) for row in self.rows.values()
                if row["state"]=="delete_pending" and row.get("delete_request_id")][:limit]

    def complete_cleanup(self,row,confirmed_etag):
        current=self.rows[row["original_key"]]
        if current["version"]!=row["version"] or current["state"]!="delete_pending" or not current.get("delete_request_id") or not confirmed_etag or current.get("blob_etag") not in (None,confirmed_etag):
            from services.resume_original_file_repository import OriginalFileUnavailable
            raise OriginalFileUnavailable()
        current.update(state="deleted",blob_name=None,blob_etag=None,version=current["version"]+1)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.adapter, self.container = storage()
        self.metadata = Metadata()
        self.service = ResumeOriginalFileService(repository=self.metadata, storage=self.adapter)
        self.source = {"source_key": str(uuid4()), "version": 1, "sha256": hashlib.sha256(DATA).hexdigest(), "content_type": "text/plain", "state": "active"}

    def retained(self):
        self.service.retain("owner", self.source, DATA)
        self.metadata.sources[("owner", self.source["source_key"])] = self.source
        return next(iter(self.metadata.rows))

    def test_sql_reservation_precedes_blob_and_confirmed_owner_file_survives_uncommitted_source(self):
        original_upload = self.adapter.upload
        def upload(*args, **kwargs):
            self.assertEqual(self.metadata.events, ["reserve"])
            staged=self.service.list("owner")
            self.assertEqual(len(staged),1)
            self.assertFalse(staged[0]["downloadable"])
            with self.assertRaises(OriginalFileNotFound):
                self.service.download("owner",staged[0]["original_key"])
            return original_upload(*args, **kwargs)
        self.adapter.upload = upload
        self.service.retain("owner", self.source, DATA)
        self.assertEqual(self.metadata.events, ["reserve", "uploaded"])
        key = next(iter(self.metadata.rows))
        self.assertEqual(self.service.download("owner",key),(DATA,"text/plain"))
        self.assertEqual(self.metadata.sources,{})
        self.assertEqual(self.service.reconcile(),{"completed":0,"pending":0})
        self.assertTrue(self.container.blob.exists_now)

    def test_foreign_original_never_reaches_blob_and_public_view_hides_paths(self):
        key = self.retained()
        for owner in ("foreign", "missing"):
            with self.assertRaises(OriginalFileNotFound):
                self.service.download(owner, key)
            self.assertEqual(self.service.list(owner), [])
        self.assertEqual(self.container.paths, [])
        shown = self.service.list("owner")[0]
        self.assertNotIn("blob_name", shown)
        self.assertNotIn("sha256", shown)
        self.assertNotIn("owner", shown)

    def test_original_delete_cas_pending_retry_and_preserved_source(self):
        key = self.retained()
        with self.assertRaises(OriginalFileConflict):
            self.service.delete("owner", key, expected_version=1, request_id=str(uuid4()))
        request = str(uuid4())
        self.container.blob.fail_delete = True
        result = self.service.delete("owner", key, expected_version=2, request_id=request)
        self.assertEqual(result["outcome"], "delete_pending")
        self.assertFalse(self.service.list("owner")[0]["downloadable"])
        self.container.blob.fail_delete = False
        result = self.service.delete("owner", key, expected_version=2, request_id=request)
        self.assertEqual(result["outcome"], "deleted")
        self.assertEqual(self.source["state"], "active")
        self.assertEqual(self.metadata.rows[key]["state"], "deleted")

    def test_source_purge_during_read_does_not_revoke_original_ownership(self):
        key = self.retained()
        original_read = self.adapter.read
        def read(*args, **kwargs):
            data = original_read(*args, **kwargs)
            self.source.update(state="purged", version=2)
            return data
        self.adapter.read = read
        self.assertEqual(self.service.download("owner",key),(DATA,"text/plain"))
        self.assertEqual(self.metadata.rows[key]["state"],"uploaded")
        self.assertEqual(self.service.reconcile(),{"completed":0,"pending":0})

    def test_member_original_delete_during_read_is_reauthorized_before_response(self):
        key=self.retained()
        original_read=self.adapter.read
        def read(*args,**kwargs):
            data=original_read(*args,**kwargs)
            self.service.delete("owner",key,expected_version=2,request_id=str(uuid4()))
            return data
        self.adapter.read=read
        with self.assertRaises(OriginalFileNotFound):
            self.service.download("owner",key)

    def test_source_absence_and_legacy_purge_never_schedule_original_cleanup(self):
        key=self.retained()
        self.source.update(state="purged",version=2,text=None)
        self.assertEqual(self.service.reconcile(),{"completed":0,"pending":0})
        self.metadata.sources.clear()
        self.assertEqual(self.service.download("owner",key),(DATA,"text/plain"))
        self.assertEqual(self.service.reconcile(),{"completed":0,"pending":0})
        self.assertTrue(self.container.blob.exists_now)
        self.assertEqual(self.service.delete("owner",key,expected_version=2,request_id=str(uuid4()))["outcome"],"deleted")

    def test_reconcile_finishes_only_explicit_member_delete_intent(self):
        key=self.retained()
        self.container.blob.fail_delete=True
        result=self.service.delete("owner",key,expected_version=2,request_id=str(uuid4()))
        self.assertEqual(result["outcome"],"delete_pending")
        self.assertEqual(self.service.reconcile(),{"completed":0,"pending":1})
        self.container.blob.fail_delete=False
        self.assertEqual(self.service.reconcile(),{"completed":1,"pending":0})
        self.assertEqual(self.metadata.rows[key]["state"],"deleted")

    def test_upload_failure_retains_durable_reservation(self):
        self.container.upload_blob = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("failure"))
        from services.resume_original_file_repository import OriginalFileUnavailable
        with self.assertRaises(OriginalFileUnavailable):
            self.service.retain("owner", self.source, DATA)
        self.assertEqual(next(iter(self.metadata.rows.values()))["state"], "reserved")
        self.assertEqual(self.metadata.events, ["reserve"])


    def test_unfinished_draft_expiry_and_parsed_source_purge_keep_member_original(self):
        from datetime import datetime,timedelta,timezone
        from werkzeug.datastructures import FileStorage
        from services.resume_intake_service import ResumeIntakeService
        from services.resume_intake_policy import SELECTED_RESUME_ONBOARDING_POLICY,sweep_parameters,MY_DATA_POLICY
        from services.resume_intake_repository import InMemoryResumeIntakeRepository
        from services.resume_draft_service import ResumeDraftService
        from services.resume_draft_repository import InMemoryResumeDraftRepository,InMemoryCanonicalCatalog
        service=ResumeIntakeService(repository=InMemoryResumeIntakeRepository(),
            draft_service=ResumeDraftService(repository=InMemoryResumeDraftRepository(),catalog=InMemoryCanonicalCatalog()),
            policy=SELECTED_RESUME_ONBOARDING_POLICY,original_files=self.service,
            document_pipeline=lambda *args,**kwargs:(DATA.decode(),"extracted",None,False,()))
        result=service.submit("owner",{"type":"add_submission","request_id":str(uuid4()),
            "attachments":[{"client_key":"file","kind":"document","filename":"fixture.txt","declared_content_type":"text/plain"}]},
            files={"file":FileStorage(stream=BytesIO(DATA),filename="fixture.txt",content_type="text/plain")})
        key=next(iter(self.metadata.rows));source_key=self.metadata.rows[key]["source_key"]
        created=datetime(2026,9,30,tzinfo=timezone.utc)
        service.save_draft("owner",{"request_id":str(uuid4()),"text":"Unfinished words","items":[],"attachments":[]},now=created)
        self.assertIsNone(service.get_draft("owner",now=created+timedelta(days=31))["draft"])
        self.assertEqual(self.service.download("owner",key),(DATA,"text/plain"))
        parsed=service.purge_source("owner",{"source_key":source_key,"request_id":str(uuid4())})
        self.assertTrue(parsed["original_files_retained"])
        self.assertIn("delete them separately",parsed["message"])
        self.assertEqual(service._load("owner")["sources"][source_key]["state"],"purged")
        self.assertEqual(self.service.download("owner",key),(DATA,"text/plain"))
        self.assertEqual(self.service.reconcile(),{"completed":0,"pending":0})
        self.assertFalse(sweep_parameters(SELECTED_RESUME_ONBOARDING_POLICY)["scheduled"])
        self.assertEqual(sweep_parameters(SELECTED_RESUME_ONBOARDING_POLICY)["draft_inactivity_days"],30)
        self.assertTrue(sweep_parameters(MY_DATA_POLICY)["scheduled"])
        self.assertEqual(self.service.delete("owner",key,expected_version=2,request_id=str(uuid4()))["outcome"],"deleted")


if __name__ == "__main__":
    unittest.main()


class LateUploadDeletionTests(unittest.TestCase):
    setUp=LifecycleTests.setUp
    # Controlled real storage-adapter ordering; no Azure/SQL execution.
    def test_delete_during_upload_keeps_intent_and_blocks_access_until_completion(self):
        import threading
        from services.resume_original_file_repository import OriginalFileUnavailable
        entered=threading.Event();release=threading.Event();finished=threading.Event();errors=[]
        self.container.blob.exists_now=False
        def delayed_upload(**kwargs):
            entered.set()
            if not release.wait(5):raise RuntimeError("fixture timeout")
            self.container.blob.exists_now=True
            return {"etag":ETAG}
        self.container.upload_blob=delayed_upload
        def writer():
            try:self.service.retain("owner",self.source,DATA)
            except Exception as error:errors.append(type(error).__name__)
            finally:finished.set()
        thread=threading.Thread(target=writer,daemon=True);thread.start()
        try:
            self.assertTrue(entered.wait(5))
            key=next(iter(self.metadata.rows));path=self.metadata.rows[key]["blob_name"]
            result=self.service.delete("owner",key,expected_version=1,request_id=str(uuid4()))
            self.assertEqual(result["outcome"],"delete_pending")
            with self.assertRaises(OriginalFileNotFound):self.service.download("owner",key)
            restarted=ResumeOriginalFileService(repository=self.metadata,storage=self.adapter)
            self.assertEqual(restarted.reconcile(),{"completed":0,"pending":1})
            self.assertEqual(self.metadata.rows[key]["blob_name"],path)
            self.assertIsNotNone(self.metadata.rows[key]["delete_request_id"])
            release.set();self.assertTrue(finished.wait(5));thread.join(5)
            self.assertEqual(errors,[])
            self.assertEqual(self.metadata.rows[key]["state"],"deleted")
            self.assertFalse(self.container.blob.exists_now)
        finally:release.set();thread.join(5)

    def test_lost_upload_reply_restart_waits_for_late_blob_then_recovers_only_explicit_delete(self):
        from services.resume_original_file_repository import OriginalFileUnavailable
        self.container.blob.exists_now=False
        self.container.upload_blob=lambda **kwargs:(_ for _ in ()).throw(RuntimeError("uncertain reply"))
        with self.assertRaises(OriginalFileUnavailable):self.service.retain("owner",self.source,DATA)
        key=next(iter(self.metadata.rows));path=self.metadata.rows[key]["blob_name"]
        self.assertEqual(self.service.reconcile(),{"completed":0,"pending":0})
        self.assertEqual(self.service.delete("owner",key,expected_version=1,request_id=str(uuid4()))["outcome"],"delete_pending")
        restarted_metadata=Metadata();restarted_metadata.rows=copy.deepcopy(self.metadata.rows)
        restarted=ResumeOriginalFileService(repository=restarted_metadata,storage=self.adapter)
        self.assertEqual(restarted.reconcile(),{"completed":0,"pending":1})
        self.assertEqual(restarted_metadata.rows[key]["blob_name"],path)
        self.container.blob.exists_now=True # eventual single create-only commit
        self.assertEqual(restarted.reconcile(),{"completed":1,"pending":0})
        self.assertFalse(self.container.blob.exists_now)
        self.assertEqual(restarted_metadata.rows[key]["state"],"deleted")
        with self.assertRaises(OriginalFileNotFound):restarted.download("owner",key)


class SingleCreateBoundaryTests(unittest.TestCase):
    def test_sdk_is_single_put_create_only_without_hidden_retry(self):
        from unittest.mock import patch
        adapter=ResumeOriginalStorageService(account_url="https://fixture.blob.core.windows.net",
            container_name="private-resume-originals",credential=object())
        with patch('azure.storage.blob.ContainerClient') as client:
            adapter._client()
        self.assertEqual(client.call_args.kwargs['max_single_put_size'],50_000_000)
        self.assertEqual(client.call_args.kwargs['retry_total'],0)
