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
from action_config import ACTION_CONFIG, parse_coordinates, build_action

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
st.subheader("Add Training Sample")

# Image Upload (outside form for preview)
uploaded_file = st.file_uploader(
    "📸 Screenshot (drag and drop or click to upload)",
    type=['png', 'jpg', 'jpeg'],
    help="Upload a screenshot to annotate",
    key="image_uploader"
)

# Show preview
if uploaded_file:
    st.image(uploaded_file, caption="Preview", use_container_width=True)

st.divider()

# Check if we're cloning or editing a sample
default_task = ""
default_thought = ""
default_action_type = "click"
editing_sample_id = None

if 'clone_sample' in st.session_state:
    default_task = st.session_state.clone_sample['task']
    default_thought = st.session_state.clone_sample['thought']
    default_action_type = st.session_state.clone_sample['action_type']
    st.info("📋 Cloning sample - modify and submit to create a new one")

if 'edit_sample' in st.session_state:
    default_task = st.session_state.edit_sample['task']
    default_thought = st.session_state.edit_sample['thought']
    default_action_type = st.session_state.edit_sample['action_type']
    editing_sample_id = st.session_state.edit_sample['id']
    st.warning(f"✏️ Editing sample - submit to update (original will be replaced)")

# Task Description
task = st.text_input(
    "Task Description",
    value=default_task,
    placeholder="e.g., Click on Chrome icon in dock",
    help="What should the agent do in this screenshot?",
    key="task_input"
)

# Thought (optional)
thought = st.text_area(
    "Thought (optional)",
    value=default_thought,
    placeholder="e.g., Chrome is in the right dock at x=1710, y=100",
    help="Reasoning about how to accomplish the task",
    height=80,
    key="thought_input"
)

# Action type selector (OUTSIDE form for reactivity)
action_types = list(ACTION_CONFIG.keys()) + ["custom"]
action_type = st.selectbox(
    "Action Type",
    options=action_types,
    index=action_types.index(default_action_type) if default_action_type in action_types else 0,
    format_func=lambda x: f"{x} - {ACTION_CONFIG[x]['description']}" if x in ACTION_CONFIG else "custom - Custom action",
    key="action_type_select"
)

# Debug info
st.caption(f"Selected action type: **{action_type}**")
if action_type in ACTION_CONFIG:
    st.caption(f"Number of fields: **{len(ACTION_CONFIG[action_type]['fields'])}**")

# Dynamic fields based on action configuration
action = ""
action_params = {}

if action_type == "custom":
    action = st.text_input("Custom Action", value="", placeholder="Enter custom action here", key="custom_action")
    action_params = {'raw': action}
elif action_type in ACTION_CONFIG:
    config = ACTION_CONFIG[action_type]
    fields = config["fields"]

    # Dynamically create form fields based on configuration
    field_values = {}

    # Determine column layout based on number of fields
    if len(fields) == 1:
        field = fields[0]
        if field["type"] == "text":
            field_values[field["name"]] = st.text_input(
                field["label"],
                value="",
                placeholder=field["placeholder"],
                key=f"field_{field['name']}"
            )
        elif field["type"] == "select":
            field_values[field["name"]] = st.selectbox(
                field["label"],
                options=field["options"],
                index=field["options"].index(field.get("default", field["options"][0])),
                key=f"field_{field['name']}"
            )
    elif len(fields) == 2:
        col1, col2 = st.columns(2)
        with col1:
            field = fields[0]
            field_values[field["name"]] = st.text_input(
                field["label"],
                value="",
                placeholder=field["placeholder"],
                key=f"field_{field['name']}"
            )
        with col2:
            field = fields[1]
            if field["type"] == "select":
                field_values[field["name"]] = st.selectbox(
                    field["label"],
                    options=field["options"],
                    index=field["options"].index(field.get("default", field["options"][0])),
                    key=f"field_{field['name']}"
                )
            else:
                field_values[field["name"]] = st.text_input(
                    field["label"],
                    value="",
                    placeholder=field["placeholder"],
                    key=f"field_{field['name']}"
                )
    elif len(fields) == 3:
        col1, col2, col3 = st.columns(3)
        for i, field in enumerate(fields):
            with [col1, col2, col3][i]:
                if field["type"] == "select":
                    field_values[field["name"]] = st.selectbox(
                        field["label"],
                        options=field["options"],
                        index=field["options"].index(field.get("default", field["options"][0])),
                        key=f"field_{field['name']}"
                    )
                else:
                    field_values[field["name"]] = st.text_input(
                        field["label"],
                        value="",
                        placeholder=field["placeholder"],
                        key=f"field_{field['name']}"
                    )
    elif len(fields) == 4:
        col1, col2, col3, col4 = st.columns(4)
        for i, field in enumerate(fields):
            with [col1, col2, col3, col4][i]:
                if field["type"] == "select":
                    field_values[field["name"]] = st.selectbox(
                        field["label"],
                        options=field["options"],
                        index=field["options"].index(field.get("default", field["options"][0])),
                        key=f"field_{field['name']}"
                    )
                else:
                    field_values[field["name"]] = st.text_input(
                        field["label"],
                        value="",
                        placeholder=field["placeholder"],
                        key=f"field_{field['name']}"
                    )

    # Parse coordinates if comma-separated (e.g., "38,38")
    if 'x' in field_values and field_values['x'] and ',' in field_values['x']:
        x_val, y_val = parse_coordinates(field_values['x'])
        field_values['x'] = x_val
        if y_val and 'y' in field_values:
            field_values['y'] = y_val

    # Build action string
    action = build_action(action_type, field_values)
    if action:
        action_params = field_values

# Display final action
st.code(action if action else f"{action_type}(...)", language="python")

st.divider()

# Submit button
button_label = "💾 Update Sample" if editing_sample_id else "➕ Add to Dataset"
if st.button(button_label, type="primary", use_container_width=True):
    # Validate inputs
    if not uploaded_file and not editing_sample_id:
        st.error("Please upload a screenshot")
    elif not task:
        st.error("Please enter a task description")
    elif not action:
        st.error("Please enter an action")
    else:
        try:
            # Get image bytes
            if uploaded_file:
                uploaded_file.seek(0)  # Reset file pointer
                image_bytes = uploaded_file.read()
            elif 'edit_sample' in st.session_state:
                # Use existing image from edit_sample
                import base64
                image_bytes = base64.b64decode(st.session_state.edit_sample['image_data'])
            else:
                st.error("No image available")
                st.stop()

            # If editing, delete the old sample first
            if editing_sample_id:
                db.delete_sample(editing_sample_id)
                st.info("Deleted original sample...")

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

            # Clear clone/edit state
            if 'clone_sample' in st.session_state:
                del st.session_state.clone_sample
            if 'edit_sample' in st.session_state:
                del st.session_state.edit_sample

            success_msg = "✅ Updated sample!" if editing_sample_id else f"✅ Added sample to {st.session_state.current_dataset}!"
            st.success(success_msg)
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
                        st.image(image, use_container_width=True)
                    except Exception as e:
                        st.error(f"Failed to load image: {e}")

                with col2:
                    st.markdown(f"**Task:** {sample['task']}")

                    if sample.get('thought'):
                        st.markdown(f"**Thought:** {sample['thought']}")

                    st.markdown(f"**Action:** `{sample['action']}`")

                    if sample.get('action_type'):
                        st.markdown(f"**Action Type:** {sample['action_type']}")
                    if sample.get('action_params'):
                        st.markdown(f"**Params:** {sample['action_params']}")

                    st.caption(f"Created: {sample['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")

                    # Clone and Edit buttons
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button("📋 Clone", key=f"clone_{sample['_id']}", use_container_width=True):
                            # Store sample data in session state for cloning
                            st.session_state.clone_sample = {
                                'task': sample['task'],
                                'thought': sample.get('thought', ''),
                                'action': sample['action'],
                                'action_type': sample.get('action_type', 'click'),
                                'action_params': sample.get('action_params', {})
                            }
                            st.success("Sample copied! Scroll up to edit and submit.")
                            st.rerun()

                    with col_b:
                        if st.button("✏️ Edit", key=f"edit_{sample['_id']}", use_container_width=True):
                            # Store sample for editing (same as clone but we'll delete original on submit)
                            st.session_state.edit_sample = {
                                'id': str(sample['_id']),
                                'task': sample['task'],
                                'thought': sample.get('thought', ''),
                                'action': sample['action'],
                                'action_type': sample.get('action_type', 'click'),
                                'action_params': sample.get('action_params', {}),
                                'image_data': sample['image_data']
                            }
                            st.success("Editing mode! Scroll up to modify and submit.")
                            st.rerun()

                    with col_c:
                        if st.button("🗑️ Delete", key=f"delete_{sample['_id']}", use_container_width=True, type="secondary"):
                            db.delete_sample(str(sample['_id']))
                            st.success("Deleted!")
                            st.rerun()

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
