# Chatbot Web UI

A modern, beautiful web interface for the AI chatbot matching the design you provided.

## Features

✅ **Modern UI Design**
- Clean, professional interface matching your design
- Responsive layout with sidebar and main chat area
- Smooth animations and transitions

✅ **Conversation Management**
- Create new conversations
- View conversation history
- Search conversations
- Edit conversation titles
- Delete conversations
- Clear all conversations

✅ **Chat Features**
- Real-time messaging with AI
- Message copy functionality
- Regenerate responses
- Loading indicators
- Smooth scrolling

✅ **Integration**
- Uses your existing chatbot backend
- Supports all LLM providers (OpenAI, Gemini, DeepSeek)
- Maintains conversation context

## Quick Start

### 1. Install Dependencies

Make sure Flask and flask-cors are installed:

```bash
pip install Flask>=2.0.1 flask-cors>=3.1.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 2. Configure Your LLM Provider

Make sure your `.env` file is configured with your LLM provider:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4.1
```

### 3. Run the Web Server

```bash
python app.py
```

The server will start on `http://localhost:5000`

### 4. Open in Browser

Open your web browser and navigate to:

```
http://localhost:5000
```

## Project Structure

```
generative-ai-chatbot/
├── app.py                 # Flask web server
├── web/
│   ├── templates/
│   │   └── index.html    # Main HTML template
│   └── static/
│       ├── css/
│       │   └── style.css # Stylesheet
│       └── js/
│           └── app.js    # JavaScript for interactions
└── src/
    └── chatbot.py        # Chatbot backend (used by app.py)
```

## API Endpoints

### POST `/api/chat`
Send a message and get AI response.

**Request:**
```json
{
  "message": "Hello!",
  "conversation_id": "conv_123" // optional
}
```

**Response:**
```json
{
  "response": "Hello! How can I help you?",
  "conversation_id": "conv_123",
  "timestamp": "2024-01-01T12:00:00"
}
```

### GET `/api/conversations`
Get list of all conversations.

**Response:**
```json
{
  "conversations": [
    {
      "id": "conv_123",
      "title": "Chat about Python",
      "created_at": "2024-01-01T12:00:00",
      "message_count": 10
    }
  ]
}
```

### GET `/api/conversations/<id>`
Get a specific conversation with all messages.

### DELETE `/api/conversations/<id>`
Delete a specific conversation.

### DELETE `/api/conversations`
Clear all conversations.

### POST `/api/new-chat`
Create a new chat conversation.

### PUT `/api/conversations/<id>/title`
Update conversation title.

## Usage

1. **Start a New Chat**: Click the "+ New chat" button
2. **Send Messages**: Type in the input field and press Enter or click send
3. **View History**: Click on any conversation in the sidebar
4. **Search**: Use the search box to find conversations
5. **Manage**: Hover over conversations to see edit/delete options
6. **Copy Messages**: Click the copy icon on any assistant message
7. **Regenerate**: Click regenerate to get a new response

## Customization

### Change Colors

Edit `web/static/css/style.css`:

- Primary color (purple): `#8b5cf6` - Change all instances
- Background: Modify the `body` background gradient
- Sidebar: Adjust `.sidebar` background color

### Change Branding

Edit `web/templates/index.html`:

- Logo text: Change "CHAT A.I+" 
- User name: Change "Andrew Neilson"
- Avatar initials: Change "AN"

### Adjust Layout

Edit `web/static/css/style.css`:

- Sidebar width: Change `.sidebar` width
- Chat area: Modify `.chat-area` styles
- Message width: Adjust `.message` max-width

## Troubleshooting

### Port Already in Use

If port 5000 is already in use, change it in `app.py`:

```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change port number
```

### CORS Errors

If you encounter CORS errors, make sure `flask-cors` is installed:

```bash
pip install flask-cors
```

### API Errors

Check that your LLM provider is configured correctly in `.env`:

```bash
# Verify configuration
python -c "from config.config import Config; print(f'Provider: {Config.LLM_PROVIDER}, Model: {Config.get_llm_model()}')"
```

### Static Files Not Loading

Make sure the directory structure is correct:

```
web/
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

## Development

### Enable Debug Mode

Debug mode is enabled by default in `app.py`. For production, set:

```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

### Add New Features

1. **Backend**: Add new routes in `app.py`
2. **Frontend**: Add UI elements in `index.html`
3. **Styling**: Add styles in `style.css`
4. **Interactions**: Add JavaScript in `app.js`

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Opera (latest)

## Next Steps

- Add user authentication
- Persist conversations to database
- Add file upload support
- Implement voice input/output
- Add theme switching (dark/light mode)
- Export conversations

Enjoy your new chatbot web interface! 🚀

