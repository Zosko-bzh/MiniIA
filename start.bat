@echo off
title MiniIA Local

setlocal
cd /d "%~dp0"

echo.
echo ==============================
echo        MiniIA Local
echo ==============================
echo.

REM Cherche une version Python deja installee, en priorite les plus recentes.
where py >nul 2>nul
if errorlevel 1 (
    echo ERREUR : Python n'est pas accessible depuis le PATH Windows.
    echo Installe Python 3.13 ou plus recent puis relance ce fichier.
    pause
    exit /b 1
)

set "PYTHON_CMD="
for %%V in (3.14 3.13 3.12 3.11) do (
    py -%%V --version >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -%%V"
        goto python_found
    )
)

:python_found
if not defined PYTHON_CMD (
    echo ERREUR : aucune version Python compatible n'a ete trouvee.
    echo Installe Python 3.11 ou plus recent puis relance ce fichier.
    pause
    exit /b 1
)

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV_PYTHON%" (
    echo Creation de l'environnement virtuel avec %PYTHON_CMD%...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo ERREUR : impossible de creer l'environnement virtuel.
        echo Verifie que la version Python installee est bien compatible.
        pause
        exit /b 1
    )
)

echo Installation des dependances du projet...
"%VENV_PYTHON%" -m pip install --upgrade pip
"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERREUR : l'installation des dependances a echoue.
    echo Verifie ta connexion internet et que Python est bien installe.
    pause
    exit /b 1
)

if not exist "%~dp0models" mkdir "%~dp0models"

if not exist "%~dp0models\model.gguf" (
    for %%F in ("%~dp0models\*.gguf") do (
        if not "%%~nxF"=="model.gguf" (
            copy /Y "%%~fF" "%~dp0models\model.gguf" >nul
            echo Copie du modele GGUF trouve en models\model.gguf
        )
    )
)

if not exist "%~dp0models\model.gguf" (
    echo.
    echo ATTENTION : aucun modele GGUF n'a ete trouve dans models\model.gguf
    echo Telecharge un petit modele conversationnel GGUF (3B a 4B, quantifie Q4)
    echo puis renomme-le en : model.gguf
    echo.
    echo Le serveur peut demarrer, mais les conversations echoueront tant que le modele n'est pas ajoute.
    echo.
)

echo Python detecte :
"%VENV_PYTHON%" --version
echo.

echo Demarrage de MiniIA...
echo.
"%VENV_PYTHON%" app.py

exit /b %errorlevel%