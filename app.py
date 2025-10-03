#!/usr/bin/env python3.11
"""
Streamlit UI for UI-TARS dataset creation (Cloud-enabled with MongoDB)
"""

import streamlit as st
import os
from datetime import datetime
from PIL import Image
from io import BytesIO
import json
from db_client import DatasetDB

# Page config
st.set_page_config(
    page_title="UI-TARS Dataset Creator",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 UI-TARS Dataset Creator")
st.markdown("Create training datasets by annotating screenshots with tasks and actions")

# Initialize database connection
@st.cache_resource
def get_db():
    """Get database connection (cached)"""
    try:
        return DatasetDB()
    except ValueError as e:
        st.error(f"❌ Database connection failed: {e}")
        st.info("""
        **Setup Instructions:**

        1. **Local Development:**
           ```bash
           export MONGODB_URI='mongodb+srv://...'
           streamlit run app.py
           ```

        2. **Streamlit Cloud:**
           - Go to App Settings → Secrets
           - Add: `MONGODB_URI = "mongodb+srv://..."`

        3. **Get MongoDB Atlas (Free):**
           - Sign up at mongodb.com/cloud/atlas
           - Create M0 (free) cluster
           - Get connection string
        """)
        st.stop()

try:
    db = get_db()
    st.sidebar.success("✅ Connected to MongoDB")
except Exception as e:
    st.error(f"Failed to connect: {e}")
    st.stop()

# Initialize session state
if 'current_dataset' not in st.session_state:
    st.session_state.current_dataset = "my_dataset"

# ============================================================================
# Sidebar - Dataset Management
# ============================================================================
st.sidebar.header("📊 Dataset")

# List existing datasets
datasets = db.get_all_datasets()
dataset_names = [d['name'] for d in datasets] if datasets else []

if dataset_names:
    selected_dataset = st.sidebar.selectbox(
        "Select Dataset",
        options=dataset_names,
        index=0
    )
    st.session_state.current_dataset = selected_dataset
else:
    st.sidebar.info("No datasets yet. Create one below.")
    st.session_state.current_dataset = "my_dataset"

# New dataset creation
with st.sidebar.expander("➕ Create New Dataset"):
    new_dataset_name = st.text_input("Dataset Name", value="", key="new_dataset_name")
    new_dataset_desc = st.text_area("Description (optional)", value="", key="new_dataset_desc", height=80)

    if st.button("Create Dataset", key="create_dataset_btn"):
        if new_dataset_name:
            db.create_dataset(new_dataset_name, new_dataset_desc)
            st.session_state.current_dataset = new_dataset_name
            st.success(f"Created dataset: {new_dataset_name}")
            st.rerun()
        else:
            st.error("Please enter a dataset name")

# Dataset stats
stats = db.get_dataset_stats(st.session_state.current_dataset)
if stats:
    st.sidebar.metric("Total Samples", stats['sample_count'])
    st.sidebar.caption(f"Created: {stats['created_at'].strftime('%Y-%m-%d')}")
else:
    st.sidebar.metric("Total Samples", 0)
    st.sidebar.caption(f"Dataset: {st.session_state.current_dataset}")

# ============================================================================
# Main Form - Add Sample
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
        help="What should the agent do in this screenshot?",
        key="task_input"
    )

    # Thought (optional)
    thought = st.text_area(
        "Thought (optional)",
        placeholder="e.g., Chrome is in the right dock at x=1710, y=100",
        help="Reasoning about how to accomplish the task",
        height=80,
        key="thought_input"
    )

    # Action
    action = st.text_input(
        "Action",
        placeholder="e.g., click(point='<point>1710 100</point>')",
        help="The action command to execute",
        key="action_input"
    )

    st.divider()

    # Submit button
    submitted = st.form_submit_button("➕ Add to Dataset", type="primary", use_container_width=True)

    if submitted:
        # Validate inputs
        if not uploaded_file:
            st.error("Please upload a screenshot")
        elif not task:
            st.error("Please enter a task description")
        elif not action:
            st.error("Please enter an action")
        else:
            try:
                # Read image bytes
                uploaded_file.seek(0)  # Reset file pointer
                image_bytes = uploaded_file.read()

                # Add to database
                sample_id = db.add_sample(
                    dataset_name=st.session_state.current_dataset,
                    image_bytes=image_bytes,
                    task=task,
                    thought=thought if thought else "",
                    action=action
                )

                st.success(f"✅ Added sample to {st.session_state.current_dataset}!")
                st.balloons()
                st.rerun()

            except Exception as e:
                st.error(f"Failed to add sample: {e}")

# ============================================================================
# Export Dataset
# ============================================================================
st.divider()

col1, col2 = st.columns(2)

with col1:
    if st.button("💾 Export Dataset", use_container_width=True):
        if not stats or stats['sample_count'] == 0:
            st.warning("No samples to export")
        else:
            with st.spinner("Exporting dataset..."):
                try:
                    annotations = db.export_dataset(st.session_state.current_dataset)

                    if annotations:
                        # Convert to JSON
                        json_str = json.dumps(annotations, indent=2)

                        # Download button
                        st.download_button(
                            label=f"⬇️ Download {len(annotations)} samples",
                            data=json_str,
                            file_name=f"{st.session_state.current_dataset}_annotations.json",
                            mime="application/json",
                            use_container_width=True
                        )

                        st.success(f"Exported {len(annotations)} samples!")
                    else:
                        st.warning("No samples to export")
                except Exception as e:
                    st.error(f"Export failed: {e}")

with col2:
    if st.button("🗑️ Clear Dataset", use_container_width=True):
        if stats and stats['sample_count'] > 0:
            if st.button("⚠️ Confirm Delete", type="secondary"):
                db.delete_dataset(st.session_state.current_dataset)
                st.success(f"Deleted {st.session_state.current_dataset}")
                st.rerun()

# ============================================================================
# Dataset Preview
# ============================================================================
if stats and stats['sample_count'] > 0:
    st.divider()
    st.subheader("📋 Recent Samples")

    # Get recent samples
    try:
        samples = db.get_dataset_samples(st.session_state.current_dataset, limit=5)

        for i, sample in enumerate(samples):
            with st.expander(f"Sample {i+1}: {sample['task'][:60]}{'...' if len(sample['task']) > 60 else ''}"):
                col1, col2 = st.columns([1, 2])

                with col1:
                    # Decode and display image
                    import base64
                    try:
                        image_data = base64.b64decode(sample['image_data'])
                        image = Image.open(BytesIO(image_data))
                        st.image(image, use_column_width=True)
                    except Exception as e:
                        st.error(f"Failed to load image: {e}")

                with col2:
                    st.markdown(f"**Task:** {sample['task']}")

                    if sample.get('thought'):
                        st.markdown(f"**Thought:** {sample['thought']}")

                    st.markdown(f"**Action:** `{sample['action']}`")

                    st.caption(f"Created: {sample['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        st.error(f"Failed to load samples: {e}")

# ============================================================================
# Footer
# ============================================================================
st.divider()
st.caption("""
**Next steps:**
1. Export dataset as JSON
2. Use for fine-tuning with `FINETUNING.md`
3. Deploy model!
""")
