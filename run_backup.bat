@echo off
echo --- Starting Database Backup ---

:: Форматируем дату для имени файла (ГГГГ-ММ-ДД)
:: (Это зависит от региональных настроек, но обычно работает)
set YYYY=%date:~6,4%
set MM=%date:~3,2%
set DD=%date:~0,2%
set TODAY=%YYYY%-%MM%-%DD%

:: --- НАСТРОЙКИ ---
:: 1. Укажи, где лежит твоя "живая" база данных
set SOURCE_FILE="C:\Users\HIkkvl\Documents\GitHub\LoVHub\central_club.db"

:: 2. Укажи, куда сохранять бэкапы (папка из Шага 1)
set BACKUP_FOLDER="C:\MyLauncherBackups"

:: 3. Имя файла для бэкапа
set BACKUP_FILE="central_club_backup_%TODAY%.db"
:: --- КОНЕЦ НАСТРОЕК ---

echo Backing up %SOURCE_FILE% to %BACKUP_FOLDER%\%BACKUP_FILE%

:: Копируем файл
copy %SOURCE_FILE% %BACKUP_FOLDER%\%BACKUP_FILE%

echo --- Backup Complete ---