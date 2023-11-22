param (
    [Parameter(Mandatory=$true)]
    [string]$tenantId
)

. ./scripts/load_azd_env.ps1

if (-not $env:AZURE_USE_AUTHENTICATION) {
  Exit 0
}

. ./scripts/load_python_env.ps1

$venvPythonPath = "./scripts/.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./scripts/.venv/bin/python"
}

Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/setup_for_external_id.py", $tenantId -Wait -NoNewWindow