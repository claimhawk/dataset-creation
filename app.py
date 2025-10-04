#!/usr/bin/env python3.11
"""
Streamlit UI for ClaimHawk dataset creation (Cloud-enabled with MongoDB)
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
    page_title="ClaimHawk Dataset Creator",
    page_icon="🦅",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Hide Streamlit UI elements
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ============================================================================
# Authentication
# ============================================================================
def check_auth():
    """Check if user is authenticated"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    # Login form
    st.title("🦅 ClaimHawk Dataset Creator")
    st.markdown("### Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            # Get credentials from secrets
            try:
                users = st.secrets.get("users", {})
                if username in users and users[username] == password:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
            except Exception as e:
                st.error(f"Authentication error: {e}")

    return False

if not check_auth():
    st.stop()

# Show logout button
col1, col2 = st.columns([5, 1])
with col2:
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

st.title("🦅 ClaimHawk Dataset Creator")
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
except Exception as e:
    st.error(f"Failed to connect: {e}")
    st.stop()

# Initialize session state
if 'current_dataset' not in st.session_state:
    st.session_state.current_dataset = "claimhawk_dataset"

# ============================================================================
# Dataset Management (inline, no sidebar)
# ============================================================================

# List existing datasets
datasets = db.get_all_datasets()
dataset_names = [d['name'] for d in datasets] if datasets else []

col1, col2 = st.columns([2, 1])

with col1:
    if dataset_names:
        selected_dataset = st.selectbox(
            "📊 Select Dataset",
            options=dataset_names,
            index=0 if st.session_state.current_dataset not in dataset_names else dataset_names.index(st.session_state.current_dataset)
        )
        st.session_state.current_dataset = selected_dataset
    else:
        st.info("No datasets yet. Create one below.")
        st.session_state.current_dataset = "claimhawk_dataset"

with col2:
    stats = db.get_dataset_stats(st.session_state.current_dataset)
    if stats:
        st.metric("Total Samples", stats['sample_count'])
    else:
        st.metric("Total Samples", 0)

# New dataset creation (admin only)
if st.session_state.username == "admin":
    with st.expander("➕ Create New Dataset"):
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

st.divider()

stats = db.get_dataset_stats(st.session_state.current_dataset)

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

    # Action type selector (from UI-TARS action_parser.py)
    action_type = st.selectbox(
        "Action Type",
        options=["click", "left_single", "left_double", "right_single", "hover",
                 "type", "hotkey", "press", "keydown", "keyup",
                 "drag", "select", "scroll", "finished", "custom"],
        key="action_type_select"
    )

    # Dynamic fields based on action type
    action = ""
    action_params = {}

    if action_type in ["click", "left_single", "left_double", "right_single", "hover"]:
        col1, col2 = st.columns(2)
        with col1:
            x = st.text_input("X coordinate", value="", placeholder="1710", key="coord_x")
        with col2:
            y = st.text_input("Y coordinate", value="", placeholder="100", key="coord_y")

        # Clean and parse coordinates (support comma-separated like "38,38" or space-separated "38 38")
        if x and ',' in x:
            # User entered "38,38" format
            parts = x.split(',')
            x_clean = parts[0].strip()
            y = parts[1].strip() if len(parts) > 1 else y
        else:
            x_clean = x.replace("<point>", "").strip()

        if x_clean and y:
            action = f"{action_type}(point='<point>{x_clean} {y}</point>')"
            action_params = {'x': x_clean, 'y': y}
        else:
            action = f"{action_type}(point='<point>x y</point>')"

    elif action_type == "type":
        text_content = st.text_input("Text to type", value="", placeholder="Hello World", key="type_content")
        if text_content:
            action = f"type(content='{text_content}')"
            action_params = {'content': text_content}
        else:
            action = "type(content='text here')"

    elif action_type in ["hotkey", "press", "keydown", "keyup"]:
        key_combo = st.text_input("Key combination", value="", placeholder="ctrl c" if action_type == "hotkey" else "enter", key="key_combo")
        if key_combo:
            action = f"{action_type}(key='{key_combo}')"
            action_params = {'key': key_combo}
        else:
            action = f"{action_type}(key='{'ctrl c' if action_type == 'hotkey' else 'enter'}')"

    elif action_type in ["drag", "select"]:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            x1 = st.text_input("Start X", value="", placeholder="100", key="drag_x1")
        with col2:
            y1 = st.text_input("Start Y", value="", placeholder="100", key="drag_y1")
        with col3:
            x2 = st.text_input("End X", value="", placeholder="500", key="drag_x2")
        with col4:
            y2 = st.text_input("End Y", value="", placeholder="500", key="drag_y2")

        x1_clean = x1.replace("<point>", "").strip()

        if x1_clean and y1 and x2 and y2:
            action = f"{action_type}(start_point='<point>{x1_clean} {y1}</point>', end_point='<point>{x2} {y2}</point>')"
            action_params = {'x1': x1_clean, 'y1': y1, 'x2': x2, 'y2': y2}
        else:
            action = f"{action_type}(start_point='<point>x1 y1</point>', end_point='<point>x2 y2</point>')"

    elif action_type == "scroll":
        col1, col2, col3 = st.columns(3)
        with col1:
            x = st.text_input("X coordinate", value="", placeholder="800", key="scroll_x")
        with col2:
            y = st.text_input("Y coordinate", value="", placeholder="600", key="scroll_y")
        with col3:
            direction = st.selectbox("Direction", options=["up", "down", "left", "right"], key="scroll_dir")

        x_clean = x.replace("<point>", "").strip()

        if x_clean and y:
            action = f"scroll(point='<point>{x_clean} {y}</point>', direction='{direction}')"
            action_params = {'x': x_clean, 'y': y, 'direction': direction}
        else:
            action = f"scroll(point='<point>x y</point>', direction='{direction}')"

    elif action_type == "finished":
        message = st.text_input("Completion message", value="", placeholder="Task completed successfully", key="finished_msg")
        if message:
            action = f"finished(content='{message}')"
            action_params = {'content': message}
        else:
            action = "finished(content='Task completed')"

    elif action_type == "custom":
        action = st.text_input("Custom Action", value="", placeholder="Enter custom action here", key="custom_action")
        action_params = {'raw': action}

    # Display final action
    st.code(action if action else f"{action_type}(...)", language="python")

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

                # Add to database with action type and params
                sample_id = db.add_sample(
                    dataset_name=st.session_state.current_dataset,
                    image_bytes=image_bytes,
                    task=task,
                    thought=thought if thought else "",
                    action=action,
                    action_type=action_type,
                    action_params=action_params
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
