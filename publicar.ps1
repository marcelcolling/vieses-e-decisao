# Publica o portal no GitHub e ativa o GitHub Pages.
# Uso (PowerShell, na pasta do repositório):  .\publicar.ps1
# Pré-requisito: ter feito login uma vez com:  gh auth login
param([string]$Nome = "vieses-e-decisao")

$ErrorActionPreference = "Stop"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
Set-Location $PSScriptRoot

gh auth status | Out-Null
$usuario = gh api user --jq .login

if (-not (git remote 2>$null | Select-String -Quiet "origin")) {
    gh repo create $Nome --public --source . --remote origin --description "Portal da disciplina Vieses e Decisão"
}
git push -u origin main

# Ativa o GitHub Pages (branch main, pasta raiz). Se já estiver ativo, apenas segue.
try {
    gh api -X POST "repos/$usuario/$Nome/pages" -f "source[branch]=main" -f "source[path]=/" | Out-Null
} catch { }
Write-Host ""
Write-Host "Pronto. Em 1-2 minutos o site estará em: https://$usuario.github.io/$Nome/"
