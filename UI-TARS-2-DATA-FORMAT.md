# UI-TARS-2 Data Format

**Source:** [UI-TARS-2 Technical Report](https://arxiv.org/abs/2509.02544) - Advancing GUI Agent with Multi-Turn Reinforcement Learning

## Overview

UI-TARS-2 uses a **multi-turn trajectory format** for training data, focusing on sequences of thought-action-observation triplets rather than single-step examples.

## Data Structure

### Trajectory Format

A trajectory τ consists of a sequence of steps:

```
τ = {(t₀, a₀, o₀), (t₁, a₁, o₁), ..., (tₜ, aₜ, oₜ)}
```

Each step contains:
- **t (thought)**: Reasoning/cognitive process
- **a (action)**: GUI action to execute
- **o (observation)**: Environment feedback/result

### Memory State

Trajectories maintain hierarchical memory:

```
ℳₜ = (𝒲ₜ, ℰₜ)
```

- **Working Memory (𝒲ₜ)**: Recent steps in high fidelity
- **Episodic Memory (ℰₜ)**: Compressed summaries of past episodes

## Data Flywheel

UI-TARS-2 employs a self-reinforcing data flywheel:

```
Cold Start → CT (Continual Pre-training) → SFT (Supervised Fine-Tuning) → RL → New Trajectories → Repeat
```

### Stages:

1. **Cold Start**: Initial data from tutorials, demonstrations
2. **Continual Pre-training (CT)**: Foundation knowledge
3. **Supervised Fine-Tuning (SFT)**: Task-specific training
4. **Multi-Turn RL**: Policy optimization via trajectories
5. **Trajectory Generation**: Model generates new data via:
   - Rejection sampling
   - Interactive annotation

## Sample Format (Our Implementation)

### Single-Turn Sample (UI-TARS 1.0 Style)
```json
{
  "image_data": "base64_encoded_screenshot",
  "task": "Click on Chrome icon in dock",
  "thought": "Chrome is in the right dock at x=1710, y=100",
  "action": "click(point='<point>1710 100</point>')",
  "action_type": "click",
  "action_params": {"x": "1710", "y": "100"},
  "conversations": [
    {
      "from": "human",
      "value": "<image>\nYou are a GUI agent. The task is: Click on Chrome icon in dock\n\nWhat is the next action?"
    },
    {
      "from": "gpt",
      "value": "Thought: Chrome is in the right dock at x=1710, y=100\nAction: click(point='<point>1710 100</point>')"
    }
  ]
}
```

### Multi-Turn Trajectory (UI-TARS 2.0 Style)
```json
{
  "task": "Open Chrome and navigate to google.com",
  "trajectory": [
    {
      "step": 0,
      "image_data": "base64_step0_screenshot",
      "thought": "I need to click on Chrome in the dock to open it",
      "action": "click(point='<point>1710 100</point>')",
      "observation": "Chrome opened successfully"
    },
    {
      "step": 1,
      "image_data": "base64_step1_screenshot",
      "thought": "Chrome is open, now I need to click the address bar",
      "action": "click(point='<point>800 50</point>')",
      "observation": "Address bar is focused"
    },
    {
      "step": 2,
      "image_data": "base64_step2_screenshot",
      "thought": "Address bar is active, type google.com",
      "action": "type(content='google.com')",
      "observation": "Typed 'google.com' in address bar"
    },
    {
      "step": 3,
      "image_data": "base64_step3_screenshot",
      "thought": "Press enter to navigate",
      "action": "press(key='enter')",
      "observation": "Navigated to google.com"
    },
    {
      "step": 4,
      "image_data": "base64_step4_screenshot",
      "thought": "Task completed successfully",
      "action": "finished(content='Successfully opened Chrome and navigated to google.com')",
      "observation": "Task complete"
    }
  ],
  "success": true,
  "total_steps": 5
}
```

## Key Differences from UI-TARS 1.0

| Aspect | UI-TARS 1.0 | UI-TARS 2.0 |
|--------|-------------|-------------|
| **Data Unit** | Single screenshot-action pair | Multi-turn trajectory |
| **Memory** | Stateless | Hierarchical (working + episodic) |
| **Training** | SFT only | CT + SFT + Multi-turn RL |
| **Thought** | Optional | Explicit reasoning required |
| **Observation** | Not stored | Captured per step |
| **Data Generation** | Manual annotation | Self-reinforcing flywheel |

## Implementation Notes

### Current ClaimHawk Dataset Creator

Our Streamlit app currently generates **UI-TARS 1.0 style** single-turn samples. This is ideal for:
- Cold-start data collection
- Initial SFT training
- Simple task annotation

### Upgrading to Multi-Turn Trajectories

To support UI-TARS 2.0 style data:

1. **Add trajectory mode** to dataset creation
2. **Capture observations** after each action
3. **Link sequential steps** within a task
4. **Store working/episodic memory** states
5. **Track success/failure** outcomes

### Example Enhancement

```python
class TrajectoryBuilder:
    def __init__(self, task):
        self.task = task
        self.steps = []
        self.working_memory = []
        self.episodic_memory = []

    def add_step(self, image, thought, action, observation):
        self.steps.append({
            'step': len(self.steps),
            'image_data': image,
            'thought': thought,
            'action': action,
            'observation': observation
        })

        # Update working memory (keep last N steps)
        self.working_memory.append(self.steps[-1])
        if len(self.working_memory) > 5:
            # Compress and move to episodic memory
            self.episodic_memory.append(self._compress(self.working_memory.pop(0)))

    def finalize(self):
        return {
            'task': self.task,
            'trajectory': self.steps,
            'success': any(step['action'].startswith('finished') for step in self.steps),
            'total_steps': len(self.steps)
        }
```

## Coordinate Normalization

**Source:** [UI-TARS Issue #39](https://github.com/bytedance/UI-TARS/issues/39)

### Alternative Format (Mind2Web Dataset)

Some datasets use normalized coordinates [0, 1000] with different box notation:

```python
# Normalized coordinate format
click(start_box="<|box_start|>(x, y)<|box_end|>")
select(start_box="<|box_start|>(x, y)<|box_end|>")
type(content="text", start_box="<|box_start|>(x, y)<|box_end|>")
```

Where:
- Coordinates are normalized to range [0, 1000]
- Uses `<|box_start|>` and `<|box_end|>` tokens instead of `<point>` tokens
- `type` action includes both content AND click position

### Our Format (Native Pixel Coordinates)

We use the native format from UI-TARS inference:

```python
# Pixel coordinate format
click(point='<point>x y</point>')
type(content='text')
```

Where:
- Coordinates are in actual pixel space (logical resolution on Retina)
- Uses `<point>` tokens
- `type` action is content-only (no click position)

**Note:** The model can handle both formats during training, but our dataset creator uses the pixel-based format for simplicity and compatibility with the official inference code.

## References

- **Paper:** [UI-TARS-2 Technical Report (arXiv:2509.02544)](https://arxiv.org/abs/2509.02544)
- **GitHub:** [bytedance/UI-TARS](https://github.com/bytedance/UI-TARS)
- **Action Parser:** [action_parser.py](https://github.com/bytedance/UI-TARS/blob/main/codes/ui_tars/action_parser.py)
- **Data Format Discussion:** [Issue #39](https://github.com/bytedance/UI-TARS/issues/39)
