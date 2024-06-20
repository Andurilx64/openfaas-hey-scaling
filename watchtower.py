import subprocess
import re

def run_hey(url, requests=200, concurrency=50):
    command = [
        'hey',
        '-n', str(requests),
        '-c', str(concurrency),
        url
    ]

    try:
        # Execute the command
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Fetch stdout and stderr
        stdout = result.stdout
        stderr = result.stderr

        return stdout
    
    except subprocess.CalledProcessError as e:
        # Handle errors
        print(f"Error occurred: {e}")
        return None
    

def parse_output(stdout):

    patterns = {
        "total": r"Total:\s+([\d.]+) secs",
        "slowest": r"Slowest:\s+([\d.]+) secs",
        "fastest": r"Fastest:\s+([\d.]+) secs",
        "average": r"Average:\s+([\d.]+) secs",
        "requests_per_sec": r"Requests/sec:\s+([\d.]+)",
        "total_data": r"Total data:\s+(\d+) bytes",
        "size_per_request": r"Size/request:\s+(\d+) bytes"
    }
     
    match = re.search(patterns["average"], stdout)
    if not match:
        return None
    else:
        return float(match.group(1))
    

url = 'http://localhost:8080/fucntion/ftest'
out = run_hey(url, 1, 1)
parsed = parse_output(out)
print(parsed)
