# Speaker-Aware Dynamic Cropping Guide 🎙️

## Overview
The speaker-aware dynamic cropping system intelligently shows 3 speakers at a time based on who's talking, even when you have 4-5 people in the podcast. It uses your transcript data to determine the active speaker and automatically selects the best combination of speakers to display.

**NEW:** The system now supports **two scene types** for each speaker count:
- **Speakers Scene**: Main discussion (triangle/grid pattern with all speakers visible)
- **Content Scene**: Content sharing (speakers visible alongside content)
  - For 3 speakers: Single crop showing all 3 on the right side
  - For 4-5 speakers: Same 3 most active speakers, but with different crop positions/sizes to fit the content layout

## How It Works
1. **Prompts for speaker count** at the start (3, 4, or 5 people)
2. **Auto-detects scene type** for each clip (speakers vs content)
3. **For 3 speakers**:
   - Speakers scene: Shows all 3 speakers stacked
   - Content scene: Single crop (all 3 on right side)
4. **For 4-5 speakers** (both scenes):
   - Analyzes transcript to identify who's speaking
   - Shows 3 most relevant speakers (active + recently active)
   - Each scene type uses different crop positions/sizes for those 3 speakers

## Configuration

### Step 1: Configure Number of Speakers Per Episode

The pipeline will **prompt you automatically** when you run it:
```
How many people are in this episode?
  3 = Core podcast (3 people)
  4 = Core + 1 guest
  5 = Core + 2 guests

Enter number of speakers (3-5):
```

Alternatively, you can pre-configure it in [3_crop_to_vertical.py](scripts/steps/3_crop_to_vertical.py#L7):
```python
EPISODE_CONFIG = {
    'num_speakers': 5,  # Set to 3, 4, or 5 (or None to prompt)
}
```

### Step 2: Configure Crop Positions for Each Speaker Count

Each speaker count (3, 4, 5) has **TWO scene configurations**:

#### For 3 Speakers (Already Configured ✓)
```python
CROP_POSITIONS_3 = {
    'speakers': [
        # Triangle pattern - 3 speakers
        {'x': 30, 'y': 30, 'width': 1180, 'height': 685},     # Top-left
        {'x': 1342, 'y': 32, 'width': 1180, 'height': 685},   # Top-right
        {'x': 684, 'y': 715, 'width': 1180, 'height': 685}    # Bottom-center
    ],
    'content': {
        # Single crop - speakers on right side
        'x': 1728,
        'y': 0,
        'width': 810,
        'height': 1440
    }
}
```

#### For 4 Speakers (CONFIGURE THESE! 📝)
```python
CROP_POSITIONS_4 = {
    'speakers': [
        # Main discussion scene - 4 speaker positions
        {'x': 30, 'y': 30, 'width': 1180, 'height': 685},     # Position 0: Top-left
        {'x': 1342, 'y': 32, 'width': 1180, 'height': 685},   # Position 1: Top-right
        {'x': 30, 'y': 715, 'width': 1180, 'height': 685},    # Position 2: Bottom-left
        {'x': 1342, 'y': 715, 'width': 1180, 'height': 685}   # Position 3: Bottom-right
    ],
    'content': [
        # Content sharing scene - SAME 4 positions but adjusted for content layout
        # These will show 3 most active speakers in smaller/different positions
        {'x': 1600, 'y': 0, 'width': 900, 'height': 480},     # Position 0: Adjusted
        {'x': 1600, 'y': 480, 'width': 900, 'height': 480},   # Position 1: Adjusted
        {'x': 1600, 'y': 960, 'width': 900, 'height': 480},   # Position 2: Adjusted
        {'x': 1600, 'y': 960, 'width': 900, 'height': 480}    # Position 3: Adjusted
    ]
}
```

**Important:** For content scene, configure where each speaker's camera appears when content is being shared. These are usually smaller and positioned to one side.

#### For 5 Speakers (CONFIGURE THESE! 📝)
```python
CROP_POSITIONS_5 = {
    'speakers': [
        # Main discussion scene - 5 speaker positions
        {'x': 30, 'y': 30, 'width': 1180, 'height': 685},     # Position 0
        {'x': 1342, 'y': 32, 'width': 1180, 'height': 685},   # Position 1
        {'x': 684, 'y': 715, 'width': 1180, 'height': 685},   # Position 2
        {'x': 30, 'y': 715, 'width': 1180, 'height': 685},    # Position 3
        {'x': 1342, 'y': 715, 'width': 1180, 'height': 685}   # Position 4
    ],
    'content': [
        # Content sharing scene - SAME 5 positions but adjusted for content layout
        # These will show 3 most active speakers in smaller/different positions
        {'x': 1600, 'y': 0, 'width': 900, 'height': 480},     # Position 0: Adjusted
        {'x': 1600, 'y': 480, 'width': 900, 'height': 480},   # Position 1: Adjusted
        {'x': 1600, 'y': 960, 'width': 900, 'height': 480},   # Position 2: Adjusted
        {'x': 1600, 'y': 960, 'width': 900, 'height': 480},   # Position 3: Adjusted
        {'x': 1600, 'y': 960, 'width': 900, 'height': 480}    # Position 4: Adjusted
    ]
}
```

**Important:** Content scene positions are typically smaller and positioned to accommodate the content display (screen/video being shared).

### Step 3: Auto-Detection Configuration

Auto-detection works by checking a pixel color that differs between scenes:

```python
AUTO_DETECT = {
    'enabled': True,
    'pixel_position': (82, 1156),  # (x, y) coordinate to check
    
    # Colors for each scene type
    'speakers_color': (0, 0, 0),        # Pixel color in speakers scene
    'content_color': (0, 216, 217),     # Pixel color in content scene
    
    'tolerance': 100
}
```

### Step 4: Map Speakers to Camera Positions (4-5 Speakers Only)
### Step 4: Map Speakers to Camera Positions (4-5 Speakers Only)

For episodes with 4-5 speakers, you need to map speaker IDs to position indices:

```python
SPEAKER_MAPPING = {
    4: {  # For 4-person episodes
        'SPEAKER_00': 0,  # Maps to position 0 (top-left)
        'SPEAKER_01': 1,  # Maps to position 1 (top-right)
        'SPEAKER_02': 2,  # Maps to position 2 (bottom-left)
        'SPEAKER_03': 3,  # Maps to position 3 (bottom-right)
    },
    5: {  # For 5-person episodes
        'SPEAKER_00': 0,
        'SPEAKER_01': 1,
        'SPEAKER_02': 2,
        'SPEAKER_03': 3,
        'SPEAKER_04': 4,
    }
}
```

**How to find Speaker IDs:**
1. Open your transcript: `output/transcripts/[video]_transcript.json`
2. Look for `"speaker"` field values like `SPEAKER_00`, `SPEAKER_01`, etc.
3. Map them to positions based on where each person sits in your camera setup

### Step 5: Enable/Disable Dynamic Cropping

```python
DYNAMIC_CONFIG = {
    'enabled': True,  # Set to False to always show all speakers (no rotation)
    'speakers_shown': 3,  # How many to show at once (recommended: 3)
    'transition_duration': 0.5,  # For future enhancements
    'min_segment_duration': 2.0,  # Minimum seconds before switching
}
```

## Usage

### Running the Pipeline
```bash
python run_pipeline.py
```

You'll be prompted:
```
How many people are in this episode?
  3 = Core podcast (3 people)
  4 = Core + 1 guest  
  5 = Core + 2 guests

Enter number of speakers (3-5): 5
```

Then for each clip, it will:
1. **Auto-detect scene type** (speakers vs content)
2. **Apply appropriate crops** based on count + scene
3. **For 4-5 speakers in speakers scene**: Use intelligent speaker selection

### Scene Detection

The system automatically detects:
- **Content Scene** → Single crop showing speakers + screen
- **Speakers Scene** → Stacked crops showing speakers (3 most relevant if 4-5 people)

If auto-detection fails, you'll be prompted manually:
```
Scene type:
  1 = Content sharing scene
  2 = Speakers scene (main discussion)
  Q = Skip this video

Your choice (1/2/Q):
```

## Current Implementation

### Version 2.0 (Current) ✨
- ✅ **Two scenes per speaker count** (speakers + content)
- ✅ **Auto-detection** works for all configurations
- ✅ **Prompts for speaker count** at pipeline start
- ✅ **3 speakers**: Shows all in speakers scene
- ✅ **4-5 speakers**: Shows 3 most relevant based on transcript
- ✅ **Intelligent speaker selection** with conversation flow analysis
- ✅ **Fallback handling** when transcript unavailable

### How It Decides What to Show

**3 Speakers:**
- Content scene → Single crop (all 3 speakers on right side)
- Speakers scene → All 3 speakers stacked vertically

**4-5 Speakers:**
- Content scene → 3 most active speakers stacked (using content scene crop positions)
- Speakers scene → 3 most active speakers stacked (using speakers scene crop positions)
- Both scenes analyze the same transcript and show the same 3 people
- Only difference: crop positions/sizes are adjusted per scene type

### Future Enhancements
- 🔄 Real-time speaker switching with crossfade transitions
- 🎬 Multiple speaker combinations per clip with temporal timeline
- 📊 Visual overlay indicating who's speaking

## Configuration Workflow

### Quick Setup for a New Episode

1. **Before running the pipeline**, check your video to see camera positions for 4 or 5 people
2. **Use `find_crop_positions.py`** to get exact coordinates
3. **Update crop positions** in [3_crop_to_vertical.py](scripts/steps/3_crop_to_vertical.py):
   - Update `CROP_POSITIONS_4` or `CROP_POSITIONS_5`
   - Both `speakers` and `content` scenes
4. **Check transcript** after step 1 to identify speaker IDs
5. **Update `SPEAKER_MAPPING`** to map IDs to positions
6. **Run pipeline** and enter speaker count when prompted

## Example Configurations

### Example 1: 3-Person Core Podcast ✓
Already configured! Just select "3" when prompted.

### Example 2: 4-Person Episode (3 core + 1 guest)
```python
# Configure both scenes with positions for all 4 speakers
CROP_POSITIONS_4 = {
    'speakers': [
        # Main discussion - full-size crops
        {'x': 100, 'y': 50, 'width': 1100, 'height': 650},   # Core member 1
        {'x': 1300, 'y': 50, 'width': 1100, 'height': 650},  # Core member 2
        {'x': 100, 'y': 750, 'width': 1100, 'height': 650},  # Core member 3
        {'x': 1300, 'y': 750, 'width': 1100, 'height': 650}  # Guest
    ],
    'content': [
        # Content sharing - smaller crops positioned to fit with content
        {'x': 1700, 'y': 100, 'width': 800, 'height': 450},  # Core member 1 - smaller
        {'x': 1700, 'y': 550, 'width': 800, 'height': 450},  # Core member 2 - smaller
        {'x': 1700, 'y': 1000, 'width': 800, 'height': 450}, # Core member 3 - smaller
        {'x': 1700, 'y': 1000, 'width': 800, 'height': 450}  # Guest - smaller
    ]
}

SPEAKER_MAPPING = {
    4: {
        'SPEAKER_00': 0,  # Core member 1 (top-left)
        'SPEAKER_01': 1,  # Core member 2 (top-right)
        'SPEAKER_02': 2,  # Core member 3 (bottom-left)
        'SPEAKER_03': 3,  # Guest (bottom-right)
    }
}
```

Both scenes will show the same 3 most active speakers, but using different crop regions!

## Tips & Best Practices

1. **Configure once per speaker count** - You only need to set up positions for each number once
2. **Test with one clip first** before processing all clips
3. **Check auto-detection** - Verify pixel detection works for your setup
4. **Update speaker mapping** for each new episode (IDs may change)
5. **Content scene coordinates** - Make sure speakers are still visible in frame
6. **Keep 3 speakers shown** for best clarity and engagement

## Troubleshooting

**Problem: Auto-detection not working**
- Check `AUTO_DETECT` pixel position and colors
- Use `find_crop_positions.py` to find a better reference pixel
- Try increasing `tolerance` value
- Verify the pixel colors are different between scenes

**Problem: Wrong speakers showing in 4-5 person episodes**
- Check `SPEAKER_MAPPING` for the correct speaker count
- Verify speaker IDs in your transcript file match the mapping
- Ensure positions are correctly configured

**Problem: People in wrong crop areas**
- Update `CROP_POSITIONS_X` coordinates for the correct speaker count
- Use `find_crop_positions.py` to identify correct areas
- Remember positions are indexed 0, 1, 2, 3, 4

**Problem: Content scene crops wrong area**
- For 3 speakers: Adjust the single `'content'` dict coordinates
- For 4-5 speakers: Adjust ALL positions in the `'content'` list
- Remember: each speaker position needs its own crop coordinates in content scene
- Content positions are usually smaller/different to accommodate the content display

**Problem: Transcript not found for speaker analysis**
- Ensure transcripts exist in `output/transcripts/`
- Transcript filename should match video name pattern
- System will fall back to showing first 3 speakers if no transcript

**Problem: Prompted for scene type every time**
- Enable auto-detection: `AUTO_DETECT['enabled'] = True`
- Configure correct reference pixel and colors
- Verify pixel colors are distinct between scenes

## Advanced: Configuring Auto-Detection

To set up auto-detection for your 4 or 5 person scenes:

1. **Open your video** in a video player
2. **Find a pixel** that has a different color between speakers and content scenes
3. **Use `find_crop_positions.py`** or an image editor to get coordinates
4. **Update AUTO_DETECT**:
```python
AUTO_DETECT = {
    'enabled': True,
    'pixel_position': (x, y),  # Your pixel coordinates
    'speakers_color': (b, g, r),  # BGR color in speakers scene
    'content_color': (b, g, r),   # BGR color in content scene
    'tolerance': 100
}
```

5. **Test** with a sample video to verify detection works

---

## Summary

The new system gives you:
- ✅ **Flexibility**: Different configurations for 3, 4, and 5 person episodes
- ✅ **Two scenes**: Content sharing + speakers for each count
- ✅ **Auto-detection**: Automatically picks the right scene
- ✅ **Smart cropping**: For 4-5 people, shows 3 most relevant speakers
- ✅ **Easy setup**: Prompt for speaker count at pipeline start

Configure once, use forever! 🎉
