# Riva on Windows � Docker + WSL2 (works with Uniview `/speech/*`)

Your backend expects a **running NVIDIA Riva Speech server** on gRPC at **`RIVA_SPEECH_URI`** (default **`localhost:50051`**). Riva is officially shipped as **Docker images** from NGC. On Windows, use **Docker Desktop** with the **WSL2** backend and an **NVIDIA GPU** (Riva is not practical on CPU for normal use).

References:

- [NVIDIA Riva � Local (Docker)](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/installation/deploy-local.html)
- [NVIDIA Riva � Quick Start](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/quick-start-guide.html)
- [Riva quickstart bundle (NGC)](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/riva/resources/riva_quickstart)
- [Docker Desktop GPU (WSL2)](https://docs.docker.com/desktop/features/gpu/)

---

## Part A � One-time OS / Docker installation

### A1. Windows and GPU driver

1. Install the **latest NVIDIA driver** from [NVIDIA drivers](https://www.nvidia.com/Download/index.aspx) (your laptop GPU must support **CUDA**/WSL if you follow NVIDIA�s Riva Docker path).

2. In **PowerShell (Admin)**:

   ```powershell
   wsl --update
   wsl --status
   ```

3. Confirm the GPU is visible:

   ```powershell
   nvidia-smi
   ```

   If `nvidia-smi` fails, fix drivers before Docker/Riva.

### A2. WSL2 + a Linux distro (e.g. Ubuntu)

1. Install Ubuntu (or another supported distro) from the Microsoft Store, or:

   ```powershell
   wsl --install -d Ubuntu
   ```

2. Reboot if Windows asks you to.

### A3. Docker Desktop

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/).

2. Open Docker Desktop ? **Settings** ? **General**: enable **Use the WSL 2 based engine**.

3. **Settings** ? **Resources** ? **WSL integration**: enable integration for your **Ubuntu** distro.

4. **Settings** ? ensure **GPU** / WSL GPU support is available per [Docker GPU docs](https://docs.docker.com/desktop/features/gpu/) (requires recent Docker Desktop + supported GPU + WSL2).

5. Smoke test **GPU in a container** (from PowerShell or from WSL, with Docker reachable):

   ```powershell
   docker run --rm --gpus all nvcr.io/nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
   ```

   You should see `nvidia-smi` output **inside** the container. If this fails, Riva containers will fail too � fix Docker/GPU/WSL integration first.

---

## Part B � NGC account and API key

1. Create/login at [NVIDIA NGC](https://catalog.ngc.nvidia.com/).

2. Generate an **API key** (NGC dashboard ? Setup ? Generate API Key).

3. You will use it for `docker login nvcr.io` and for **`riva_init.sh`** (`NGC_API_KEY`).

---

## Part C � Riva quick-start (inside WSL Ubuntu)

These steps mirror NVIDIA�s �Local (Docker)� guide. Paths are examples � use your real download folder.

### C1. Open WSL Ubuntu

From PowerShell:

```powershell
wsl -d Ubuntu
```

### C2. Install prerequisites inside WSL (if missing)

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl unzip
```

Ensure `docker` works **from WSL** (Docker Desktop exposes the CLI):

```bash
docker ps
```

### C3. Download the Riva quickstart from NGC

1. In a browser, open [Riva quickstart (NGC)](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/riva/resources/riva_quickstart).

2. Download the **quickstart archive** and copy it into WSL (e.g. `$HOME/riva-quickstart/`). Exact filename changes with releases.

   Example after copying to `~/riva-quickstart/`:

   ```bash
   cd ~/riva-quickstart
   ls
   ```

   You should see scripts such as **`config.sh`**, **`riva_init.sh`**, **`riva_start.sh`**, **`riva_stop.sh`**.

### C4. Configure which models/services to load

Edit **`config.sh`** in that directory (NVIDIA documents every flag inside the file). For your app you need **ASR** enabled (and **TTS** too if you use read-aloud). Keep the **gRPC** port **`50051`** unless you deliberately change Docker port mapping everywhere.

### C5. Log in to NVIDIA�s registry (once)

```bash
docker login nvcr.io
```

Use:

- Username: **`$oauthtoken`**
- Password: your **NGC API key** (pastes masked)

### C6. Initialize (downloads images + models � long first run)

```bash
cd ~/riva-quickstart
export NGC_API_KEY='paste-your-ngc-api-key-here'
bash riva_init.sh
```

Wait until NVIDIA�s message indicates success, e.g. that you should run **`riva_start.sh`**.

### C7. Start Riva

```bash
bash riva_start.sh
```

### C8. Verify Riva listens on port 50051

```bash
docker logs riva-speech 2>&1 | tail -n 50
```

Look for a line like **Riva � listening on 0.0.0.0:50051** (wording can vary slightly by release).

From **Windows PowerShell** (host):

```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 50051
```

`TcpTestSucceeded : True` means your FastAPI app on Windows can open gRPC to **localhost:50051** (typical with Docker Desktop port publish).

### C9. Stop Riva (when you are done)

From the quickstart directory:

```bash
bash riva_stop.sh
```

---

## Part D � This repository (Python API + UI)

### D1. Backend Python client

In your **Backend** venv:

```powershell
cd "D:\...\Uniview-Quin-Eryl\Backend"
.\.venv\Scripts\activate
pip install -r requirements-riva-speech.txt
```

### D2. `unified.env` (Backend)

Set at least (adjust if you changed Riva�s host/port):

```env
RIVA_SPEECH_URI=localhost:50051
RIVA_SPEECH_SSL=false
RIVA_ASR_LANGUAGE=en-US
RIVA_TTS_LANGUAGE=en-US
RIVA_TTS_SAMPLE_RATE_HZ=24000
```

If your Riva deployment requires a **specific ASR model name**, set:

```env
RIVA_ASR_MODEL=your-riva-asr-model-name
RIVA_TTS_VOICE=your-riva-voice-name
```

(Model/voice strings must match what your Riva quickstart loaded � check Riva docs for your `config.sh` choices.)

Restart **uvicorn** after editing `unified.env`.

### D3. Frontend

Ensure:

- `VITE_APP_API_URL` points at your FastAPI base (e.g. `http://127.0.0.1:8000`).
- `VITE_RIVA_SPEECH` is **not** the string `false` if you want mic + Riva TTS routes.

Rebuild/restart `npm run dev` as you normally do.

### D4. Quick HTTP checks

- `GET http://127.0.0.1:8000/speech/riva/health` ? `riva_client_installed: true`
- Mic in UI ? `POST /speech/transcribe` should return `{"text":"..."}` when Riva is up.

---

## Troubleshooting (short)

| Symptom | Likely cause |
|--------|----------------|
| `Connection refused` / `UNAVAILABLE` on `127.0.0.1:50051` | Riva containers not running, or port not published to Windows |
| `docker run --gpus all ... nvidia-smi` fails | Docker Desktop GPU/WSL not configured or driver issue |
| `riva_init.sh` auth errors | Wrong `NGC_API_KEY` or `docker login nvcr.io` |
| ASR returns errors about model | Set `RIVA_ASR_MODEL` / language to match loaded models in `config.sh` |
| Port works in WSL but not from Windows | Docker port mapping / firewall; confirm `Test-NetConnection` from Windows |

---

## If Docker Desktop + GPU on your laptop is painful

Run Riva on a **Linux GPU server** or cloud VM (same quickstart, native Linux Docker), then set:

```env
RIVA_SPEECH_URI=192.168.x.x:50051
```

and ensure the host/firewall allows your dev machine to reach that port (only on trusted networks).
