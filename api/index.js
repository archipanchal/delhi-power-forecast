// Simple Node.js based API endpoint for Vercel
module.exports = (req, res) => {
  const date = new Date().toISOString();
  
  res.setHeader('Content-Type', 'text/html');
  res.status(200).send(`
    <!DOCTYPE html>
    <html>
    <head>
        <title>Delhi Power Consumption Forecast</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
              font-family: sans-serif; 
              margin: 0; 
              padding: 20px; 
              text-align: center;
              background-color: #f5f5f5;
            }
            h1 { 
              color: #1E88E5; 
              margin-bottom: 20px;
            }
            .container { 
              max-width: 800px; 
              margin: 0 auto; 
              padding: 30px;
              background: white;
              border-radius: 8px;
              box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .button {
              display: inline-block;
              background-color: #1E88E5;
              color: white;
              padding: 10px 20px;
              text-decoration: none;
              border-radius: 4px;
              font-weight: bold;
              margin-top: 20px;
            }
            .timestamp {
              margin-top: 20px;
              font-size: 0.9rem;
              color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Delhi Power Consumption Forecast</h1>
            <p>Successfully deployed to Vercel!</p>
            <p>This application demonstrates the Delhi Power Consumption forecast system, which uses machine learning to predict future power demand based on historical patterns.</p>
            <p><a href="https://github.com/archipanchal/delhi-power-forecast" class="button">View on GitHub</a></p>
            <div class="timestamp">
                Server time: ${date}
            </div>
        </div>
    </body>
    </html>
  `);
}; 