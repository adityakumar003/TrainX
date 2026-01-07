# GymLife Pose Detection Setup Guide

## Problem
The application was encountering a `protobuf` version compatibility issue with `mediapipe` and `tensorflow`:
```
ImportError: cannot import name 'runtime_version' from 'google.protobuf'
```

## Solution: Virtual Environment Setup

### Step 1: Activate the Virtual Environment

The virtual environment `gymlife_env` has been created. Activate it using:

```powershell
.\gymlife_env\Scripts\Activate.ps1
```

> **Note**: If you get an execution policy error, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Step 2: Install Dependencies

Once the environment is activated (you'll see `(gymlife_env)` in your prompt), install all dependencies:

```powershell
pip install -r requirements.txt
```

### Step 3: Run the Application

```powershell
python app1.py
```

### Step 4: Deactivate (when done)

```powershell
deactivate
```

---

## What Was Fixed

- **Changed**: `protobuf==4.25.8` → `protobuf==3.20.3`
- **Reason**: `mediapipe 0.10.14` requires `protobuf 3.x` for compatibility with TensorFlow

---

## Alternative: Using Conda (if you have it installed)

If you prefer conda and have Anaconda/Miniconda installed:

```bash
# Create environment
conda create -n gymlife python=3.10 -y

# Activate
conda activate gymlife

# Install dependencies
pip install -r requirements.txt

# Run
python app1.py

# Deactivate
conda deactivate
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `.\gymlife_env\Scripts\Activate.ps1` | Activate virtual environment |
| `pip install -r requirements.txt` | Install all dependencies |
| `python app1.py` | Run the pose detection app |
| `deactivate` | Exit virtual environment |

---

## Troubleshooting

### Issue: "Execution policy" error when activating
**Solution**: Run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: Still getting protobuf errors
**Solution**: Ensure you're in the virtual environment and reinstall:
```powershell
pip uninstall protobuf -y
pip install protobuf==3.20.3
```

### Issue: Camera not opening
**Solution**: Make sure no other application is using your webcam
