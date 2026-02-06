# AutoShorts Pipeline 🎬

Automated pipeline to convert podcast videos into vertical shorts ready for Instagram, TikTok, and YouTube Shorts.

## Pipeline Overview

```
Video Input
    ↓
[1] Transcribe with Speaker Diarization
    ↓
[2] AI Analysis (External) → clips.json
    ↓
[3] Extract Clips
    ↓
[4] Crop to Vertical (9:16)
    ↓
[5] Add Karaoke Subtitles
    ↓
Final Shorts Ready! 🎉
```

## Quick Start

### Run Full Pipeline
```bash
python run_pipeline.py
```

The pipeline will:
1. ✅ Transcribe your video automatically
2. ⏸️ Wait for you to provide AI analysis (clips.json)
3. ✅ Extract, crop, and add subtitles automatically
4. 🎉 Output final videos to `output/final/`

### Resume from Specific Step
```bash
python run_pipeline.py --from-step 3    # Resume from clip extraction
python run_pipeline.py --from-step 4    # Resume from cropping
```

### Skip Transcription
If you already have a transcript:
```bash
python run_pipeline.py --skip-transcribe
```

### Reset Pipeline State
```bash
python run_pipeline.py --reset
```

## Folder Structure

```
autoshorts/
├── input/
│   └── example.mp4              # Your source video
├── output/
│   ├── transcripts/              # Transcription results
│   │   ├── example_transcript.json
│   │   ├── example_transcript.txt
│   │   └── nexample_transcript_detailed.txt
│   ├── ai_analysis/              # AI-selected clips
│   │   └── clips.json            # ← YOU PROVIDE THIS
│   ├── extracted/                # Raw extracted clips
│   ├── cropped/                  # Vertical format clips
│   └── final/                    # Final videos with subtitles
│       └── clip_XX_title_subtitled.mp4  # ← UPLOAD THESE!
├── scripts/                      # Individual pipeline scripts
│   ├── transcribe_with_speakers.py
│   ├── extract_clips.py
│   ├── crop_to_vertical.py
│   └── add_subtitles.py
└── run_pipeline.py              # 🚀 Main orchestrator
```

## Step 2: AI Analysis (Manual)

After transcription completes, you need to provide `output/ai_analysis/clips.json` with this format:

```json
[
  {
    "clip_number": 1,
    "title": "Amazing Discussion About AI",
    "start_time": "2:30",
    "end_time": "3:15"
  },
  {
    "clip_number": 2,
    "title": "Funny Moment",
    "start_time": "5:45",
    "end_time": "6:20"
  }
]
```

The pipeline will wait for this file and check periodically. Once detected, it continues automatically.

## Individual Scripts

You can still run individual steps manually:

```bash
# Step 1: Transcribe
python scripts/transcribe_with_speakers.py

# Step 3: Extract clips
python scripts/extract_clips.py

# Step 4: Crop to vertical
python scripts/crop_to_vertical.py

# Step 5: Add subtitles
python scripts/add_subtitles.py
```

## Requirements

- Python 3.8+
- FFmpeg
- CUDA-capable GPU (for transcription)
- See individual scripts for Python package requirements

## Customization

### Subtitle Styling
Edit `scripts/add_subtitles.py` to customize:
- Font family and size
- Colors (text, karaoke effect, outline)
- Position on screen
- Timing and grouping

### Crop Positions
Edit `scripts/crop_to_vertical.py` to adjust:
- Single crop position (content sharing mode)
- Triple crop positions (speaker triangle mode)
- Auto-detection settings

## Output

Final videos are saved to `output/final/` with:
- ✅ Vertical 9:16 aspect ratio (810x1440)
- ✅ Karaoke-style subtitles
- ✅ Optimized for mobile viewing
- ✅ Ready to upload!

## Tips

1. **Place your video** in `input/example.mp4`
2. **Run the pipeline** with `python run_pipeline.py`
3. **Prepare clips.json** while waiting (use transcript output)
4. **Pipeline resumes** automatically after you provide clips.json
5. **Check `output/final/`** for your ready-to-upload shorts!

---

Made with ❤️ for content creators
