# Hooks Feature - Quick Start 🚀

## What Did We Just Create?

A complete system to create **compelling intro/teaser videos** from your podcast, like the ones you see from top podcasters - full of cliffhangers, controversial takes, and hooks that make viewers want to watch the full episode!

## 📁 New Files Created

1. **`hook_extraction_prompt.txt`** - Comprehensive AI prompt to identify engaging moments
2. **`scripts/utils/create_hooks_compilation.py`** - Script to compile hooks into a video
3. **`output/ai_analysis/hooks_example.json`** - Example of expected AI output format
4. **`HOOKS_FEATURE_GUIDE.md`** - Complete documentation and tips
5. **`README.md`** - Updated with hooks feature info

## ⚡ 3-Step Quick Start

### 1️⃣ Get Your Hooks (AI Analysis)

You already have a transcript at: `output/transcripts/nintendo_transcript.txt`

Now:
1. Open [**hook_extraction_prompt.txt**](hook_extraction_prompt.txt)
2. Copy the entire prompt
3. Go to ChatGPT/Claude and paste:
   ```
   [Paste the hook_extraction_prompt.txt content]
   
   Now analyze this transcript:
   [Paste your nintendo_transcript.txt content]
   ```
4. The AI will give you JSON output
5. Save it as: `output/ai_analysis/hooks.json`

**💡 Tip:** Check `output/ai_analysis/hooks_example.json` to see the expected format!

### 2️⃣ Generate the Compilation

Run:
```powershell
python scripts/utils/create_hooks_compilation.py
```

Or with background music:
```powershell
python scripts/utils/create_hooks_compilation.py --music path/to/your/music.mp3
```

### 3️⃣ Get Your Video!

Your hooks compilation will be at:
```
output/final/hooks_compilation.mp4
```

**Share it as:**
- Episode teaser on social media
- YouTube video intro
- Instagram/TikTok promo
- "Watch full episode" CTA content

## 🎯 What Makes This Work?

The AI looks for **8 types of hooks**:

| Icon | Type | Purpose |
|------|------|---------|
| 🔥 | Strong Opinions | "This is the BEST game ever" |
| 😱 | Shocking Statements | "You won't believe what happened" |
| 💥 | Passionate Reactions | "I can't believe they did this!" |
| 🎯 | Debates | "You're completely wrong!" |
| 🚀 | Bold Predictions | "In 6 months, everything changes" |
| 🎬 | Intriguing Questions | "What if Nintendo..." |
| 💣 | Cliffhangers | "I have info I can't share..." |
| 🎪 | Funny Moments | Unexpected jokes or situations |

**Each hook is 8-12 seconds**, combined into a **60-120 second compilation**.

## 🎨 Adding Background Music

Find good background music at:
- **Epidemic Sound** (paid, high quality)
- **Artlist** (subscription)
- **YouTube Audio Library** (free)
- **Free Music Archive** (Creative Commons)

Choose upbeat electronic, synthwave, or epic music that builds energy!

```powershell
# Add music at 30% volume (recommended)
python scripts/utils/create_hooks_compilation.py --music music.mp3 --music-volume 0.3

# Quieter background music
python scripts/utils/create_hooks_compilation.py --music music.mp3 --music-volume 0.2

# More prominent music
python scripts/utils/create_hooks_compilation.py --music music.mp3 --music-volume 0.5
```

## 🎬 Pro Tips for Your First Compilation

1. **Quality > Quantity**: 6 amazing hooks beat 12 mediocre ones
2. **Lead Strong**: First hook should be your MOST controversial/shocking
3. **End with Cliffhanger**: Leave them wanting more
4. **Mix It Up**: Alternate between different hook types
5. **Test Multiple**: Try different selections and see what works

## 📊 Example Real-World Usage

```
🎙️ You have: 2-hour Nintendo podcast
📝 Already done: Transcription ✓
💪 You want: Viral teaser to promote full episode

🤖 Step 1: AI finds 8 shocking Nintendo moments
📂 Step 2: Save as hooks.json
🎬 Step 3: Run compilation script
🎵 Step 4: Add epic gaming music
📱 Step 5: Post to social media

Result: 90-second teaser that drives traffic to full episode!
Caption: "🚨 NINTENDO JUST DID WHAT?! Full episode link in bio 👇"
```

## 🔧 Customization Options

```powershell
# Different transition effects
python scripts/utils/create_hooks_compilation.py --transition fade      # Smooth (default)
python scripts/utils/create_hooks_compilation.py --transition wipeleft  # Wipe effect
python scripts/utils/create_hooks_compilation.py --transition dissolve  # Cross dissolve

# Transition duration
python scripts/utils/create_hooks_compilation.py --duration 0.3  # Quick
python scripts/utils/create_hooks_compilation.py --duration 0.5  # Default
python scripts/utils/create_hooks_compilation.py --duration 1.0  # Cinematic
```

## 🆚 Hooks vs Regular Clips

**Your Main Pipeline (Existing):**
- Creates individual 30-90s viral clips
- For TikTok/Reels/Shorts direct upload
- Goal: Standalone viral content

**Hooks Feature (NEW):**
- Creates ONE compilation teaser
- 60-120 seconds of best moments
- Goal: Drive traffic to full episode

**Use Both!** Hooks for promotion, clips for distribution.

## 📚 Need More Help?

- **Full Guide**: [HOOKS_FEATURE_GUIDE.md](HOOKS_FEATURE_GUIDE.md)
- **Example Format**: `output/ai_analysis/hooks_example.json`
- **AI Prompt**: [hook_extraction_prompt.txt](hook_extraction_prompt.txt)
- **Main Pipeline**: [README.md](README.md)

## 🎉 Ready to Go!

You have everything you need. Just:
1. ✅ Use AI to analyze your transcript
2. ✅ Run the compilation script
3. ✅ Share your hooks video
4. ✅ Watch the views roll in!

**Happy hook hunting! 🎣**

---

*Questions? Check HOOKS_FEATURE_GUIDE.md for detailed explanations, examples, and troubleshooting.*
