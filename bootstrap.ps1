param(
    [switch]$SkipOllama,
    [switch]$SkipPython
)

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$ErrorActionPreference = "Stop"

Write-Host "CogniCore Portable - 首次运行准备" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# ---- Python Portable ----
if (-not $SkipPython -and -not (Test-Path "$ROOT\python\python.exe")) {
    Write-Host "[1/3] 下载便携 Python 3.12..." -ForegroundColor Yellow

    $pythonUrl = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip"
    $zipPath = "$env:TEMP\python-embed.zip"
    $extractPath = "$ROOT\python"

    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $zipPath -UseBasicParsing
        Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
        Remove-Item $zipPath -Force

        # Enable pip for embeddable Python
        $pthFile = Get-ChildItem "$extractPath\python*._pth" | Select-Object -First 1
        if ($pthFile) {
            $content = Get-Content $pthFile.FullName
            $content = $content -replace '#import site', 'import site'
            Set-Content -Path $pthFile.FullName -Value $content
        }
        Write-Host "  Python 便携版已下载到 $extractPath" -ForegroundColor Green
    } catch {
        Write-Host "  [错误] 下载失败：$($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  请手动下载 https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip"
        Write-Host "  解压到 $ROOT\python\"
        exit 1
    }
} elseif (-not $SkipPython) {
    Write-Host "[1/3] Python 已存在，跳过" -ForegroundColor Gray
}

# ---- Install pip + get-pip ----
$pythonExe = "$ROOT\python\python.exe"
if (Test-Path $pythonExe) {
    Write-Host "[2/3] 安装 pip..." -ForegroundColor Yellow
    $getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
    $getPipPath = "$env:TEMP\get-pip.py"

    try {
        Invoke-WebRequest -Uri $getPipUrl -OutFile $getPipPath -UseBasicParsing
        & $pythonExe $getPipPath --quiet > $null 2>&1
        Remove-Item $getPipPath -Force
        Write-Host "  pip 安装完成" -ForegroundColor Green
    } catch {
        Write-Host "  [跳过] pip 安装失败，可后续手动安装" -ForegroundColor DarkYellow
    }
}

# ---- Install dependencies ----
if (Test-Path $pythonExe) {
    Write-Host "[3/3] 安装 CogniCore 依赖..." -ForegroundColor Yellow
    $req = "$ROOT\cognicore\requirements.txt"
    if (Test-Path $req) {
        try {
            & $pythonExe -m pip install -r $req --quiet 2>&1 | Out-Null
            Write-Host "  依赖安装完成" -ForegroundColor Green
        } catch {
            Write-Host "  [跳过] 部分依赖可能未安装，运行 start.bat 时会自动重试" -ForegroundColor DarkYellow
        }
    }
}

# ---- Ollama ----
if (-not $SkipOllama -and -not (Test-Path "$ROOT\ollama\ollama.exe")) {
    Write-Host ""
    Write-Host "[可选] 下载 Ollama (AI 对话引擎)..." -ForegroundColor Yellow
    Write-Host "  建议手动下载: https://ollama.com/download/windows"
    Write-Host "  安装后将 ollama.exe 复制到 $ROOT\ollama\"
    Write-Host "  然后运行: ollama pull qwen2.5:1.5b"
    Write-Host "  (按回车键跳过)" -NoNewline
    Read-Host
}

Write-Host ""
Write-Host "准备完成！运行 start.bat 启动 CogniCore" -ForegroundColor Cyan
Write-Host ""
