@echo off
REM ============================================================
REM  Option-Analitik - единый скрипт запуска
REM  Запускает FastAPI-бэкенд (порт 8000) и React-фронтенд (5173)
REM  в отдельных окнах CMD и открывает браузер.
REM ============================================================

setlocal EnableDelayedExpansion
chcp 65001 >nul
title Option-Analitik launcher

REM --- Корень проекта = папка, где лежит этот bat ---
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "PIPELINE=%ROOT%\Hibrid Condor\options_alpha"

echo.
echo  ============================================================
echo   Option-Analitik
echo  ============================================================
echo   Корень:    %ROOT%
echo   Backend:   %BACKEND%
echo   Frontend:  %FRONTEND%
echo   Pipeline:  %PIPELINE%
echo  ============================================================
echo.

REM --- Проверка структуры ---
if not exist "%BACKEND%\app\main.py" (
    echo [ОШИБКА] Не найден backend\app\main.py
    echo Убедитесь, что start.bat лежит в корне репозитория Option-Analitik.
    pause
    exit /b 1
)
if not exist "%FRONTEND%\package.json" (
    echo [ОШИБКА] Не найден frontend\package.json
    pause
    exit /b 1
)

REM --- Проверка Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Python не найден в PATH.
    echo Установите Python 3.10+ с https://www.python.org/downloads/
    pause
    exit /b 1
)

REM --- Проверка Node.js ---
where node >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Node.js не найден в PATH.
    echo Установите Node.js 18+ с https://nodejs.org/
    pause
    exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] npm не найден в PATH.
    pause
    exit /b 1
)

REM --- Меню действий ---
echo Выберите действие:
echo   [1] Запустить UI (бэкенд + фронтенд + браузер)  ^<-- по умолчанию
echo   [2] Запустить только пайплайн (main_pipeline.py)
echo   [3] Установить/обновить все зависимости
echo   [4] Запустить всё: установка + пайплайн + UI
echo   [Q] Выход
echo.
set "CHOICE="
set /p CHOICE="Ваш выбор [1]: "
if "%CHOICE%"=="" set "CHOICE=1"

if /i "%CHOICE%"=="Q" exit /b 0
if "%CHOICE%"=="1" goto RUN_UI
if "%CHOICE%"=="2" goto RUN_PIPELINE
if "%CHOICE%"=="3" goto INSTALL_DEPS
if "%CHOICE%"=="4" goto RUN_ALL

echo Неизвестный выбор.
pause
exit /b 1

REM ============================================================
:INSTALL_DEPS
echo.
echo [1/3] Установка Python-зависимостей пайплайна...
pushd "%PIPELINE%"
python -m pip install --user --upgrade-strategy only-if-needed -r requirements.txt
popd

echo.
echo [2/3] Установка Python-зависимостей бэкенда...
pushd "%BACKEND%"
python -m pip install --user --upgrade-strategy only-if-needed -r requirements.txt
popd

echo.
echo [3/3] Установка npm-пакетов фронтенда...
pushd "%FRONTEND%"
call npm install
popd

echo.
echo Зависимости установлены.
if "%RUN_AFTER_INSTALL%"=="1" goto AFTER_INSTALL
pause
exit /b 0

:AFTER_INSTALL
set "RUN_AFTER_INSTALL="
goto RUN_PIPELINE_THEN_UI

REM ============================================================
:RUN_PIPELINE
echo.
echo Запуск пайплайна (main_pipeline.py)...
pushd "%PIPELINE%"
python main_pipeline.py
set "RC=%ERRORLEVEL%"
popd
echo.
if "%RC%"=="0" (
    echo Пайплайн успешно завершён. Отчёты: "%PIPELINE%\reports\"
) else (
    echo Пайплайн завершился с кодом %RC%.
)
pause
exit /b %RC%

REM ============================================================
:RUN_ALL
set "RUN_AFTER_INSTALL=1"
goto INSTALL_DEPS

:RUN_PIPELINE_THEN_UI
echo.
echo Запуск пайплайна перед UI...
pushd "%PIPELINE%"
python main_pipeline.py
popd
echo.
goto RUN_UI

REM ============================================================
:RUN_UI
echo.
echo Запускаю бэкенд в новом окне (порт 8000)...
start "Option-Analitik :: Backend (FastAPI)" cmd /k "cd /d "%BACKEND%" && python -m uvicorn app.main:app --reload --port 8000"

echo Жду готовности бэкенда...
call :WAIT_PORT 8000 30
if errorlevel 1 (
    echo [ВНИМАНИЕ] Бэкенд не отвечает на :8000 за 30 сек, но UI всё равно запущу.
)

echo.
echo Запускаю фронтенд в новом окне (порт 5173)...
start "Option-Analitik :: Frontend (Vite)" cmd /k "cd /d "%FRONTEND%" && npm run dev"

echo Жду готовности фронтенда...
call :WAIT_PORT 5173 60
if errorlevel 1 (
    echo [ВНИМАНИЕ] Фронтенд не отвечает на :5173 за 60 сек.
    echo Если это первый запуск, npm может ещё ставить пакеты в окне фронтенда.
)

echo.
echo Открываю браузер: http://localhost:5173
start "" "http://localhost:5173"

echo.
echo  ============================================================
echo   UI запущен.
echo   Бэкенд:    http://localhost:8000   (Swagger: /docs)
echo   Фронтенд:  http://localhost:5173
echo.
echo   Чтобы остановить - закройте окна "Backend" и "Frontend".
echo  ============================================================
pause
exit /b 0

REM ============================================================
REM  Утилита: ждёт, пока порт не начнёт слушаться
REM  %1 = порт, %2 = таймаут в секундах
REM ============================================================
:WAIT_PORT
set "PORT=%~1"
set "TIMEOUT=%~2"
set /a COUNT=0
:WAIT_LOOP
netstat -an | find ":%PORT% " | find "LISTENING" >nul
if not errorlevel 1 exit /b 0
set /a COUNT+=1
if %COUNT% GEQ %TIMEOUT% exit /b 1
timeout /t 1 /nobreak >nul
goto WAIT_LOOP
