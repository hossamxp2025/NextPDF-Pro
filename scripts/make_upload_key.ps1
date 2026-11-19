<#
.SYNOPSIS
    Creates the Google Play upload key for the Android app.

.DESCRIPTION
    Run this yourself, in your own terminal, and type the passwords when
    keytool asks. That is the point of the script: nothing here takes a
    password as an argument, so no password reaches a script file, a shell
    history, a log, or the process list that any program on the machine can
    read. Whoever runs it is the only one who ever sees it.

    What the key is: Google Play signs the published app with a key it holds
    itself. What you upload is signed with this *upload* key, which only
    proves an upload came from you. If you lose it, Play support can register
    a new one - unlike the app signing key, losing which would end the
    listing. That is a reason to be careful, not relaxed: whoever holds this
    file and its password can upload a release as you.

    Afterwards: back the file up somewhere that is not this computer, and
    fill in android/keystore.properties (see the .example beside it).

.PARAMETER KeystorePath
    Where to write the key. The default is outside the repository on purpose.

.PARAMETER Alias
    The key's name inside the keystore. Must match keyAlias in
    keystore.properties.

.PARAMETER DistinguishedName
    Who the certificate says it belongs to, as one X.500 string, for example
    "CN=Your Name, O=Your Organisation, L=Your City, C=EG". None of it is
    secret and nobody verifies it, so it is given on the command line: that
    way keytool asks only for the passwords, and a slip while answering six
    questions in a row cannot end up inside the certificate. Leave it out and
    keytool asks for the fields itself, as it did before.

    The country has to be a two-letter ISO code. X.509 defines that field as
    exactly two characters, and keytool does NOT check it - it will happily
    write a city name or a whole sentence there. This script checks instead,
    because the cheap moment to catch it is before the key exists.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\make_upload_key.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\make_upload_key.ps1 -DistinguishedName "CN=A Name, O=An Organisation, L=A City, C=EG"
#>
[CmdletBinding()]
param(
    [string]$KeystorePath = (Join-Path $HOME "keys\nextpdf-upload.jks"),
    [string]$Alias = "nextpdf-upload",
    [string]$DistinguishedName
)

$ErrorActionPreference = "Stop"

# Google's own instructions for an upload key: RSA 2048 and a long validity.
# A larger key would very probably be accepted too, but "probably" is not a
# good enough reason to differ from the documented values for a key that
# cannot be swapped out casually.
$KeyAlgorithm = "RSA"
$KeySize = 2048
$ValidityDays = 10000

function Find-Keytool {
    $onPath = Get-Command keytool -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    if ($env:JAVA_HOME) {
        $fromJavaHome = Join-Path $env:JAVA_HOME "bin\keytool.exe"
        if (Test-Path $fromJavaHome) { return $fromJavaHome }
    }
    $candidates = Get-ChildItem "C:\Program Files\Eclipse Adoptium" `
        -Filter "jdk-*" -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending
    foreach ($jdk in $candidates) {
        $candidate = Join-Path $jdk.FullName "bin\keytool.exe"
        if (Test-Path $candidate) { return $candidate }
    }
    throw "keytool was not found. Install a JDK, or set JAVA_HOME to one."
}

$keytool = Find-Keytool
Write-Host "keytool: $keytool"

# keytool accepts anything in the country field, so check it here. A
# certificate whose countryName breaks the two-character rule is malformed
# per X.509, and whether Play's backend minds is not something to find out
# after the key is registered.
$dnameArguments = @()
if ($DistinguishedName) {
    $country = [regex]::Match($DistinguishedName, '(?i)(?:^|,)\s*C\s*=\s*([^,]*)')
    if (-not $country.Success) {
        throw ("The distinguished name has no country field. Add one, as a " +
               "two-letter ISO code, for example C=EG.")
    }
    $code = $country.Groups[1].Value.Trim().Trim('"')
    if ($code -notmatch '^[A-Za-z]{2}$') {
        throw ("The country in the distinguished name is '$code'. It has to " +
               "be a two-letter ISO code, such as EG, SA or US - X.509 " +
               "allows exactly two characters there, and keytool will not " +
               "stop you putting something else in.")
    }
    $dnameArguments = @("-dname", $DistinguishedName)
}

# Never overwrite. A keystore that is already registered with Play and gets
# replaced by a fresh one is the one mistake here that cannot be undone from
# this machine.
if (Test-Path $KeystorePath) {
    throw ("A keystore already exists at $KeystorePath. Refusing to touch " +
           "it. If you really want a new key, move the old one aside " +
           "yourself first - and remember Play has to be told about a new " +
           "upload key before it will accept an upload signed with it.")
}

$folder = Split-Path -Parent $KeystorePath
if ($folder -and -not (Test-Path $folder)) {
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
}

Write-Host ""
Write-Host "keytool will now ask for:"
Write-Host "  - a keystore password, twice. Choose a long one and keep it in"
Write-Host "    your password manager. Nobody can recover it for you."
Write-Host "    It must be ASCII - plain letters, digits and punctuation."
Write-Host "    keytool refuses anything else with 'Password is not ASCII',"
Write-Host "    so Arabic or any other script will not work here. A long"
Write-Host "    passphrase in Latin letters is stronger anyway."
if (-not $DistinguishedName) {
    Write-Host "  - your name and organisation. These end up inside the"
    Write-Host "    certificate; they are not secret and not checked by"
    Write-Host "    anyone. The country must be a two-letter code (EG, SA,"
    Write-Host "    US); keytool does not check, so getting it wrong there"
    Write-Host "    goes unnoticed. Answer 'no' at the confirmation line to"
    Write-Host "    be asked all of them again."
}
Write-Host "  - a key password. Pressing Enter reuses the keystore password,"
Write-Host "    which is what keystore.properties expects unless you set"
Write-Host "    keyPassword to something else."
Write-Host ""

& $keytool -genkeypair `
    -keystore $KeystorePath `
    -alias $Alias `
    -keyalg $KeyAlgorithm `
    -keysize $KeySize `
    -validity $ValidityDays `
    @dnameArguments

if ($LASTEXITCODE -ne 0) {
    throw "keytool failed with exit code $LASTEXITCODE. No key was created."
}

Write-Host ""
Write-Host "Created: $KeystorePath"
Write-Host "Alias:   $Alias"
Write-Host ""
Write-Host "Its fingerprint (keytool will ask for the keystore password again):"
& $keytool -list -v -keystore $KeystorePath -alias $Alias

Write-Host ""
Write-Host "Next, and none of it is optional:"
Write-Host "  1. Back this file up somewhere that is not this computer."
Write-Host "  2. Put the keystore password and the key password in your"
Write-Host "     password manager."
Write-Host "  3. Copy android\keystore.properties.example to"
Write-Host "     android\keystore.properties and fill it in. That file is"
Write-Host "     excluded from git; keep it that way."
Write-Host "  4. Build the bundle:  cd android;  .\gradlew bundleRelease"
Write-Host ""
Write-Host "This key is not the app signing key. Play holds that one and uses"
Write-Host "it to sign what users install; this key only authorises uploads."
