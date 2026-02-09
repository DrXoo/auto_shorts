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

## ✨ Key Features

- **🎙️ Speaker-Aware Dynamic Cropping** - Intelligently shows 3 speakers at a time in episodes with 4-5 people, based on who's talking
- **🎯 Speaker Diarization** - Automatically identifies different speakers in your podcast
- **🤖 AI-Powered Clip Selection** - Provide clips.json for intelligent moment extraction
- **📱 Vertical Format Optimization** - Perfect 9:16 for Instagram Reels, TikTok, and YouTube Shorts
- **📝 Karaoke-Style Subtitles** - Word-by-word highlighting for maximum engagement
- **🔄 Multi-Scene Support** - Auto-detection or manual selection for different camera layouts
- **🎮 Trending Topics Integration** - Fetch gaming trends from Reddit, Steam, and YouTube
- **⚡ GPU-Accelerated** - Fast transcription with CUDA support

### 🆕 Speaker-Aware Mode (4-5 Speakers)
For episodes with 4-5 people, the system analyzes the transcript and dynamically shows the 3 most relevant speakers at any given moment (active speaker + recently active ones). This works for BOTH scene types:
- **Speakers scene**: 3 most active in full discussion layout
- **Content scene**: Same 3 most active but with different crop positions/sizes to fit the content

See [SPEAKER_CONFIG_GUIDE.md](SPEAKER_CONFIG_GUIDE.md) for setup instructions.

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
├── scripts/
│   ├── steps/                    # Pipeline steps (run by orchestrator)
│   │   ├── 1_transcribe.py
│   │   ├── 2_extract_clips.py
│   │   ├── 3_crop_to_vertical.py
│   │   └── 4_add_subtitles.py
│   └── utils/                    # Utility scripts
│       ├── aggregate_trending_topics.py
│       ├── check_gpu.py
│       ├── clean_output.py
│       ├── find_crop_positions.py
│       └── fetch_*_trends.py
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
python scripts/steps/1_transcribe.py

# Step 3: Extract clips
python scripts/steps/2_extract_clips.py

# Step 4: Crop to vertical
python scripts/steps/3_crop_to_vertical.py

# Step 5: Add subtitles
python scripts/steps/4_add_subtitles.py
```

## Utility Scripts

Helper scripts for various tasks:

```bash
# Check GPU availability for transcription
python scripts/utils/check_gpu.py

# Find optimal crop positions for your video layout
python scripts/utils/find_crop_positions.py

# Aggregate trending topics from all sources (Recommended!)
python scripts/utils/aggregate_trending_topics.py

# Fetch trending topics from individual sources
python scripts/utils/fetch_reddit_trends.py
python scripts/utils/fetch_steam_trends.py
python scripts/utils/fetch_youtube_trends.py

# Clean all output files (keeps folder structure)
python scripts/utils/clean_output.py
```

### Getting Trending Topics for AI Analysis

The `aggregate_trending_topics.py` script fetches gaming trends from:
- **Reddit** (r/gaming, r/Games, r/pcgaming, etc.)
- **Steam** (top sellers, new releases, most played)
- **YouTube** (trending gaming videos in Spanish market)

It combines and scores all results, giving you the **most relevant trending games** to help your AI identify viral-worthy clips. Run it before starting the pipeline to get the latest trends!

The output (`output/trending_topics.json`) includes:
- Top 50 trending games with scores
- Multi-source validation (games mentioned across platforms)
- Sample posts/videos mentioning each game
- Categorization (top seller, new release, etc.)

## Requirements

- Python 3.8+
- FFmpeg
- CUDA-capable GPU (for transcription)
- See individual scripts for Python package requirements

## Customization

### Subtitle Styling
Edit `scripts/steps/4_add_subtitles.py` to customize:
- Font family and size
- Colors (text, karaoke effect, outline)
- Position on screen
- Timing and grouping

### Crop Positions
Edit `scripts/steps/3_crop_to_vertical.py` to adjust:
- Single crop position (content sharing mode)
- Triple crop positions (speaker triangle mode)
- **Multi-speaker dynamic mode (4-5 people)** - See [SPEAKER_CONFIG_GUIDE.md](SPEAKER_CONFIG_GUIDE.md)
  - Configure number of speakers per episode
  - Map speaker IDs to camera positions
  - Adjust crop coordinates for your setup
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
