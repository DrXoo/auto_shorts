import torch

print("=== GPU Information ===")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU device: {torch.cuda.get_device_name(0)}")
    print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    print(f"Number of GPUs: {torch.cuda.device_count()}")
    
    # Check current memory usage
    print(f"\nCurrent GPU memory allocated: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
    print(f"Current GPU memory reserved: {torch.cuda.memory_reserved(0) / 1024**3:.2f} GB")
else:
    print("WARNING: CUDA is not available. The script will run on CPU (very slow).")
    print("\nPlease install PyTorch with CUDA support:")
    print("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
