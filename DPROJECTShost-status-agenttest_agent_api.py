import requests
import json
import os
import time

AGENT_URL = "http://127.0.0.1:9876"

def run_test(name, func):
    print(f"\n--- Running Test: {name} ---")
    try:
        func()
        print(f"--- Test '{name}' PASSED ---")
    except Exception as e:
        print(f"--- Test '{name}' FAILED: {e} ---")

# --- Test Functions ---

def test_status_endpoint():
    print(f"GET {AGENT_URL}/status")
    response = requests.get(f"{AGENT_URL}/status")
    response.raise_for_status() # Raise an exception for HTTP errors
    data = response.json()
    print("Response data:", json.dumps(data, indent=2))
    assert "timestamp" in data
    assert "services" in data
    print("Status endpoint returned 200 OK and valid JSON.")

def test_launch_explorer():
    test_path = os.getcwd() # Use current directory for explorer test
    print(f"POST {AGENT_URL}/launch with path: {test_path}, type: explorer")
    response = requests.post(f"{AGENT_URL}/launch", json={"path": test_path, "type": "explorer"})
    response.raise_for_status()
    data = response.json()
    print("Response data:", json.dumps(data, indent=2))
    assert data.get("status") == "success"
    print("Launch (explorer) endpoint returned 200 OK. Please visually confirm a new Explorer window opened to this directory.")

def test_launch_terminal():
    test_path = os.getcwd() # Use current directory for terminal test
    print(f"POST {AGENT_URL}/launch", json={"path": test_path, "type": "terminal"})
    response = requests.post(f"{AGENT_URL}/launch", json={"path": test_path, "type": "terminal"})
    response.raise_for_status()
    data = response.json()
    print("Response data:", json.dumps(data, indent=2))
    assert data.get("status") == "success"
    print("Launch (terminal) endpoint returned 200 OK. Please visually confirm a new Windows Terminal window opened to this directory.")

def test_launch_vscode():
    test_path = os.getcwd() # Use current directory for vscode test
    print(f"POST {AGENT_URL}/launch", json={"path": test_path, "type": "vscode"})
    response = requests.post(f"{AGENT_URL}/launch", json={"path": test_path, "type": "vscode"})
    response.raise_for_status()
    data = response.json()
    print("Response data:", json.dumps(data, indent=2))
    assert data.get("status") == "success"
    print("Launch (vscode) endpoint returned 200 OK. Please visually confirm VS Code opened to this directory.")

def test_get_file_content_success():
    # Assuming this script is in the agent's root, we can try to read its own README.md
    file_to_read = os.path.join(os.getcwd(), "README.md")
    if not os.path.exists(file_to_read):
        print(f"WARNING: README.md not found at {file_to_read}. Skipping file content test.")
        return

    print(f"GET {AGENT_URL}/files/content?path={file_to_read}")
    response = requests.get(f"{AGENT_URL}/files/content", params={"path": file_to_read})
    response.raise_for_status()
    data = response.json()
    print("Response content (first 200 chars):", data.get("content", "")[:200] + "...")
    assert "content" in data
    assert len(data["content"]) > 0
    print("File content endpoint returned 200 OK and content.")

def test_get_file_content_not_found():
    non_existent_file = "C:\\non_existent_file_12345.txt"
    print(f"GET {AGENT_URL}/files/content?path={non_existent_file}")
    response = requests.get(f"{AGENT_URL}/files/content", params={"path": non_existent_file})
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    print(f"File content endpoint correctly returned 404 for '{non_existent_file}'.")

# --- Main Execution ---
if __name__ == "__main__":
    print(f"Attempting to connect to Host Status Agent at {AGENT_URL}")
    print("Please ensure the agent service is running.")
    time.sleep(2) # Give a moment for agent to be fully up if just started

    run_test("Agent Status", test_status_endpoint)
    run_test("Launch Explorer", test_launch_explorer)
    run_test("Launch Terminal", test_launch_terminal)
    run_test("Launch VS Code", test_launch_vscode)
    run_test("Get File Content (Success)", test_get_file_content_success)
    run_test("Get File Content (Not Found)", test_get_file_content_not_found)
