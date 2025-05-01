from http.server import BaseHTTPRequestHandler
from datetime import datetime
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Delhi Power Consumption Forecast</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f8fa;
                    color: #333;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 2rem;
                }
                header {
                    background-color: #1E88E5;
                    color: white;
                    padding: 2rem 0;
                    text-align: center;
                }
                h1 {
                    margin: 0;
                    font-size: 2.5rem;
                }
                .subtitle {
                    margin-top: 0.5rem;
                    font-size: 1.2rem;
                    opacity: 0.9;
                }
                .card {
                    background-color: white;
                    border-radius: 8px;
                    padding: 2rem;
                    margin: 2rem 0;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }
                .feature-list {
                    list-style-type: none;
                    padding: 0;
                }
                .feature-list li {
                    margin-bottom: 1rem;
                    padding-left: 1.5rem;
                    position: relative;
                }
                .feature-list li:before {
                    content: "⚡";
                    position: absolute;
                    left: 0;
                    color: #1E88E5;
                }
                .button {
                    display: inline-block;
                    background-color: #1E88E5;
                    color: white;
                    padding: 0.8rem 1.5rem;
                    text-decoration: none;
                    border-radius: 4px;
                    font-weight: bold;
                    margin-top: 1rem;
                }
                footer {
                    text-align: center;
                    margin-top: 2rem;
                    padding: 1rem 0;
                    color: #666;
                    font-size: 0.9rem;
                }
                .timestamp {
                    margin-top: 1rem;
                    font-size: 0.8rem;
                    color: #666;
                }
            </style>
        </head>
        <body>
            <header>
                <div class="container">
                    <h1>Delhi Power Consumption Forecast</h1>
                    <div class="subtitle">Analyzing and predicting power demand patterns</div>
                </div>
            </header>
            
            <div class="container">
                <div class="card">
                    <h2>About the Project</h2>
                    <p>
                        This application uses machine learning to analyze historical power consumption data 
                        in Delhi and predict future demand patterns. It provides interactive visualizations 
                        and forecasting tools to help understand electricity usage trends.
                    </p>
                    
                    <h3>Key Features</h3>
                    <ul class="feature-list">
                        <li><strong>Interactive Dashboard:</strong> Visualize historical power consumption patterns</li>
                        <li><strong>ML-Powered Forecasting:</strong> Predict future power demand using LSTM models</li>
                        <li><strong>Comparative Analysis:</strong> Compare current consumption with historical patterns</li>
                        <li><strong>Multi-Factor Authentication:</strong> Secure access with email and mobile verification</li>
                        <li><strong>Comprehensive Logging:</strong> Detailed activity tracking for system monitoring</li>
                    </ul>
                    
                    <a href="https://github.com/archipanchal/delhi-power-forecast" class="button">Visit GitHub Repository</a>
                </div>
                
                <div class="timestamp">
                    Deployed on Vercel | Server time: {timestamp}
                </div>
            </div>
            
            <footer>
                <div class="container">
                    Delhi Power Consumption Forecast Application | © 2024
                </div>
            </footer>
        </body>
        </html>
        """.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        self.wfile.write(html_content.encode())
        return

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            'status': 'success',
            'message': 'This is the API endpoint for Delhi Power Consumption Forecast',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.wfile.write(json.dumps(response).encode()) 