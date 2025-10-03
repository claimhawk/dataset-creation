#!/usr/bin/env python3.11
"""
Streamlit UI for UI-TARS dataset creation
"""

import streamlit as st
import os
from datetime import datetime
from PIL import Image
import json
from pathlib import Path

from create_training_dataset import WorkflowDatasetCreator

# Page config
st.set_page_config(
    page_title="UI-TARS Dataset Creator",
    page_icon="🤖",
    layout="centered"
)

# Initialize session state
if 'dataset_creator' not in st.session_state:
    st.session_state.dataset_creator = WorkflowDatasetCreator("my_dataset")
if 'last_saved_path' not in st.session_state:
    st.session_state.last_saved_path = None

st.title("🤖 UI-TARS Dataset Creator")
st.markdown("Create training datasets by annotating screenshots with tasks and actions")

# ============================================================================
# Dataset Info
# ============================================================================
st.sidebar.header("📊 Dataset Info")
dataset_name = st.sidebar.text_input(
    "Dataset Name",
    value="my_dataset",
    help="Name for your dataset folder"
)

if st.sidebar.button("🔄 New Dataset"):
    st.session_state.dataset_creator = WorkflowDatasetCreator(dataset_name)
    st.session_state.last_saved_path = None
    st.sidebar.success(f"Created new dataset: {dataset_name}")

# Update dataset name if changed
if st.session_state.dataset_creator and st.session_state.dataset_creator.dataset_name != dataset_name:
    st.session_state.dataset_creator = WorkflowDatasetCreator(dataset_name)

current_count = len(st.session_state.dataset_creator.dataset) if st.session_state.dataset_creator else 0
st.sidebar.metric("Total Samples", current_count)

if st.session_state.last_saved_path:
    st.sidebar.success(f"Last saved: {st.session_state.last_saved_path}")

# ============================================================================
# Main Form
# ============================================================================
with st.form("annotation_form", clear_on_submit=True):
    st.subheader("Add Training Sample")

    # Image Upload with drag and drop
    uploaded_file = st.file_uploader(
        "📸 Screenshot (drag and drop or click to upload)",
        type=['png', 'jpg', 'jpeg'],
        help="Upload a screenshot to annotate"
    )

    # Show preview
    if uploaded_file:
        st.image(uploaded_file, caption="Preview", use_column_width=True)

    st.divider()

    # Task Description
    task = st.text_input(
        "Task Description",
        placeholder="e.g., Click on Chrome icon in dock",
        help="What should the agent do in this screenshot?"
    )

    # Thought (optional)
    thought = st.text_area(
        "Thought (optional)",
        placeholder="e.g., Chrome is in the right dock at x=1710, y=100",
        help="Reasoning about how to accomplish the task",
        height=80
    )

    # Action
    action = st.text_input(
        "Action",
        placeholder="e.g., click(point='<point>1710 100</point>')",
        help="The action command to execute"
    )

    st.divider()

    # Submit button
    col1, col2 = st.columns([3, 1])
    with col1:
        submitted = st.form_submit_button("➕ Add to Dataset", type="primary", use_container_width=True)
    with col2:
        clear = st.form_submit_button("🗑️ Clear", use_container_width=True)

    if submitted:
        # Validate inputs
        if not uploaded_file:
            st.error("Please upload a screenshot")
        elif not task:
            st.error("Please enter a task description")
        elif not action:
            st.error("Please enter an action")
        else:
            # Save uploaded file
            os.makedirs("screenshots/temp", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"screenshot_{timestamp}_{uploaded_file.name}"
            image_path = f"screenshots/temp/{image_filename}"

            with open(image_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())

            # Add to dataset
            st.session_state.dataset_creator.add_workflow_step(
                image_path=image_path,
                task_description=task,
                action=action,
                thought=thought if thought else ""
            )

            st.success(f"✅ Added sample! Total: {len(st.session_state.dataset_creator.dataset)}")
            st.rerun()

# ============================================================================
# Action Buttons
# ============================================================================
st.divider()

col1, col2 = st.columns(2)

with col1:
    if st.button("💾 Save Dataset", type="primary", use_container_width=True):
        if len(st.session_state.dataset_creator.dataset) == 0:
            st.warning("Dataset is empty. Add some samples first!")
        else:
            saved_path = st.session_state.dataset_creator.save_dataset()
            st.session_state.last_saved_path = saved_path
            st.success(f"Saved {len(st.session_state.dataset_creator.dataset)} samples!")
            st.rerun()

with col2:
    if st.button("🗑️ Clear All", use_container_width=True):
        if len(st.session_state.dataset_creator.dataset) > 0:
            st.session_state.dataset_creator.dataset = []
            st.success("Dataset cleared")
            st.rerun()
        else:
            st.info("Dataset is already empty")

# ============================================================================
# Dataset Preview
# ============================================================================
if len(st.session_state.dataset_creator.dataset) > 0:
    st.divider()
    st.subheader("📋 Dataset Preview")

    # Show last few entries
    preview_count = min(3, len(st.session_state.dataset_creator.dataset))
    st.caption(f"Showing last {preview_count} of {len(st.session_state.dataset_creator.dataset)} samples")

    for i, entry in enumerate(reversed(st.session_state.dataset_creator.dataset[-preview_count:])):
        with st.expander(f"Sample {len(st.session_state.dataset_creator.dataset) - i}"):
            col1, col2 = st.columns([1, 2])

            with col1:
                # Try to show image
                img_path = Path(st.session_state.dataset_creator.data_dir) / entry['image']
                if img_path.exists():
                    st.image(str(img_path), use_column_width=True)
                else:
                    st.caption(f"Image: {entry['image']}")

            with col2:
                # Show conversation
                for msg in entry['conversations']:
                    if msg['from'] == 'human':
                        st.markdown(f"**Human:** {msg['value']}")
                    else:
                        st.markdown(f"**Assistant:** {msg['value']}")
