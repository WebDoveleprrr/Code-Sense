import pytest
from app.ml.pipeline import rank_files

def test_rank_files_truncation_and_priority():
    # Simulate a parsed repository with 5000 files
    files = []
    
    # 1. High priority source files
    for i in range(10):
        files.append({
            "file_path": f"src/controllers/controller_{i}.py",
            "language": "python",
            "size_bytes": 1000
        })
        
    for i in range(10):
        files.append({
            "file_path": f"src/routes/route_{i}.js",
            "language": "javascript",
            "size_bytes": 1200
        })

    # 2. Medium priority files
    for i in range(50):
        files.append({
            "file_path": f"utils/helper_{i}.py",
            "language": "python",
            "size_bytes": 800
        })
        
    # 3. Low priority files
    for i in range(200):
        files.append({
            "file_path": f"tests/test_feature_{i}.py",
            "language": "python",
            "size_bytes": 500
        })
        
    # 4. Filler (Default priority)
    for i in range(4730):
        files.append({
            "file_path": f"data/filler_{i}.txt",
            "language": None,
            "size_bytes": 200
        })
        
    # Total files = 10 + 10 + 50 + 200 + 4730 = 5000
    assert len(files) == 5000

    ranked = rank_files(files)
    
    # Check top ranked
    # src/ (score 80) and main/index (100) are top. We have 20 high priority (80)
    top_20 = ranked[:20]
    for f in top_20:
        assert "src/controllers" in f["file_path"] or "src/routes" in f["file_path"]
        
    # Check next 50 (medium priority, score 50)
    next_50 = ranked[20:70]
    for f in next_50:
        assert "utils/" in f["file_path"]
        
    # Check next (default priority, score 30, since tests are score 10)
    # Filler is scored 30. Tests are scored 10.
    # Therefore, filler (4730) should come before tests (200).
    next_filler = ranked[70:80]
    for f in next_filler:
        assert "data/filler" in f["file_path"]
        
    # Slicing at 1000:
    sliced = ranked[:1000]
    assert len(sliced) == 1000
    
    # We should have all 20 high, 50 medium, and 930 fillers. 0 tests.
    high_count = sum(1 for f in sliced if "src/" in f["file_path"])
    med_count = sum(1 for f in sliced if "utils/" in f["file_path"])
    filler_count = sum(1 for f in sliced if "data/filler" in f["file_path"])
    test_count = sum(1 for f in sliced if "tests/" in f["file_path"])
    
    assert high_count == 20
    assert med_count == 50
    assert filler_count == 930
    assert test_count == 0

    # Tie breaking check
    # Same score (30 for fillers), depth (1 /data/..), is_source (None -> 1).
    # Then size ascending. We made them all 200 bytes. If we had varying sizes, smallest would win.
    files.append({
        "file_path": "data/filler_small.txt",
        "language": None,
        "size_bytes": 50
    })
    files.append({
        "file_path": "data/filler_large.txt",
        "language": None,
        "size_bytes": 10000
    })
    
    ranked_again = rank_files(files)
    
    # Small should appear before large
    small_idx = next(i for i, f in enumerate(ranked_again) if f["file_path"] == "data/filler_small.txt")
    large_idx = next(i for i, f in enumerate(ranked_again) if f["file_path"] == "data/filler_large.txt")
    
    assert small_idx < large_idx
