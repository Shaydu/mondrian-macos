# Mondrian Quick Start Guide

## MLX Backend Setup (Python 3.12 Required)

The Mondrian services use Apple's MLX framework for efficient on-device AI inference. MLX requires Python 3.12+.

## Easy Launch Methods

### Method 1: Use the Launcher Script (Recommended)
```bash
# From anywhere in the project
./mondrian.sh

# Examples:
./mondrian.sh                    # Start services
./mondrian.sh stop               # Stop services
./mondrian.sh restart            # Restart services
./mondrian.sh status             # Check status
./mondrian.sh --no-verbose       # Start without monitoring
```

### Method 2: Add to Your Shell Profile
Add this alias to your `~/.zshrc` or `~/.bashrc`:
```bash
alias mondrian='/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 /Users/shaydu/dev/mondrian-macos/scripts/start_services.py'
```

Then reload:
```bash
source ~/.zshrc
```

Now you can run from anywhere:
```bash
mondrian                    # Start services
mondrian stop               # Stop services
mondrian restart            # Restart services
mondrian status             # Check status
```

### Method 3: Direct Python 3.12 Call
```bash
cd /Users/shaydu/dev/mondrian-macos
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 scripts/start_services.py
```

## Testing the Setup

Once services are running, test with:
```bash
# Wait 60 seconds for model to load on first run, then:
curl -X POST http://localhost:5100/analyze \
  -F "image=@mondrian/source/mike-shrub.jpg" \
  -F "advisor=mondrian" \
  -F "job_id=test_123"
```

## Service Endpoints

- **Job Service**: http://127.0.0.1:5005
- **AI Advisor**: http://127.0.0.1:5100
- **Backend**: MLX (Apple Silicon)
- **Model**: Qwen3-VL-4B-Instruct-MLX-4bit

## iOS Development

The services automatically detect and use link-local IP addresses (169.254.x.x) for iOS tethering, perfect for development without WiFi.

## Troubleshooting

### "Python 3.12+ required" Error
Install Python 3.12 from python.org, or use the launcher scripts above which automatically use the correct Python version.

### MLX Not Loading
Ensure you're using Python 3.12:
```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 --version
# Should show: Python 3.12.x
```

### Model Not Found
The model downloads automatically from Hugging Face on first use. This takes 30-60 seconds.
