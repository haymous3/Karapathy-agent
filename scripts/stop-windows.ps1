$ErrorActionPreference = "Stop"

$containerName = "pm-mvp-app"

$existing = docker ps -aq --filter "name=^${containerName}$"
if ($existing) {
  Write-Host "Stopping and removing container: $containerName"
  docker rm -f $containerName | Out-Null
  Write-Host "Container removed."
} else {
  Write-Host "Container not found: $containerName"
}
