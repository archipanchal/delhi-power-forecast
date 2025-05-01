from datetime import datetime

def handler(request, response):
    # Return a simple HTML response
    response.status = 200
    response.headers = {
        "Content-Type": "text/html"
    }
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Delhi Power Consumption Forecast</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 20px; text-align: center; }}
            h1 {{ color: #1E88E5; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Delhi Power Consumption Forecast</h1>
            <p>Successfully deployed to Vercel!</p>
            <p>Server time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p><a href="https://github.com/archipanchal/delhi-power-forecast">View on GitHub</a></p>
        </div>
    </body>
    </html>
    """ 