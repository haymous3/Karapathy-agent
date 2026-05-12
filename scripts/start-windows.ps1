$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$imageName = "pm-mvp-app:latest"
$containerName = "pm-mvp-app"
$port = if ($env:PM_MVP_PORT) { [int]$env:PM_MVP_PORT } else { 8000 }

docker info *> $null
if ($LASTEXITCODE -ne 0) {
  throw "Docker daemon is not reachable. Start Docker Desktop, then rerun this script."
}

Write-Host "Building Docker image: $imageName"
docker build -t $imageName .
if ($LASTEXITCODE -ne 0) {
  throw "Docker build failed."
}

$existing = docker ps -aq --filter "name=^${containerName}$"
if ($LASTEXITCODE -ne 0) {
  throw "Unable to inspect existing containers."
}
if ($existing) {
  Write-Host "Removing existing container: $containerName"
  docker rm -f $containerName | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to remove existing container."
  }
}

Write-Host "Starting container: $containerName on port $port"
docker run -d --name $containerName -p "${port}:8000" --env-file ".env" $imageName | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Docker run failed. If port $port is busy, rerun with PM_MVP_PORT set to a free port (for example 8001)."
}

Write-Host "Waiting for service warm-up..."
Start-Sleep -Seconds 1

$health = $null
for ($i = 0; $i -lt 20; $i++) {
  try {
    $health = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:$port/health"
    break
  } catch {
    Start-Sleep -Seconds 1
  }
}

if (-not $health) {
  throw "Service did not become healthy in time."
}

Write-Host "Health response: $($health | ConvertTo-Json -Compress)"
Write-Host "App available at http://127.0.0.1:$port/"
