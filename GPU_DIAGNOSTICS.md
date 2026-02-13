# GPU and Detection Issues - Diagnostics Report

## Summary
Fixed a critical PySceneDetect API compatibility issue. Scene detection is now working correctly.

## Issues Fixed

### 1. ✅ PySceneDetect AdaptiveDetector Parameter Issue (FIXED)
**Problem**: Code was using `AdaptiveDetector(threshold=...)` but current PySceneDetect expects `adaptive_threshold`

**Fix**: Changed parameter name in `src/unrealitytv/detectors/scene_detector.py:54`
```python
# Before
scene_manager.add_detector(AdaptiveDetector(threshold=threshold))

# After
scene_manager.add_detector(AdaptiveDetector(adaptive_threshold=threshold))
```

**Impact**: Scene detection now fully functional

## Issue Analysis

### 2. GPU Compatibility Issue (ENVIRONMENTAL - Cannot Fix in Code)
**Problem**: PyTorch CUDA version mismatch with hardware

**Details**:
- **System GPU**: NVIDIA GeForce GTX 1080 Ti
- **Compute Capability**: sm_61 (6.1)
- **Installed PyTorch**: Compiled for CUDA 12.8
- **PyTorch Requirements**: sm_70+ (Turing generation or newer)
- **Impact**: GPU cannot be used with current PyTorch installation

**Warnings Observed**:
```
NVIDIA GeForce GTX 1080 Ti with CUDA capability sm_61 is not compatible with the current PyTorch installation.
The current PyTorch install supports CUDA capabilities sm_70 sm_75 sm_80 sm_86 sm_90 sm_100 sm_120.
```

**Workaround Options**:
1. **Install older PyTorch**: Build/install PyTorch version supporting CUDA 11.x (supports sm_61)
   ```bash
   pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 --index-url https://download.pytorch.org/whl/cu116
   ```

2. **Use CPU-only mode**: Current code gracefully falls back to PySceneDetect CPU-based detection
   - Still highly effective (detected 76 scenes in 5 min of video)
   - CPU processing time: ~25 seconds for 5 minutes of video

3. **Upgrade GPU**: GTX 1080 Ti is from 2017, newer GPUs have better compute capabilities

**Current Code Behavior**:
- Auto-detection checks `torch.cuda.is_available()`
- If GPU unavailable, gracefully falls back to PySceneDetect
- CPU fallback is working correctly

### 3. TransNetV2 Not Available on PyPI
**Problem**: TransNetV2 optional dependency not available through pip

**Why**: TransNetV2 is in `pyproject.toml` but not published on PyPI

**Current Handling**: Code gracefully catches RuntimeError and falls back to PySceneDetect
- This is by design in Phase 2.2
- Provides robustness for different environments

## Test Results

### Scene Detection Test (5-minute test clip)
**File**: `test_data/90day_test_5min.mkv`
- **Size**: 204MB (reduced from 3.6GB for faster testing)
- **Duration**: ~5 minutes
- **Scenes Detected**: 76
- **Detection Time**: ~25 seconds (CPU-based PySceneDetect)
- **Method**: PySceneDetect with AdaptiveDetector (adaptive_threshold=3.0)

**Sample Scene Distribution**:
- Most scenes: 2-4 seconds
- Some longer scenes: up to 5.3 seconds
- Scene length filter: 2000ms minimum

### All Tests Passing
- `test_scene_detector.py`: 9/9 ✅
- `test_orchestrator.py`: 14/14 ✅ (excluding transnetv2-specific tests)

## Findings: "Few Segments Detected" Issue

**Root Cause**: The broken PySceneDetect parameter was causing scene detection to fail silently, appearing as if no segments were found

**Resolution**: With fix applied, detection is working properly:
- **Not a threshold issue**: Default threshold (3.0) is appropriate
- **Not a CPU issue**: CPU detection is very effective
- **Was a code bug**: Parameter name mismatch

## Recommendations

1. **Keep GPU Fallback Design**: Current graceful fallback is good for portability
2. **Document Hardware Limitations**: GTX 1080 Ti users should know GPU acceleration won't work
3. **Consider Alternative GPU Support**:
   - Document CPU-only as viable alternative
   - CPU performance is acceptable (25s for 5 min video)
4. **Use Test File**: Keep `test_data/90day_test_5min.mkv` for faster local testing

## Future Work

If GPU acceleration becomes critical:
1. Implement CPU batching optimization
2. Consider alternative GPU libraries (ONNX, TensorRT)
3. Or downgrade PyTorch to version with CUDA 11.x support
