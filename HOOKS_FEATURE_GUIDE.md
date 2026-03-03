# Hooks Compilation Feature Guide

## 🎬 What is it?

Create compelling intro/teaser videos using the most engaging moments from your podcast - the kind of hooks that make viewers stop scrolling and want to watch the full episode!

Think of it like a movie trailer: controversial statements, cliffhangers, passionate reactions, debates, and bold predictions all compiled into a punchy 60-120 second video.

## 🚀 Quick Start

### Step 1: Transcribe Your Podcast

Make sure you have:
- ✅ Your video file in `input/`
- ✅ Transcription already done (from step 1 of your pipeline)
- ✅ Transcript available in `output/transcripts/`

If you haven't transcribed yet:
```powershell
python run_pipeline.py --step 1
```

### Step 2: Analyze for Hooks with AI

1. Open the **transcript file** (`output/transcripts/your_podcast_transcript.txt`)
2. Open the **prompt file** (`hook_extraction_prompt.txt`)
3. Send BOTH to your AI assistant (ChatGPT, Claude, etc.) together with instructions like:

```
Using the prompt in hook_extraction_prompt.txt, analyze this transcript and identify 
the best hooks for creating a compelling intro/teaser video. Output the results in 
the exact JSON format specified.
```

4. Save the AI's JSON output as: `output/ai_analysis/hooks.json`

**💡 Tip:** Check `output/ai_analysis/hooks_example.json` to see the expected format!

### Step 3: Generate the Compilation

Run the compilation script:

```powershell
# Basic compilation (no music)
python scripts/utils/create_hooks_compilation.py

# With background music
python scripts/utils/create_hooks_compilation.py --music path/to/music.mp3

# Custom music volume (0.0 to 1.0)
python scripts/utils/create_hooks_compilation.py --music music.mp3 --music-volume 0.2

# Different transition style
python scripts/utils/create_hooks_compilation.py --transition fade --duration 0.7
```

### Step 4: Review and Share!

Your compilation will be at: `output/final/hooks_compilation.mp4`

## 📋 Hook Types Explained

The AI looks for these types of engaging moments:

| Type | Description | Example |
|------|-------------|---------|
| 🔥 **Strong Opinion** | Bold takes and declarations | "This is the best/worst game ever made" |
| 😱 **Shocking Statement** | Surprising revelations | "You won't believe what they announced..." |
| 💥 **Passionate Reaction** | Emotional responses | "I can't believe they did this!" |
| 🎯 **Debate** | Disagreements and arguments | "You're completely wrong!" "No way!" |
| 🚀 **Bold Prediction** | Future claims and speculation | "In 6 months, everything will change..." |
| 🎬 **Intriguing Question** | Hook-building questions | "What if Nintendo did X?" |
| 💣 **Cliffhanger** | Suspense-building statements | "I have info I can't share but..." |

## 🎯 What Makes a Great Hook?

**✅ DO:**
- Keep each hook 5-15 seconds (sweet spot: 8-12 seconds)
- Choose high-energy, passionate moments
- Include variety (mix different hook types)
- Lead with your STRONGEST hook
- End with a cliffhanger or call-to-action feeling
- Use natural conversation boundaries (don't cut mid-sentence)

**❌ DON'T:**
- Include long explanations
- Use inside jokes that need context
- Pick slow-paced or monotone segments
- Give away too much (maintain mystery!)
- Cluster similar hooks together
- Include moments with unclear audio

## 🎨 Background Music Tips

Choose music that:
- **Builds energy** throughout the compilation
- **Matches the mood** (electronic/synthwave for tech, epic for dramatic, etc.)
- **Doesn't overpower** dialogue (keep volume around 0.2-0.4)
- **Has dynamic sections** that align with your hook pacing

Recommended sources:
- Epidemic Sound
- Artlist
- Free Music Archive (Creative Commons)
- YouTube Audio Library

## 🎬 Compilation Strategy

**Structure your hooks like a movie trailer:**

1. **Opening (0-20s)** - First 2-3 hooks
   - Lead with ABSOLUTE STRONGEST moment
   - Controversial or shocking to grab attention
   - Set the tone immediately

2. **Middle (20-80s)** - Next 4-6 hooks
   - Mix different types for variety
   - Maintain high energy
   - Build narrative tension
   - Alternate speakers for dynamic feel

3. **Closing (80-120s)** - Last 2-3 hooks
   - Peak moments or cliffhanger
   - End with "you need to watch this" feeling
   - Leave them wanting more

## 📁 File Structure

```
autoshorts/
├── hook_extraction_prompt.txt          # AI prompt for identifying hooks
├── input/
│   └── your_podcast.mp4               # Source video
├── output/
│   ├── transcripts/
│   │   └── your_podcast_transcript.txt # From step 1
│   ├── ai_analysis/
│   │   ├── hooks.json                 # AI output (you create this)
│   │   └── hooks_example.json         # Example format
│   ├── hooks_temp/                    # Temporary extracted hooks
│   │   ├── hook_01.mp4
│   │   ├── hook_02.mp4
│   │   └── ...
│   └── final/
│       └── hooks_compilation.mp4      # 🎉 Final output!
└── scripts/
    └── utils/
        └── create_hooks_compilation.py # Compilation script
```

## 🛠️ Advanced Options

### Custom Transitions

Available transition types:
```powershell
--transition fade        # Smooth fade (default)
--transition wipeleft    # Wipe from left
--transition wiperight   # Wipe from right  
--transition slideup     # Slide up
--transition slidedown   # Slide down
--transition dissolve    # Cross dissolve
--transition pixelize    # Pixelation effect
```

### Transition Duration
```powershell
--duration 0.3  # Quick transitions
--duration 0.5  # Default
--duration 1.0  # Slower, more cinematic
```

## 🎓 Pro Tips

1. **Quality over Quantity**: 6 amazing hooks > 12 mediocre ones
2. **Test Multiple Versions**: Try different hook selections and orders
3. **Watch the Energy**: Ensure variety in energy levels to avoid monotony
4. **Mind the Context**: Each hook should make sense standalone
5. **Use the Metadata**: The AI provides music recommendations - use them!
6. **Iterate**: If a hook doesn't work, replace it and recompile
7. **Think Mobile**: Most viewers will watch on phones - ensure audio is clear

## 🔧 Troubleshooting

**"No hooks found in hooks.json"**
- Ensure your JSON file matches the example format
- Check that the file is in `output/ai_analysis/hooks.json`

**"Failed to extract hook"**
- Verify timestamps are in seconds (not mm:ss format)
- Check that timestamps exist in your source video
- Ensure source video is in `input/` directory

**"Music file not found"**
- Use absolute path to music file
- Or place music in project directory and use relative path

**Transitions look choppy**
- Increase `--duration` for smoother transitions
- Try different `--transition` types
- Check that your source video quality is good

## 🚀 Integration with Main Pipeline

This feature works **independently** from the main shorts pipeline:

- **Main Pipeline**: Creates individual 30-90s viral clips
- **Hooks Feature**: Creates one compilation teaser from the best moments

You can run both! The hooks compilation can serve as:
- A teaser for the full episode
- An intro to your YouTube video
- Social media promotion
- A "best of" highlight reel

## 📊 Example Workflow

Real-world example:

```powershell
# 1. You have a 2-hour podcast about Nintendo rumors
# 2. Already transcribed it
python run_pipeline.py --step 1  ✓ Done

# 3. Paste transcript + prompt to Claude/GPT
# "Find the 8 most shocking Nintendo moments from this podcast"

# 4. Save AI output as hooks.json

# 5. Generate compilation
python scripts/utils/create_hooks_compilation.py --music nintendo_theme.mp3 --music-volume 0.25

# 6. Share hooks_compilation.mp4 on social media
# "🚨 NINTENDO JUST DID WHAT?! Full episode link in bio 👇"
```

Result: A punchy 90-second teaser that drives traffic to your full episode!

## 🎉 Examples of Great Hooks

**From gaming podcasts:**
- "Sony just made the worst decision in PlayStation history"
- "I'm going to say something controversial... Elden Ring is overrated"
- "The leak I saw yesterday is going to blow your mind"
- "This game is a masterpiece and I'll fight anyone who disagrees"

**From tech podcasts:**
- "Apple is about to kill the iPhone"
- "I have information I can't share, but trust me..."
- "This is the biggest tech disaster of 2026"
- "Everyone is wrong about AI"

Study these patterns and apply them to your content!

## 📈 Next Steps

After creating your first compilation:

1. **Share it everywhere**: Social media, YouTube Community tab, email list
2. **A/B test**: Try different hook selections and see what performs better
3. **Track metrics**: Monitor which types of hooks drive the most clicks
4. **Iterate**: Use insights to improve future compilations
5. **Create variations**: Make multiple teasers for different platforms

---

**Questions?** Check the example files or review your main pipeline documentation.

**Happy hook hunting! 🎣**
