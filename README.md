# UI-TARS Streamlit Dataset Creator

Web UI for creating UI-TARS training datasets with MongoDB storage.

## Features

- **app.py**: Cloud-enabled version using MongoDB Atlas for storage
- **app_local.py**: Local version using filesystem (requires parent project's `create_training_dataset.py`)
- Drag-and-drop screenshot annotation
- Export datasets in LLaVA format for fine-tuning

## Setup

### Cloud Version (app.py)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure MongoDB:**
   - Sign up for [MongoDB Atlas](https://mongodb.com/cloud/atlas) (free tier available)
   - Create a cluster and get your connection string
   - Create `.env` file:
     ```
     MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
     ```

3. **Run:**
   ```bash
   streamlit run app.py
   ```

### Local Version (app_local.py)

**Note:** This version requires the parent `ui-tars-test` project for `create_training_dataset.py`.

```bash
# From parent directory
cd ..
streamlit run streamlit-app/app_local.py
```

## Deployment

### Streamlit Cloud

1. Push this folder to GitHub
2. Connect at [share.streamlit.io](https://share.streamlit.io)
3. Add `MONGODB_URI` in App Settings → Secrets

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py"]
```

## Usage

1. Upload a screenshot
2. Describe the task
3. Specify the action
4. Add to dataset
5. Export as JSON for fine-tuning
