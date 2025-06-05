#!/usr/bin/env python3
"""
Quick validation test for Ai-semble v2
"""
import os
import sys
import subprocess
import json

def test_python_files():
    """Test Python file compilation"""
    python_files = [
        'containers/orchestrator/src/app.py',
        'containers/orchestrator/src/api/health.py',
        'containers/orchestrator/src/api/ai.py',
        'containers/orchestrator/src/api/jobs.py',
        'containers/orchestrator/src/config/settings.py',
        'containers/ai-services/llm/src/llm_service.py',
        'containers/data-processor/src/processor_service.py'
    ]
    
    for py_file in python_files:
        if os.path.exists(py_file):
            try:
                subprocess.run([sys.executable, '-m', 'py_compile', py_file], 
                             check=True, capture_output=True)
                print(f"✓ {py_file}")
            except subprocess.CalledProcessError as e:
                print(f"✗ {py_file}: {e}")
                return False
        else:
            print(f"✗ {py_file}: File not found")
            return False
    return True

def test_json_files():
    """Test JSON file syntax"""
    json_files = [
        'security/seccomp/ai-semble.json'
    ]
    
    for json_file in json_files:
        if os.path.exists(json_file):
            try:
                with open(json_file) as f:
                    json.load(f)
                print(f"✓ {json_file}")
            except json.JSONDecodeError as e:
                print(f"✗ {json_file}: {e}")
                return False
        else:
            print(f"✗ {json_file}: File not found")
            return False
    return True

def test_file_structure():
    """Test basic file structure"""
    required_files = [
        'README.md',
        'CLAUDE.md', 
        'DEVELOPMENT_PLAN.md',
        'containers/orchestrator/Containerfile',
        'containers/orchestrator/requirements.txt',
        'containers/ai-services/llm/Containerfile',
        'containers/data-processor/Containerfile',
        'pods/ai-semble.yaml',
        'scripts/setup.sh',
        'scripts/deploy.sh'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path}: Missing")
            return False
    return True

def main():
    print("=== Ai-semble v2 Quick Validation ===")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Syntax", test_python_files), 
        ("JSON Syntax", test_json_files)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        result = test_func()
        results.append(result)
        print(f"{test_name}: {'PASS' if result else 'FAIL'}")
    
    print(f"\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All basic validations passed!")
        print("\nNext steps:")
        print("1. Check if Podman is available: podman --version")
        print("2. Try building a container: podman build containers/orchestrator/")
        return 0
    else:
        print("✗ Some validations failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())