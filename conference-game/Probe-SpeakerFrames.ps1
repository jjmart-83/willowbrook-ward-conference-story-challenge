param(
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$OutputPath
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
        $_.Name -eq 'AsTask' -and
        $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    } |
    Select-Object -First 1

if (-not $asTaskMethod) {
    throw 'The Windows Runtime async bridge is unavailable.'
}

function Wait-WinRT {
    param($Operation, [Type]$ResultType)
    $method = $asTaskMethod.MakeGenericMethod($ResultType)
    $task = $method.Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}

$ocrType = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$fileType = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$streamType = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage, ContentType=WindowsRuntime]
$decoderType = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$bitmapType = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$resultType = [Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime]
$engine = $ocrType::TryCreateFromUserProfileLanguages()

if (-not $engine) {
    throw 'Windows OCR is unavailable. Install an OCR language pack in Windows Settings.'
}

$manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$results = [System.Collections.Generic.List[object]]::new()

foreach ($talk in @($manifest)) {
    foreach ($frame in @($talk.frames)) {
        $stream = $null
        $bitmap = $null
        try {
            $file = Wait-WinRT ($fileType::GetFileFromPathAsync([string]$frame.path)) $fileType
            $stream = Wait-WinRT ($file.OpenAsync([Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime]::Read)) $streamType
            $decoder = Wait-WinRT ($decoderType::CreateAsync($stream)) $decoderType
            $bitmap = Wait-WinRT ($decoder.GetSoftwareBitmapAsync()) $bitmapType
            $recognized = Wait-WinRT ($engine.RecognizeAsync($bitmap)) $resultType
            $text = [string]$recognized.Text
            $errorMessage = ''
        }
        catch {
            $text = ''
            $errorMessage = $_.Exception.Message
        }
        finally {
            if ($bitmap) { $bitmap.Dispose() }
            if ($stream) { $stream.Dispose() }
        }

        $results.Add([pscustomobject]@{
            id = [string]$talk.id
            second = [double]$frame.second
            text = $text
            error = $errorMessage
        })
    }
}

$json = ConvertTo-Json -InputObject @($results.ToArray()) -Depth 4
[System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.Encoding]::UTF8)
