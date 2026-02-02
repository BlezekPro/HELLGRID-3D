@echo off
title HELLGRID - Instalator zaleznosci
color 0C

echo ==========================================================
echo           HELLGRID: ARENA - INSTALATOR DODATKOW
echo ==========================================================
echo.

:: Sprawdzanie czy Python jest zainstalowany
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [BLAD] Nie znaleziono Pythona! 
    echo Pobierz go z: https://www.python.org/downloads/
    echo Pamietaj, aby zaznaczyc "Add Python to PATH" podczas instalacji.
    pause
    exit
)

echo [1/3] Aktualizacja menedzera pakietow pip...
python -m pip install --upgrade pip

echo.
echo [2/3] Instalacja silnika Ursina...
python -m pip install ursina

echo.
echo [3/3] Instalacja biblioteki Pillow (obrazki)...
python -m pip install Pillow

echo.
echo ==========================================================
echo   WSZYSTKO GOTOWE! Mozesz teraz uruchomic main.py
echo ==========================================================
pause