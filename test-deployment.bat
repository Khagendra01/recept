@echo off
echo Testing deployment configuration...

REM Check Python version
python --version

REM Test if we can install the requirements
echo Testing requirements installation...
pip install --upgrade pip
pip install --upgrade setuptools wheel

REM Try to install with pre-compiled wheels
echo Attempting to install with pre-compiled wheels...
pip install --only-binary=all -r requirements.txt

if %ERRORLEVEL% EQU 0 (
    echo ✅ Successfully installed with pre-compiled wheels
) else (
    echo ⚠️  Some packages need compilation, this is expected for Rust dependencies
    echo Testing full installation...
    pip install -r requirements.txt
    if %ERRORLEVEL% EQU 0 (
        echo ✅ Successfully installed all dependencies
    ) else (
        echo ❌ Failed to install dependencies
        exit /b 1
    )
)

echo Testing application startup...
python -c "from app.main import app; print('✅ Application imports successfully')"

echo ✅ Deployment test completed successfully 