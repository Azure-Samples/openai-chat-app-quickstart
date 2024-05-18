. ./scripts/load_azd_env.ps1

. ./scripts/load_python_env.ps1

$venvPythonPath = "./scripts/.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./scripts/.venv/bin/python"
}

Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/auth_update.py" -Wait -NoNewWindow

azd env set OPENAICOM_API_KEY ""