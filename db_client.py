#!/usr/bin/env python3.11
"""
MongoDB database client for UI-TARS dataset storage
"""

from pymongo import MongoClient
import os
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Try to import streamlit for secrets (optional)
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


class DatasetDB:
    def __init__(self, mongodb_uri=None):
        """
        Initialize MongoDB connection

        Args:
            mongodb_uri: MongoDB connection string. If None, reads from MONGODB_URI env var or Streamlit secrets
        """
        if mongodb_uri is None:
            # Try Streamlit secrets first, then env var
            if HAS_STREAMLIT:
                try:
                    mongodb_uri = st.secrets.get("MONGODB_URI")
                except:
                    pass

            if not mongodb_uri:
                mongodb_uri = os.getenv('MONGODB_URI')

        if not mongodb_uri:
            raise ValueError(
                "MONGODB_URI not provided. Set as environment variable or pass to constructor."
            )

        # Add TLS/SSL parameters for Python 3.13+ compatibility
        self.client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000
        )
        self.db = self.client['ui_tars']
        self.datasets = self.db['datasets']
        self.samples = self.db['samples']

    def create_dataset(self, name, description=""):
        """Create a new dataset"""
        # Check if already exists
        existing = self.datasets.find_one({'name': name})
        if existing:
            return str(existing['_id'])

        dataset = {
            'name': name,
            'description': description,
            'created_at': datetime.utcnow(),
            'sample_count': 0
        }

        result = self.datasets.insert_one(dataset)
        return str(result.inserted_id)

    def add_sample(self, dataset_name, image_bytes, task, thought, action):
        """
        Add a training sample to dataset

        Args:
            dataset_name: Name of the dataset
            image_bytes: Image data as bytes
            task: Task description
            thought: Reasoning (optional, can be empty string)
            action: Action to perform

        Returns:
            Sample ID
        """
        # Get or create dataset
        dataset = self.datasets.find_one({'name': dataset_name})
        if not dataset:
            dataset_id = self.create_dataset(dataset_name)
        else:
            dataset_id = str(dataset['_id'])

        # Convert image to base64 for storage
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        # Create sample document
        sample = {
            'dataset_id': dataset_id,
            'dataset_name': dataset_name,
            'image_data': image_b64,  # Store as base64
            'task': task,
            'thought': thought,
            'action': action,
            'created_at': datetime.utcnow(),
            'conversations': [
                {
                    'from': 'human',
                    'value': f'<image>\nYou are a GUI agent. The task is: {task}\n\nWhat is the next action?'
                },
                {
                    'from': 'gpt',
                    'value': f'Thought: {thought}\nAction: {action}' if thought else f'Action: {action}'
                }
            ]
        }

        # Insert sample
        result = self.samples.insert_one(sample)

        # Update dataset count
        self.datasets.update_one(
            {'name': dataset_name},
            {'$inc': {'sample_count': 1}}
        )

        return str(result.inserted_id)

    def get_dataset_samples(self, dataset_name, limit=100):
        """Get samples from a dataset"""
        return list(self.samples.find(
            {'dataset_name': dataset_name}
        ).sort('created_at', -1).limit(limit))

    def get_all_datasets(self):
        """List all datasets"""
        return list(self.datasets.find().sort('created_at', -1))

    def export_dataset(self, dataset_name):
        """
        Export dataset in LLaVA format for fine-tuning

        Returns:
            List of annotations with embedded images
        """
        samples = self.get_dataset_samples(dataset_name, limit=10000)

        annotations = []
        for i, sample in enumerate(samples):
            annotations.append({
                'id': f"{dataset_name}_{i}_{sample['_id']}",
                'image_data': sample['image_data'],  # Base64 encoded
                'conversations': sample['conversations']
            })

        return annotations

    def get_dataset_stats(self, dataset_name):
        """Get statistics for a dataset"""
        dataset = self.datasets.find_one({'name': dataset_name})
        if not dataset:
            return None

        return {
            'name': dataset['name'],
            'sample_count': dataset['sample_count'],
            'created_at': dataset['created_at'],
            'description': dataset.get('description', '')
        }

    def delete_sample(self, sample_id):
        """Delete a sample"""
        from bson.objectid import ObjectId

        sample = self.samples.find_one({'_id': ObjectId(sample_id)})
        if sample:
            self.samples.delete_one({'_id': ObjectId(sample_id)})
            self.datasets.update_one(
                {'name': sample['dataset_name']},
                {'$inc': {'sample_count': -1}}
            )
            return True
        return False

    def delete_dataset(self, dataset_name):
        """Delete a dataset and all its samples"""
        # Delete all samples
        self.samples.delete_many({'dataset_name': dataset_name})

        # Delete dataset
        result = self.datasets.delete_one({'name': dataset_name})
        return result.deleted_count > 0

    def clear_all(self):
        """Clear all datasets and samples (use with caution!)"""
        self.samples.delete_many({})
        self.datasets.delete_many({})
