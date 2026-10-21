param(
  [string]$EdgePath,
  [string]$OutputDir
)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$manuscript=Join-Path $root 'manuscript\final'
if(-not $OutputDir){$OutputDir=Join-Path $root 'deliverables\final'}
if(-not $EdgePath){$candidates=@((Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),(Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'));$EdgePath=$candidates|Where-Object{Test-Path -LiteralPath $_}|Select-Object -First 1}
if(-not $EdgePath -or -not (Test-Path -LiteralPath $EdgePath)){throw 'Microsoft Edge executable not found; pass -EdgePath.'}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$CornellOutputDir=Join-Path $OutputDir 'editions'
New-Item -ItemType Directory -Force -Path $CornellOutputDir | Out-Null
$profile=Join-Path $env:TEMP ('cs336-render-'+[guid]::NewGuid().ToString('N'))
try {
  foreach($edition in @(@{Html='book_print.html';Pdf='大语言模型从0构建_合订本.pdf';Dir=$OutputDir},@{Html='cornell.html';Pdf='大语言模型从0构建_合订本.pdf';Dir=$CornellOutputDir})){
    $html=Join-Path $manuscript $edition.Html
    $pdf=Join-Path $edition.Dir $edition.Pdf
    if(-not (Test-Path -LiteralPath $html)){throw "Missing print HTML: $html"}
    $uri=([System.Uri]$html).AbsoluteUri
    $args=@('--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-extensions','--no-pdf-header-footer',"--user-data-dir=$profile","--print-to-pdf=$pdf",$uri)
    $proc=Start-Process -FilePath $EdgePath -ArgumentList $args -Wait -PassThru
    if($proc.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $pdf)){throw "PDF render failed for $($edition.Html); exit=$($proc.ExitCode)"}
  }
} finally { if(Test-Path -LiteralPath $profile){Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue} }
