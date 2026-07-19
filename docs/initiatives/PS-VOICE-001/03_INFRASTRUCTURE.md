# PS-VOICE-001 Infrastructure Contract

## Verified starting point - 2026-07-18

- Resource group: `peerslate`
- App Service: `peerslate-pete`
- App Service has a system-assigned managed identity.
- Azure AI Services account: `peerslate-foundry`, kind `AIServices`, region `eastus`, custom subdomain configured.
- No Storage account exists in the `peerslate` resource group.
- No Azure resource role assignment was observed for the web-app managed identity.

These are read-only inventory facts, not permission to reuse a resource without verification.

## Required production resources

The idempotent provisioning script must support `plan`, `apply`, and `verify` behavior and accept explicit resource names. It must never retrieve or print keys.

1. Create a globally unique General Purpose v2 Storage account in the existing resource group and an opaque private container dedicated to Capture source media.
2. Disable Blob public access, require TLS 1.2 or later, enable encryption at rest, use secure transfer, and disable shared-key access if the deployed SDK and management path are proved compatible.
3. Assign the App Service identity `Storage Blob Data Contributor` at the narrowest practical Blob/container scope.
4. Verify whether `peerslate-foundry` supports the selected Speech-to-text endpoint in its deployed region/account kind. If it does, assign the App Service identity `Cognitive Services Speech User` at that account scope. If it does not, stop and return a manager decision packet before creating a second AI account.
5. Add only nonsecret App Service settings for account URL, container, Speech endpoint/API version, locale, and limits.

## Credential-safe verification boundary

`verify` checks only resource posture, container privacy, managed-identity RBAC,
and the existing AI Services account's Speech-capable Entra endpoint. It must
never call `az webapp config appsettings list`, retrieve the App Service setting
collection, or inspect any setting value. A client-side query is not an
acceptable safeguard because Azure CLI receives the complete secret-bearing
response before filtering it.

`apply` writes the reviewed nonsecret Voice settings with output suppressed.
After apply, the known settings are proved through a signed-in functional Voice
lifecycle: private upload, Azure transcription, owner playback/export,
explicit deletion with final media absence, and continued text Capture
availability. This proves the configured behavior without reading unrelated App
Service settings or credentials.

## Approved integration direction

- Blob access: Azure SDK for Python using `DefaultAzureCredential` and the App Service managed identity.
- Transcription: the current official Azure Speech fast-transcription/AI Services endpoint using Microsoft Entra authentication and an accepted browser recording format.
- The implementation must pin reviewed dependency versions in `requirements.txt` and document size/startup impact.
- Local and CI tests use fakes/emulators or deterministic adapters. They must not require a developer credential, production resource, or live provider call.

## Production authority boundary

Codex may write and dry-run the infrastructure script, prove idempotence against an isolated disposable resource when safe, and document exact commands. Codex must not provision or modify production resources. ChatGPT Work owns production `plan`, explicit resource review, `apply`, role verification, database migration, PR, deployment, and live validation.

## Stop conditions

Stop and return to ChatGPT Work if:

- the current AI Services account cannot provide the required Speech endpoint under managed identity;
- shared-key disablement breaks a required Azure control path and no passwordless alternative is available;
- the app identity cannot receive the narrow roles;
- browser output needs media transcoding or a new runtime/native dependency;
- production requires a queue, worker, VNet/private endpoint, Key Vault secret, or paid resource not described here;
- any design would expose a public media URL or put a credential in the browser.

## Official implementation references

- Azure Blob Storage Python passwordless quickstart: <https://learn.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python>
- Upload a Blob with Python and Entra authorization: <https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-upload-python>
- Azure Speech Entra authentication: <https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-configure-azure-ad-auth>
- Speech role-based access control: <https://learn.microsoft.com/en-us/azure/ai-services/speech-service/role-based-access-control>
- Speech-to-text REST API: <https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-speech-to-text>
