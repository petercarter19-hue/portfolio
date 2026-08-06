# One-click PS-WORKSHOP-002 gate runner for Pete.
# Run from the repository root on a machine with az CLI + the local Python venv:
#   powershell -ExecutionPolicy Bypass -File scripts\gate_workshop_002.ps1
# It creates a disposable Basic-tier database, proves the leg-9 backlog-
# confirmation migration against it (apply, no-op reapply, verify, rollback,
# reapply), deletes the database, and pushes the recorded gate proof on a
# branch named work/workshop-002-gate-proof. The waiting automation takes
# over from there: governed apply, merge of the held implementation branch,
# deploy, and live smoke.
$ErrorActionPreference = 'Stop'
if (-not (Test-Path "SQL FIles/Migrations/registry.json")) {
    throw "Run this from the repository root (portfolio)."
}
git fetch origin main
git checkout -B work/workshop-002-gate-proof origin/main

$stamp = Get-Date -Format "yyyyMMddHHmm"
$db = "ps-workshop-002-gate-$stamp"
$python = if (Test-Path "venv\Scripts\python.exe") { "venv\Scripts\python.exe" } else { "python" }

Write-Host "Creating disposable database $db ..."
az sql db create --resource-group peerslate --server peerslate --name $db `
    --service-objective Basic --collation SQL_Latin1_General_CP1_CI_AS | Out-Null

try {
    Write-Host "Gating PS-WORKSHOP-002 against $db ..."
    & $python scripts/govern_sql_migrations.py --database $db gate PS-WORKSHOP-002 `
        --expect-database $db --operator "Pete" --update-registry
    if ($LASTEXITCODE -ne 0) { throw "Gate failed; registry not updated. Nothing was pushed." }
}
finally {
    Write-Host "Deleting disposable database $db ..."
    az sql db delete --resource-group peerslate --server peerslate --name $db --yes | Out-Null
}

git add "SQL FIles/Migrations/registry.json"
git commit -m "chore(workshop): record the PS-WORKSHOP-002 gate proof

Disposable database $db, operator Pete, recorded by scripts/gate_workshop_002.ps1."
git push -u origin work/workshop-002-gate-proof
Write-Host ""
Write-Host "Done. The gate proof is pushed; the automation completes the apply,"
Write-Host "the held implementation branch merge, the deploy, and the live smoke"
Write-Host "from here."
