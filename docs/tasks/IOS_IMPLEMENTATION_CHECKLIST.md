# iOS Implementation Checklist - Real-Time Thinking Updates

**Quick Guide for iOS Developers**

---

## Overview

The backend now sends `thinking_update` SSE events every 5 seconds during LLM analysis. This document provides a step-by-step checklist to add this feature to the iOS app.

**Time to implement**: 10-15 minutes  
**Difficulty**: Easy  
**Impact**: Significantly improved user experience  

---

## Step 1: Add the Data Model ✓

Add this struct to your project (e.g., `Models.swift`):

```swift
struct ThinkingUpdateEvent: Decodable {
    let type: String
    let job_id: String
    let thinking: String  // e.g., "Generating analysis... (150 tokens, 44.1 tps)"
}
```

**Checklist:**
- [ ] Copy struct code
- [ ] Add to your models file
- [ ] Verify it compiles

---

## Step 2: Add State Variables ✓

In your analysis view, add state variables:

```swift
@State private var thinkingMessage: String = ""
@State private var isThinking: Bool = false
```

**Checklist:**
- [ ] Add both state variables
- [ ] Verify state is accessible in your view

---

## Step 3: Add Event Listener ✓

In your SSE stream connection handler, add this listener:

```swift
// Listen for 'thinking_update' events (NEW! - Real-time LLM feedback)
eventSource.addEventListener("thinking_update") { id, event, data in
    if let data = data?.data(using: .utf8),
       let event = try? JSONDecoder().decode(ThinkingUpdateEvent.self, from: data) {
        DispatchQueue.main.async {
            // Update thinking state
            self.thinkingMessage = event.thinking
            self.isThinking = true
        }
    }
}
```

**Where to add it:**
- Place between `status_update` and `analysis_complete` listeners
- Keep same pattern as other event listeners

**Checklist:**
- [ ] Add event listener code
- [ ] Update state variables correctly
- [ ] Verify it's in the right place in the listener chain
- [ ] Check threading (should be on main dispatch queue)

---

## Step 4: Display in UI ✓

Choose ONE of the following approaches:

### Option A: Simple (Recommended for quick implementation)

```swift
if isThinking {
    Text(thinkingMessage)
        .font(.caption)
        .foregroundColor(.secondary)
}
```

### Option B: With Icon and Animation (Recommended for best UX)

```swift
if isThinking {
    HStack(spacing: 8) {
        Image(systemName: "brain")
            .font(.title2)
            .foregroundColor(.blue)
            .transition(.scale.combined(with: .opacity))
        
        Text(thinkingMessage)
            .font(.body)
            .foregroundColor(.secondary)
            .lineLimit(1)
            .truncationMode(.tail)
        
        Spacer()
    }
    .padding()
    .background(Color(.systemGray6))
    .cornerRadius(8)
    .transition(.move(edge: .top).combined(with: .opacity))
}
.animation(.easeInOut(duration: 0.3), value: isThinking)
```

### Option C: Detailed Metrics Display

```swift
if isThinking, let (tokens, speed) = parseThinkingMetrics(thinkingMessage) {
    HStack(spacing: 12) {
        VStack(alignment: .leading) {
            Text("Tokens Generated").font(.caption).foregroundColor(.secondary)
            Text("\(tokens)").font(.headline)
        }
        
        Divider().frame(height: 24)
        
        VStack(alignment: .leading) {
            Text("Speed").font(.caption).foregroundColor(.secondary)
            Text(String(format: "%.1f tps", speed)).font(.headline)
        }
        
        Spacer()
    }
    .padding()
    .background(Color(.systemGray6))
    .cornerRadius(8)
}
```

For Option C, also add the helper function:

```swift
func parseThinkingMetrics(_ message: String) -> (tokens: Int, speed: Double)? {
    let pattern = #"\((\d+) tokens,\s*([\d.]+) tps\)"#
    if let regex = try? NSRegularExpression(pattern: pattern),
       let match = regex.firstMatch(in: message, range: NSRange(message.startIndex..., in: message)),
       let tokenRange = Range(match.range(at: 1), in: message),
       let speedRange = Range(match.range(at: 2), in: message),
       let tokens = Int(message[tokenRange]),
       let speed = Double(message[speedRange]) {
        return (tokens, speed)
    }
    return nil
}
```

**Placement:**
- Add near where you display other analysis progress
- Typically above the loading spinner or status text
- Should update as thinking messages arrive

**Checklist:**
- [ ] Choose your preferred UI option
- [ ] Copy the code to your view
- [ ] Test that it displays correctly
- [ ] Verify animations work smoothly

---

## Step 5: Optional Enhancements ✓

### Add Auto-Fade Behavior

```swift
// In your SSE listener, after updating state:
DispatchQueue.main.asyncAfter(deadline: .now() + 10.0) {
    if self.thinkingMessage == event.thinking {
        withAnimation {
            self.isThinking = false
        }
    }
}
```

**Benefit**: Message automatically fades out if no updates for 10 seconds

**Checklist:**
- [ ] Add auto-fade if desired
- [ ] Test timing works as expected

### Clear Message When Analysis Completes

```swift
// In your 'analysis_complete' event listener:
eventSource.addEventListener("analysis_complete") { id, event, data in
    // ... existing code ...
    DispatchQueue.main.async {
        self.isThinking = false  // Hide thinking message
        // ... show results ...
    }
}
```

**Benefit**: Thinking message disappears when results appear

**Checklist:**
- [ ] Add clear logic
- [ ] Test message hides properly

---

## Testing Checklist

### Local Testing

- [ ] Services running (job_service, ai_advisor)
- [ ] Image ready for analysis
- [ ] Build and run iOS app
- [ ] Submit image for analysis
- [ ] Check that thinking message appears in ~5 seconds
- [ ] Verify token count increases: 50 → 100 → 150
- [ ] Verify speed is displayed: 40.0 tps, 42.5 tps, etc.
- [ ] Message continues every 5 seconds until analysis completes
- [ ] Message disappears when results shown
- [ ] No crashes or errors in logs

### Verification Points

✓ First thinking update appears within 5-7 seconds  
✓ Updates continue roughly every 5 seconds  
✓ Token count increases with each update  
✓ Generation speed values are reasonable (40-50 tps typical)  
✓ UI animates smoothly when message appears/disappears  
✓ No memory leaks (monitor memory while analyzing)  
✓ Works with multiple advisors  
✓ Works with RAG enabled/disabled  

---

## Debugging

### Message Not Appearing

1. Check if event listener is actually being called:
   ```swift
   print("thinking_update received: \(event.thinking)")
   ```

2. Verify `isThinking` state is updating:
   ```swift
   print("isThinking: \(self.isThinking)")
   ```

3. Ensure UI is checking `isThinking`:
   ```swift
   if isThinking { ... }  // Must be in view body
   ```

### Showing Old Messages

1. Clear thinking state when new job starts:
   ```swift
   thinkingMessage = ""
   isThinking = false
   ```

2. Add in upload/analysis start:
   ```swift
   eventSource.connect()  // After connecting
   self.thinkingMessage = ""  // Clear old message
   self.isThinking = false
   ```

### Animation Issues

1. Verify animation block includes value:
   ```swift
   .animation(.easeInOut(duration: 0.3), value: isThinking)
   ```

2. All state changes should be on main thread:
   ```swift
   DispatchQueue.main.async {
       self.isThinking = true
   }
   ```

---

## Performance Notes

✅ **Minimal Impact**: Simple text updates every 5 seconds  
✅ **No Network Overhead**: Uses existing SSE connection  
✅ **Efficient Parsing**: JSON decoding is negligible  
✅ **Memory**: Small string storage (~50 bytes per message)  
✅ **CPU**: Single UI update every 5 seconds  

---

## Rollback (if needed)

If you need to disable this feature:

1. Comment out the event listener
2. Remove state variables (or leave them unused)
3. Remove UI display code

Everything else remains unchanged!

---

## Summary

| Step | Task | Time |
|------|------|------|
| 1 | Add data model | 1 min |
| 2 | Add state variables | 1 min |
| 3 | Add event listener | 3 min |
| 4 | Add UI display | 5 min |
| 5 | Test | 5 min |
| **Total** | | **15 min** |

---

## Resources

- **Full Documentation**: See `docs/ios/API_INTEGRATION.md`
- **Backend Implementation**: See `mondrian/ai_advisor_service.py` (lines 604-679)
- **Update Guide**: See `IOS_API_DOCUMENTATION_UPDATE.md`

---

## Support

Questions? Check:
1. Full docs in `docs/ios/API_INTEGRATION.md`
2. Event listener examples in same file
3. Backend code showing what's being sent
4. Debug output if something's not working

---

## Quick Reference

```swift
// 1. Model
struct ThinkingUpdateEvent: Decodable {
    let type: String
    let job_id: String
    let thinking: String
}

// 2. State
@State private var thinkingMessage: String = ""
@State private var isThinking: Bool = false

// 3. Listener
eventSource.addEventListener("thinking_update") { id, event, data in
    if let data = data?.data(using: .utf8),
       let event = try? JSONDecoder().decode(ThinkingUpdateEvent.self, from: data) {
        DispatchQueue.main.async {
            self.thinkingMessage = event.thinking
            self.isThinking = true
        }
    }
}

// 4. UI
if isThinking {
    Text(thinkingMessage).font(.caption).foregroundColor(.secondary)
}
```

**That's it! 4 simple pieces = real-time thinking updates** ✓

---

**Status**: Ready to implement  
**Estimated time**: 15 minutes  
**Difficulty**: Easy  
**User impact**: Very positive!  

🚀 Ready to implement? Start with the model!
