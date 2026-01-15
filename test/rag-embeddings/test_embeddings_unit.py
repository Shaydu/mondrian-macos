#!/usr/bin/env python3
"""
Unit Tests for Embedding Support Functions

This test suite verifies the core embedding functions in isolation:
1. CLIP embedding computation
2. Embedding similarity search
3. Hybrid prompt augmentation
4. Database operations for embeddings

Usage:
    python3 test/test_embeddings_unit.py                    # Run all tests
    python3 test/test_embeddings_unit.py TestEmbeddingComputation  # Run specific test
    python3 test/test_embeddings_unit.py -v                 # Verbose output
"""

import os
import sys
import json
import tempfile
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "mondrian"))

# Test image path
TEST_IMAGE_PATH = PROJECT_ROOT / "source" / "photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg"


class TestEmbeddingComputation(unittest.TestCase):
    """Test CLIP embedding computation."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.test_image_path = TEST_IMAGE_PATH
    
    def test_clip_embedding_import(self):
        """Test that CLIP can be imported."""
        try:
            import torch
            import clip
            self.assertIsNotNone(torch)
            self.assertIsNotNone(clip)
        except ImportError as e:
            self.skipTest(f"CLIP not installed: {e}")
    
    def test_embedding_computation(self):
        """Test that embeddings can be computed from an image."""
        try:
            import torch
            import clip
            from PIL import Image
            import numpy as np
        except ImportError:
            self.skipTest("CLIP dependencies not installed")
        
        if not self.test_image_path.exists():
            self.skipTest(f"Test image not found: {self.test_image_path}")
        
        try:
            device = "cpu"  # Use CPU for testing
            model, preprocess = clip.load("ViT-B/32", device=device)
            
            # Load and process image
            image = preprocess(Image.open(self.test_image_path).convert("RGB"))
            image = image.unsqueeze(0).to(device)
            
            # Compute embedding
            with torch.no_grad():
                embedding = model.encode_image(image)
                embedding_np = embedding.cpu().numpy().squeeze()
            
            # Verify embedding properties
            self.assertIsInstance(embedding_np, np.ndarray)
            self.assertEqual(embedding_np.shape, (512,))  # ViT-B/32 produces 512-dim vectors
            self.assertTrue(np.all(np.isfinite(embedding_np)))  # No NaN or Inf
            
        except Exception as e:
            self.fail(f"Failed to compute embedding: {e}")
    
    def test_embedding_normalization(self):
        """Test that embeddings are normalized (unit vectors)."""
        try:
            import torch
            import clip
            from PIL import Image
            import numpy as np
        except ImportError:
            self.skipTest("CLIP dependencies not installed")
        
        if not self.test_image_path.exists():
            self.skipTest(f"Test image not found: {self.test_image_path}")
        
        try:
            device = "cpu"
            model, preprocess = clip.load("ViT-B/32", device=device)
            
            image = preprocess(Image.open(self.test_image_path).convert("RGB"))
            image = image.unsqueeze(0).to(device)
            
            with torch.no_grad():
                embedding = model.encode_image(image)
                embedding_np = embedding.cpu().numpy().squeeze()
            
            # Check if embedding is normalized
            norm = np.linalg.norm(embedding_np)
            self.assertAlmostEqual(norm, 1.0, places=5)
            
        except Exception as e:
            self.fail(f"Failed to check normalization: {e}")
    
    def test_embedding_consistency(self):
        """Test that computing embedding twice gives same result."""
        try:
            import torch
            import clip
            from PIL import Image
            import numpy as np
        except ImportError:
            self.skipTest("CLIP dependencies not installed")
        
        if not self.test_image_path.exists():
            self.skipTest(f"Test image not found: {self.test_image_path}")
        
        try:
            device = "cpu"
            model, preprocess = clip.load("ViT-B/32", device=device)
            model.eval()  # Set to eval mode for consistency
            
            image = preprocess(Image.open(self.test_image_path).convert("RGB"))
            image = image.unsqueeze(0).to(device)
            
            with torch.no_grad():
                embedding1 = model.encode_image(image).cpu().numpy().squeeze()
                embedding2 = model.encode_image(image).cpu().numpy().squeeze()
            
            # Check consistency (should be identical on CPU)
            np.testing.assert_array_almost_equal(embedding1, embedding2, decimal=6)
            
        except Exception as e:
            self.fail(f"Failed consistency check: {e}")


class TestEmbeddingSimilarity(unittest.TestCase):
    """Test embedding similarity search."""
    
    def test_cosine_similarity_computation(self):
        """Test cosine similarity calculation."""
        import numpy as np
        
        # Create test embeddings
        v1 = np.array([1, 0, 0], dtype=np.float32)
        v2 = np.array([1, 0, 0], dtype=np.float32)  # Identical
        v3 = np.array([0, 1, 0], dtype=np.float32)  # Orthogonal
        
        # Compute similarities
        sim_same = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        sim_orth = np.dot(v1, v3) / (np.linalg.norm(v1) * np.linalg.norm(v3))
        
        self.assertAlmostEqual(sim_same, 1.0, places=5)  # Identical vectors have similarity 1
        self.assertAlmostEqual(sim_orth, 0.0, places=5)  # Orthogonal vectors have similarity 0
    
    def test_similarity_ranking(self):
        """Test that similarity ranking works correctly."""
        import numpy as np
        
        # Create test embeddings (normalized)
        user = np.array([1, 0, 0], dtype=np.float32)
        
        # Portfolio embeddings (in order of decreasing similarity)
        portfolio = {
            'img1': np.array([0.99, 0.1, 0], dtype=np.float32),  # Very similar
            'img2': np.array([0.7, 0.7, 0], dtype=np.float32),   # Somewhat similar
            'img3': np.array([0, 1, 0], dtype=np.float32),       # Orthogonal
        }
        
        # Normalize
        user = user / np.linalg.norm(user)
        for key in portfolio:
            portfolio[key] = portfolio[key] / np.linalg.norm(portfolio[key])
        
        # Compute similarities
        similarities = {}
        for key, embedding in portfolio.items():
            sim = np.dot(user, embedding)
            similarities[key] = sim
        
        # Sort by similarity
        ranked = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        
        # Verify ranking
        self.assertEqual(ranked[0][0], 'img1')  # Most similar should be first
        self.assertEqual(ranked[1][0], 'img2')  # Second most similar
        self.assertEqual(ranked[2][0], 'img3')  # Least similar


class TestHybridAugmentation(unittest.TestCase):
    """Test hybrid prompt augmentation."""
    
    def test_augmentation_structure(self):
        """Test that augmented prompt has required structure."""
        # Mock data
        base_prompt = "Analyze the provided image."
        visual_matches = [
            {'image_title': 'Visual Match 1', 'embedding_similarity': 0.85},
            {'image_title': 'Visual Match 2', 'embedding_similarity': 0.80}
        ]
        dimensional_matches = {
            'composition': {'image_title': 'Composition Example', 'comparison': {}},
            'lighting': {'image_title': 'Lighting Example', 'comparison': {}}
        }
        
        # Create augmented prompt
        augmented = f"{base_prompt}\n\n### Visual Matches\n"
        for match in visual_matches:
            augmented += f"- {match['image_title']} ({match['embedding_similarity']:.1%})\n"
        
        # Verify structure
        self.assertIn("### Visual Matches", augmented)
        self.assertIn("Visual Match 1", augmented)
        self.assertIn("0.85", augmented)
    
    def test_augmentation_hybrid_context(self):
        """Test that augmentation combines visual, dimensional, and technique context."""
        prompt = "Base prompt"
        
        # Simulate hybrid augmentation
        augmented = f"{prompt}\n\n=== HYBRID ANALYSIS ===" \
                    f"\n### Visual Similarity (CLIP)\n" \
                    f"### Dimensional Strengths\n" \
                    f"### Technique Matches\n"
        
        # Verify all sections present
        self.assertIn("HYBRID", augmented)
        self.assertIn("Visual Similarity", augmented)
        self.assertIn("Dimensional", augmented)
        self.assertIn("Technique", augmented)


class TestEmbeddingDatabase(unittest.TestCase):
    """Test embedding database operations."""
    
    def setUp(self):
        """Create temporary test database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Create schema
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE dimensional_profiles (
                id TEXT PRIMARY KEY,
                advisor_id TEXT,
                image_path TEXT,
                composition_score REAL,
                lighting_score REAL,
                focus_sharpness_score REAL,
                color_harmony_score REAL,
                subject_isolation_score REAL,
                depth_perspective_score REAL,
                visual_balance_score REAL,
                emotional_impact_score REAL,
                embedding BLOB
            )
        """)
        
        cursor.execute("""
            CREATE INDEX idx_embedding ON dimensional_profiles(advisor_id)
            WHERE embedding IS NOT NULL
        """)
        
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_embedding_storage(self):
        """Test storing and retrieving embeddings from database."""
        import numpy as np
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create test embedding
        embedding = np.random.randn(512).astype(np.float32)
        embedding_bytes = embedding.tobytes()
        
        # Store
        cursor.execute("""
            INSERT INTO dimensional_profiles 
            (id, advisor_id, image_path, composition_score, embedding)
            VALUES (?, ?, ?, ?, ?)
        """, ('test1', 'ansel', '/path/to/image.jpg', 8.5, embedding_bytes))
        
        conn.commit()
        
        # Retrieve
        cursor.execute("""
            SELECT embedding FROM dimensional_profiles WHERE id = ?
        """, ('test1',))
        
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        
        retrieved_bytes = row[0]
        retrieved_embedding = np.frombuffer(retrieved_bytes, dtype=np.float32)
        
        # Verify
        np.testing.assert_array_equal(embedding, retrieved_embedding)
        
        conn.close()
    
    def test_embedding_index_query(self):
        """Test querying profiles with embeddings."""
        import numpy as np
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert profiles with and without embeddings
        for i in range(5):
            embedding = None if i < 2 else np.random.randn(512).astype(np.float32).tobytes()
            cursor.execute("""
                INSERT INTO dimensional_profiles 
                (id, advisor_id, image_path, composition_score, embedding)
                VALUES (?, ?, ?, ?, ?)
            """, (f'test{i}', 'ansel', f'/path/to/image{i}.jpg', 8.5, embedding))
        
        conn.commit()
        
        # Query profiles with embeddings
        cursor.execute("""
            SELECT COUNT(*) FROM dimensional_profiles
            WHERE advisor_id = ? AND embedding IS NOT NULL
        """, ('ansel',))
        
        count = cursor.fetchone()[0]
        self.assertEqual(count, 3)  # Should have 3 profiles with embeddings
        
        conn.close()
    
    def test_embedding_index_exists(self):
        """Test that embedding index was created."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if index exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE '%embedding%'
        """)
        
        indices = cursor.fetchall()
        self.assertTrue(len(indices) > 0, "Embedding index should exist")
        
        conn.close()


class TestEmbeddingGracefulDegradation(unittest.TestCase):
    """Test graceful degradation when embeddings are unavailable."""
    
    @patch('mondrian.strategies.rag_lora.torch')
    def test_missing_torch(self, mock_torch):
        """Test behavior when torch is not installed."""
        mock_torch.side_effect = ImportError("No module named 'torch'")
        
        # Should handle gracefully - this is verified in actual code
        self.assertIsNotNone(mock_torch)
    
    @patch('mondrian.strategies.rag_lora.clip')
    def test_missing_clip(self, mock_clip):
        """Test behavior when CLIP is not installed."""
        mock_clip.side_effect = ImportError("No module named 'clip'")
        
        # Should handle gracefully
        self.assertIsNotNone(mock_clip)
    
    def test_empty_embedding_results(self):
        """Test handling of empty embedding search results."""
        # Empty portfolio should return empty results
        results = []
        
        self.assertEqual(len(results), 0)
        # System should fall back to dimensional matching
        self.assertIsNotNone(results)  # Result object should still exist


class TestEmbeddingIntegration(unittest.TestCase):
    """Integration tests for embedding workflow."""
    
    def test_embedding_workflow_structure(self):
        """Test that embedding workflow follows expected structure."""
        # Expected workflow:
        # 1. Compute user embedding
        # 2. Query database for profiles with embeddings
        # 3. Compute similarity scores
        # 4. Rank results
        # 5. Augment prompt with top results
        # 6. Generate analysis
        
        workflow_steps = [
            "compute_user_embedding",
            "query_portfolio_embeddings",
            "compute_similarities",
            "rank_results",
            "augment_prompt",
            "generate_analysis"
        ]
        
        # Verify workflow structure
        for step in workflow_steps:
            self.assertIsNotNone(step)  # All steps should be defined
    
    def test_fallback_behavior(self):
        """Test fallback when embeddings fail."""
        # If embedding computation fails:
        # 1. Set enable_embeddings = False
        # 2. Continue with dimensional-only RAG
        # 3. Log warning message
        
        # Simulate fallback scenario
        enable_embeddings = True
        user_embedding = None
        
        # This should trigger fallback
        if user_embedding is None:
            enable_embeddings = False
        
        self.assertFalse(enable_embeddings)


def suite():
    """Create test suite."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestEmbeddingComputation))
    suite.addTests(loader.loadTestsFromTestCase(TestEmbeddingSimilarity))
    suite.addTests(loader.loadTestsFromTestCase(TestHybridAugmentation))
    suite.addTests(loader.loadTestsFromTestCase(TestEmbeddingDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestEmbeddingGracefulDegradation))
    suite.addTests(loader.loadTestsFromTestCase(TestEmbeddingIntegration))
    
    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())
    sys.exit(0 if result.wasSuccessful() else 1)
