# Technique-Based RAG Requirements

## Objective

Analyze advisor's images to learn their signature techniques, then analyze the user's image and provide feedback on how to make the user's techniques more effective by matching the advisor's approach.

## Workflow

### 1. Advisor Image Analysis (Indexing Phase)
- **When**: During initial indexing of advisor images
- **What**: Analyze each advisor image to extract:
  - **Techniques used**: zone_system, depth_of_field, composition, lighting, foreground_anchoring
  - **Dimensional scores**: How well each technique is executed (composition, lighting, focus_sharpness, etc.)
  - **Comments**: Qualitative feedback on technique execution
- **Storage**: Save to `dimensional_profiles` table with `techniques` JSON field

### 2. User Image Analysis (Pass 1)
- **When**: First pass of RAG workflow
- **What**: Extract from user's image:
  - **Techniques used**: What techniques did the user employ?
  - **Dimensional scores**: How well did they execute each dimension?
- **Purpose**: Establish baseline for comparison

### 3. Technique Matching (Query Phase)
- **When**: After Pass 1 completes
- **What**: Find advisor images that use similar techniques
- **Purpose**: Get reference images showing how the advisor executed those same techniques

### 4. Comparative Analysis (Pass 2)
- **When**: Second pass of RAG workflow
- **What**: Compare user's technique execution to advisor's technique execution
- **Output Format**: Identical to baseline (same JSON structure)
- **Feedback Focus**:
  - **For each dimension**: Compare how well user executed techniques vs how advisor executed them
  - **Identify gaps**: Where user's technique execution falls short
  - **Provide recommendations**: Specific steps to improve technique execution to match advisor's level

## Key Principles

1. **Technique-Based, Not Similarity-Based**
   - Match images by techniques used, not dimensional similarity
   - User might use same techniques but execute them differently

2. **Execution Quality Comparison**
   - Compare how well user executes techniques vs advisor
   - Example: Both use "deep DOF", but advisor achieves better sharpness across all planes

3. **Actionable Feedback**
   - Every recommendation should reference advisor's reference images
   - Provide specific steps: "To match Reference #1's approach, use f/16 instead of f/8"

4. **Same Output Structure**
   - RAG output must be structurally identical to baseline
   - Only difference: Content quality (technique-based recommendations vs generic feedback)

## Example Feedback Format

For each dimension (e.g., Composition):

```
**User's Technique**: You used rule_of_thirds composition.
**Advisor's Technique**: Reference images #1, #2, #3 use leading_lines composition.
**Execution Comparison**: Your composition scores 7/10. Advisor's reference images score 9/10.
**Recommendation**: To improve your composition technique:
  1. Look for natural leading lines (roads, rivers, tree lines)
  2. Position them to guide the eye through the frame
  3. Use them to create depth and visual flow
  (See Reference #1 "The Tetons and the Snake River" for example)
```

## Technical Implementation

- **Pass 1 Prompt**: Extract techniques + dimensional scores
- **Technique Matching**: Find advisor images with matching techniques
- **Pass 2 Prompt**: Compare execution quality and provide improvement steps
- **Output**: Same JSON structure as baseline, converted to HTML identically
