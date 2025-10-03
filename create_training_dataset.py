#!/usr/bin/env python3.11
"""
Create UI-TARS training dataset from recorded workflows
Format: LLaVA-style JSON for Qwen2.5-VL fine-tuning

⚠️ FORMAT VERIFICATION REQUIRED:
This script uses LLaVA-style format based on:
1. 2U1/Qwen2-VL-Finetune requirements (conversations array)
2. Observed inference output format (Thought: ... Action: ...)
3. Qwen2.5-VL conventions (<image> token, from: human/gpt)

The exact format for UI-TARS fine-tuning is not officially documented.
Before fine-tuning, verify against official Qwen2.5-VL examples or contact
ByteDance (TARS@bytedance.com) for guidance.

Known format variations:
- Coordinates: <point>x y</point> vs <|box_start|>(x,y)<|box_end|>
- Normalization: pixel values vs normalized [0, 1000]
- Action format: start_box vs point parameter names
"""

import json
import os
from datetime import datetime

class WorkflowDatasetCreator:
    def __init__(self, dataset_name="ui_workflows"):
        self.dataset_name = dataset_name
        self.data_dir = f"datasets/{dataset_name}"
        self.images_dir = f"{self.data_dir}/images"
        self.annotations_file = f"{self.data_dir}/annotations.json"

        # Create directories
        os.makedirs(self.images_dir, exist_ok=True)

        # Initialize dataset
        self.dataset = []

    def add_workflow_step(self, image_path, task_description, action, thought=""):
        """
        Add a single step from a workflow

        Args:
            image_path: Path to screenshot
            task_description: What the user wants to do
            action: The action to take (e.g., "click(point='<point>1200 500</point>')")
            thought: Optional reasoning about the action
        """
        # Copy image to dataset
        image_filename = os.path.basename(image_path)
        dataset_image_path = f"{self.images_dir}/{image_filename}"

        if not os.path.exists(dataset_image_path):
            import shutil
            shutil.copy(image_path, dataset_image_path)

        # Create conversation format
        entry = {
            "id": f"workflow_{len(self.dataset)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "image": f"images/{image_filename}",
            "conversations": [
                {
                    "from": "human",
                    "value": f"<image>\nYou are a GUI agent. The task is: {task_description}\n\nWhat is the next action?"
                },
                {
                    "from": "gpt",
                    "value": f"Thought: {thought}\nAction: {action}" if thought else f"Action: {action}"
                }
            ]
        }

        self.dataset.append(entry)
        print(f"Added step {len(self.dataset)}: {task_description[:50]}...")

    def add_full_workflow(self, workflow_name, steps):
        """
        Add a complete workflow with multiple steps

        Args:
            workflow_name: Name of the workflow
            steps: List of dicts with keys: image_path, task, action, thought
        """
        print(f"\nAdding workflow: {workflow_name}")
        print(f"Steps: {len(steps)}")

        for i, step in enumerate(steps):
            self.add_workflow_step(
                image_path=step['image_path'],
                task_description=f"{workflow_name} - Step {i+1}: {step['task']}",
                action=step['action'],
                thought=step.get('thought', '')
            )

    def save_dataset(self):
        """Save dataset to JSON file"""
        with open(self.annotations_file, 'w') as f:
            json.dump(self.dataset, f, indent=2)

        print(f"\n✅ Dataset saved!")
        print(f"   Total samples: {len(self.dataset)}")
        print(f"   Annotations: {self.annotations_file}")
        print(f"   Images: {self.images_dir}")

        return self.annotations_file

    def create_example_workflows(self):
        """Create example workflows for common tasks"""

        # Example 1: Open Chrome and navigate
        chrome_workflow = [
            {
                'image_path': 'screenshots/screenshot_example1.png',
                'task': 'Open Chrome browser',
                'action': "click(point='<point>1710 100</point>')",
                'thought': 'Chrome icon is in the dock on the right side at approximately x=1710'
            },
            {
                'image_path': 'screenshots/screenshot_example2.png',
                'task': 'Navigate to website',
                'action': "type(content='google.com')",
                'thought': 'Address bar is focused, type the URL'
            },
            {
                'image_path': 'screenshots/screenshot_example3.png',
                'task': 'Submit URL',
                'action': "hotkey(key='enter')",
                'thought': 'Press enter to navigate'
            }
        ]

        # Add workflow (if images exist)
        # self.add_full_workflow("Open Chrome and Navigate", chrome_workflow)

def main():
    """Example usage"""
    creator = WorkflowDatasetCreator(dataset_name="mac_workflows")

    # Example: Add manual annotations
    # creator.add_workflow_step(
    #     image_path="/path/to/screenshot.png",
    #     task_description="Click on Chrome icon in dock",
    #     action="click(point='<point>1710 100</point>')",
    #     thought="Chrome is in the right dock at x=1710"
    # )

    # Save dataset
    # creator.save_dataset()

    print("Dataset creator initialized!")
    print("Use creator.add_workflow_step() or creator.add_full_workflow() to add data")
    print("Then call creator.save_dataset() to save")

if __name__ == "__main__":
    main()
