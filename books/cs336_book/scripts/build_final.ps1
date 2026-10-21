param(
  [string]$EdgePath,
  [string]$OutputDir
)
$ErrorActionPreference='Stop'
$bookRoot=Split-Path -Parent $PSScriptRoot
$repoRoot=Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$manuscript=Join-Path $bookRoot 'manuscript\final'
if(-not $OutputDir){$OutputDir=$repoRoot}
if(-not $EdgePath){$candidates=@((Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),(Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'));$EdgePath=$candidates|Where-Object{Test-Path -LiteralPath $_}|Select-Object -First 1}
if(-not $EdgePath -or -not (Test-Path -LiteralPath $EdgePath)){throw 'Microsoft Edge executable not found; pass -EdgePath.'}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$profile=Join-Path $env:TEMP ('open-course-render-'+[guid]::NewGuid().ToString('N'))
try {
  foreach($edition in @(@{Html='book_print.html';Pdf='大语言模型从0构建-王自强_公开版.pdf';Subdir=''},@{Html='cornell.html';Pdf='大语言模型从0构建-王自强_康奈尔批注版.pdf';Subdir='editions'})){
    $html=Join-Path $manuscript $edition.Html
    $targetDir=$OutputDir
    if($edition.Subdir){$targetDir=Join-Path $OutputDir $edition.Subdir;New-Item -ItemType Directory -Force -Path $targetDir|Out-Null}
    $pdf=Join-Path $targetDir $edition.Pdf
    if(-not (Test-Path -LiteralPath $html)){throw "Missing print HTML: $html"}
    $uri=([System.Uri]$html).AbsoluteUri
    $args=@('--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-extensions','--no-pdf-header-footer',"--user-data-dir=$profile","--print-to-pdf=$pdf",$uri)
    $proc=Start-Process -FilePath $EdgePath -ArgumentList $args -Wait -PassThru
    if($proc.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $pdf)){throw "PDF render failed for $($edition.Html); exit=$($proc.ExitCode)"}
  }
} finally { if(Test-Path -LiteralPath $profile){Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue} }
