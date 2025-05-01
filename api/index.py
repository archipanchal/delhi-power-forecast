from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Delhi Power Consumption Forecast</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: sans-serif; margin: 0; padding: 20px; }
                h1 { color: #1E88E5; }
            </style>
        </head>
        <body>
            <h1>Delhi Power Consumption Forecast</h1>
            <p>Successfully deployed to Vercel!</p>
            <p><a href="https://github.com/archipanchal/delhi-power-forecast">View on GitHub</a></p>
        </body>
        </html>
        """
        
        self.wfile.write(html_content.encode())
        return 