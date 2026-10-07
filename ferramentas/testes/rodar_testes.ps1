# Roda o teste de ponta a ponta do portal num Edge headless, contra um Apps Script simulado.
# Uso (PowerShell, na raiz do repositório):  .\ferramentas\testes\rodar_testes.ps1
# Não toca na planilha real. Saída: uma linha PASS/FAIL por verificação.
$ErrorActionPreference = "Stop"
$aqui = $PSScriptRoot
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$perfil = Join-Path $env:TEMP ("vd-teste-" + (Get-Random))
$saida = Join-Path $env:TEMP "vd-teste-dom.txt"

$srv = Start-Process python -ArgumentList "`"$aqui\servidor_simulado.py`"", "8766" -PassThru -WindowStyle Hidden
Start-Sleep 2
try {
  # --virtual-time-budget acelera os setTimeout do teste; a página escreve o resultado em <pre id="log">
  $p = Start-Process -FilePath $edge -ArgumentList "--headless=new","--disable-gpu","--no-first-run","--user-data-dir=$perfil","--virtual-time-budget=240000","--dump-dom","http://127.0.0.1:8766/__teste.html" -PassThru -WindowStyle Hidden -RedirectStandardOutput $saida
  if (-not $p.WaitForExit(240000)) { Stop-Process -Id $p.Id -Force; Write-Host "TIMEOUT"; exit 1 }
} finally {
  Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue
}
$t = [IO.File]::ReadAllText($saida, [Text.Encoding]::UTF8)
if ($t -match '(?s)<pre id="log">(.*?)</pre>') {
  $log = [System.Net.WebUtility]::HtmlDecode($matches[1])
  Write-Host $log
  $falhas = ([regex]::Matches($log, '^(FAIL|ERRO)', 'Multiline')).Count
  Write-Host "---"
  Write-Host ("PASS: {0}  FAIL/ERRO: {1}" -f ([regex]::Matches($log, '^PASS', 'Multiline')).Count, $falhas)
  if ($falhas) { exit 1 }
} else {
  Write-Host "Não foi possível ler o resultado do teste."; exit 1
}
