import subprocess
import time
import webbrowser

def start_server():
    print("🚀 Starting PayMe Wallet Server...")
    
    try:
        # Start the Flask server
        process = subprocess.Popen(['python', 'app.py'])
        
        # Wait for server to start
        time.sleep(3)
        
        # Open the browser
        webbrowser.open('http://127.0.0.1:5000/api/test')
        
        print("✅ Server should be running at http://127.0.0.1:5000")
        print("📊 Test API: http://127.0.0.1:5000/api/test")
        print("💱 Exchange rates: http://127.0.0.1:5000/api/exchange-rates")
        
        # Keep the server running
        process.wait()
        
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == '__main__':
    start_server()