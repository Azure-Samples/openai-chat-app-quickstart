Write-Host ""
Write-Host "Copying azd environment variables to .env file"
Write-Host ""

$output = azd env get-values

Add-Content -Path .env -Value $output